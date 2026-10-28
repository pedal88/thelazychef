"""Fill the pantry for saved v2 recipes whose lines are not all linked (services/recipe_v2/pantry_fill.py, 27.10.2026).

New recipes get this in the queue after they are made; this is for the ones made before. For each recipe Claude
decides per unlinked line: alias to a pantry item, a new item, or leave it. Then the recipe is recalculated; a
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
"""
import argparse
import getpass
import os


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
    args = ap.parse_args()
    if not args.ids and not args.symbols and not args.looks:
        ap.error('give --ids, --symbols or --looks')
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
