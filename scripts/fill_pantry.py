"""Fill the pantry for saved v2 recipes whose lines are not all linked (services/recipe_v2/pantry_fill.py, 27.10.2026).

New recipes get this in the queue after they are made; this is for the ones made before. For each recipe Claude
decides per unlinked line: alias to a pantry item, a swap, a question to Pål, or leave it; a published recipe only gets aliases. Then the recipe is recalculated; a
recipe with every line linked is only recalculated (as the Recalculate button), so fixes to the nutrition or the
chefs' rules reach it too.

Without --apply nothing is saved: the decisions are printed and rolled back (Claude is still called, about
0.01-0.05 USD a recipe). With --apply each recipe is committed on its own.

    SSL_CERT_FILE=... DB_PASS=... DB_BACKEND=cloudsql ... ANTHROPIC_API_KEY=... ./venv/bin/python -m scripts.fill_pantry --ids 337-360
    ... -m scripts.fill_pantry --ids 337-360 --apply

--symbols instead makes the symbol images of every item added this way that has none yet (the queue job does it
for new recipes). It saves to the bucket, so it needs GOOGLE_API_KEY (Gemini), STORAGE_BACKEND=gcs,
GCS_BUCKET_NAME and Google application default credentials (gcloud auth application-default login).

    ... GOOGLE_API_KEY=... STORAGE_BACKEND=gcs GCS_BUCKET_NAME=thelazychef-assets ./venv/bin/python -m scripts.fill_pantry --symbols

--looks "flatbrød=thin rectangular crispbread sheets, stacked" (with the same environment as --symbols) sets how
one pantry item looks (image_notes, which the symbol prompt uses) and makes its symbol again.

    ... -m scripts.fill_pantry --looks "flatbrød=thin rectangular crispbread sheets, stacked, pale brown"

--nutrition "name=calories:121,fat:4.12,..." sets one pantry item's values per 100 g (fields in NUTRITION; kJ follows the
calories) and recalculates every v2 recipe that uses it, and the recipes in --ids too, published ones included. No AI,
nothing paid. Without --apply it prints each recipe's calories a serving before and after, and saves nothing.

    ... -m scripts.fill_pantry --nutrition "chicken thigh=calories:121,protein:19.7,fat:4.12,fat_saturated:1.1" --ids 387,388
"""
import argparse
import getpass
import os

NUTRITION = {'calories': 'calories_per_100g', 'protein': 'protein_per_100g', 'carbs': 'carbs_per_100g', 'fat': 'fat_per_100g',
             'fat_saturated': 'fat_saturated_per_100g', 'sugar': 'sugar_per_100g', 'fiber': 'fiber_per_100g',
             'sodium_mg': 'sodium_mg_per_100g'}


def parse_nutrition(text):
    """'chicken thigh=calories:121,fat:4.12' -> ('chicken thigh', {'calories_per_100g': 121.0, 'fat_per_100g': 4.12})"""
    if '=' not in text:
        raise ValueError('--nutrition takes "name=field:value,field:value"')
    name, rest = (x.strip() for x in text.split('=', 1))
    values = {}
    for part in (p.strip() for p in rest.split(',') if p.strip()):
        field, _, value = part.partition(':')
        if field.strip() not in NUTRITION:
            raise ValueError(f'unknown field {field.strip()!r}; known: {", ".join(NUTRITION)}')
        values[NUTRITION[field.strip()]] = float(value)
    if not name or not values:
        raise ValueError('--nutrition takes "name=field:value,field:value"')
    return name, values


def set_nutrition(ing, values, ids=()):
    """Set the item's values and recalculate every v2 recipe that uses it, and those in ids. Returns the item's old
    values and [(recipe, kcal a serving before, after)]. The caller commits or rolls back."""
    from database.models import Recipe, RecipeLine, db
    from services.recipe_v2 import nutrition
    from services.recipe_v2.generate import recalculate

    used = db.select(RecipeLine.recipe_id).where(RecipeLine.ingredient_id == ing.id)
    recipes = db.session.execute(db.select(Recipe).where(
        Recipe.schema_version == 2, db.or_(Recipe.id.in_(used), Recipe.id.in_(list(ids)))).order_by(Recipe.id)).scalars().all()
    before = {f: getattr(ing, f) for f in values}
    kcal = [(nutrition.per_serving(r) or {}).get('kcal') for r in recipes]
    for field, value in values.items():
        setattr(ing, field, value)
    if 'calories_per_100g' in values:
        ing.kj_per_100g = round(values['calories_per_100g'] * 4.184, 1)
    db.session.flush()
    rows = []
    for recipe, was in zip(recipes, kcal):
        recalculate(recipe)
        rows.append((recipe, was, (nutrition.per_serving(recipe) or {}).get('kcal')))
    return before, rows


def parse_ids(text):
    """'337-340,345' -> [337, 338, 339, 340, 345]"""
    ids = []
    for part in (p.strip() for p in text.split(',') if p.strip()):
        if '-' in part:
            a, b = (int(x) for x in part.split('-', 1))
            ids += range(a, b + 1)
        else:
            ids.append(int(part))
    return ids


def main():
    ap = argparse.ArgumentParser(description='Fill the pantry for saved v2 recipes with unlinked lines.')
    ap.add_argument('--ids', help='recipe ids: 337-360 or 337,340')
    ap.add_argument('--apply', action='store_true', help='save; without it the decisions are only printed')
    ap.add_argument('--symbols', action='store_true', help='make the missing symbol images of the items added here')
    ap.add_argument('--looks', help='"name=how it looks": set the image notes of one item and make its symbol again')
    ap.add_argument('--nutrition', help='"name=calories:121,fat:4.12": set one item\'s values and recalculate the recipes using it')
    args = ap.parse_args()
    if not args.ids and not args.symbols and not args.looks and not args.nutrition:
        ap.error('give --ids, --symbols, --looks or --nutrition')
    if args.nutrition:
        try:
            nutrition_of = parse_nutrition(args.nutrition)
        except ValueError as e:
            ap.error(str(e))
    if args.looks and '=' not in args.looks:
        ap.error('--looks takes "name=how it looks"')
    args.symbols = args.symbols or bool(args.looks)

    if os.getenv('DB_BACKEND', 'local').lower() == 'cloudsql' and not os.getenv('DB_PASS'):
        os.environ['DB_PASS'] = getpass.getpass('Database password (not shown, not stored): ')
    if args.symbols and (not os.getenv('GOOGLE_API_KEY') or os.getenv('STORAGE_BACKEND') != 'gcs'):
        ap.error('--symbols needs GOOGLE_API_KEY and STORAGE_BACKEND=gcs with GCS_BUCKET_NAME')
    os.environ.setdefault('GOOGLE_API_KEY', 'not-used')  # app.py wants one; without --symbols nothing calls Google

    from app import app, db
    from database.models import Ingredient, Recipe
    from services.recipe_v2 import pantry_fill
    from services.recipe_v2.generate import recalculate

    with app.app_context():
        if args.nutrition:
            from services.ingredient_service import normalize_alias

            name, values = nutrition_of
            ing = db.session.execute(db.select(Ingredient).where(db.func.lower(Ingredient.name) == normalize_alias(name))
                                     ).scalars().first()
            if ing is None:
                print(f'No pantry item called {name!r}')
                return
            before, rows = set_nutrition(ing, values, parse_ids(args.ids) if args.ids else ())
            print(f'{ing.name} (id {ing.id}), per 100 g: ' + ', '.join(f'{f} {before[f]} -> {values[f]}' for f in values))
            for recipe, was, now in rows:
                print(f'#{recipe.id} {recipe.status:8} {recipe.title[:50]:50} kcal a serving {was} -> {now}')
            if args.apply:
                db.session.commit()
            else:
                db.session.rollback()
            print(f'\n{len(rows)} recipes recalculated, no AI. ' + ('Saved.' if args.apply else 'Nothing saved: run again with --apply to keep it.'))
            return
        if args.looks:
            from routes._shared import get_storage
            from services.ingredient_service import normalize_alias

            name, looks = (x.strip() for x in args.looks.split('=', 1))
            ing = db.session.execute(db.select(Ingredient).where(db.func.lower(Ingredient.name) == normalize_alias(name))
                                     ).scalars().first()
            if ing is None:
                print(f'No pantry item called {name!r}')
                return
            ing.image_notes = looks
            made = pantry_fill.make_symbols([ing], get_storage())
            db.session.commit()
            print(f'{ing.name}: image notes set; ' + (f'new symbol {ing.image_url}' if made else 'the symbol failed, see above'))
            return
        if args.symbols:
            from routes._shared import get_storage

            items = pantry_fill.without_symbol()
            made = pantry_fill.make_symbols(items, get_storage())
            db.session.commit()
            print(f'Symbol images made for {len(made)} of {len(items)}: {", ".join(made) or "-"}')
            return
        recipes = db.session.execute(db.select(Recipe).where(
            Recipe.id.in_(parse_ids(args.ids)), Recipe.schema_version == 2).order_by(Recipe.id)).scalars().all()
        cost = 0.0
        for recipe in recipes:
            if not pantry_fill.unlinked(recipe):
                recalculate(recipe)
                print(f'#{recipe.id} {recipe.title}: every line is linked, recalculated')
            else:
                result = pantry_fill.fill(recipe)
                cost += result['cost_usd']
                print(f'#{recipe.id} {recipe.title}')
                for note in result['notes']:
                    print(f'   {note}')
            if args.apply:
                db.session.commit()
            else:
                db.session.rollback()
        print(f'\n{len(recipes)} recipes, about {cost:.2f} USD with Claude. '
              + ('Saved.' if args.apply else 'Nothing saved: run again with --apply to keep it.'))


if __name__ == '__main__':
    main()
