"""Fill the pantry for saved v2 recipes whose lines are not all linked (services/recipe_v2/pantry_fill.py, 27.10.2026).

New recipes get this in the queue after they are made; this is for the ones made before. For each recipe Claude
decides per unlinked line: alias to a pantry item, a new pending item, or leave it. Then the recipe is recalculated.

Without --apply nothing is saved: the decisions are printed and rolled back (Claude is still called, about
0.01-0.05 USD a recipe). With --apply each recipe is committed on its own.

    SSL_CERT_FILE=... DB_PASS=... DB_BACKEND=cloudsql ... ANTHROPIC_API_KEY=... ./venv/bin/python -m scripts.fill_pantry --ids 337-360
    ... -m scripts.fill_pantry --ids 337-360 --apply
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
    ap.add_argument('--ids', required=True, help='recipe ids: 337-360 or 337,340')
    ap.add_argument('--apply', action='store_true', help='save; without it the decisions are only printed')
    args = ap.parse_args()

    if os.getenv('DB_BACKEND', 'local').lower() == 'cloudsql' and not os.getenv('DB_PASS'):
        os.environ['DB_PASS'] = getpass.getpass('Database password (not shown, not stored): ')
    os.environ.setdefault('GOOGLE_API_KEY', 'not-used')  # app.py wants one; nothing here calls Google

    from app import app, db
    from database.models import Recipe
    from services.recipe_v2 import pantry_fill

    with app.app_context():
        recipes = db.session.execute(db.select(Recipe).where(
            Recipe.id.in_(parse_ids(args.ids)), Recipe.schema_version == 2).order_by(Recipe.id)).scalars().all()
        cost = 0.0
        for recipe in recipes:
            todo = [line.name for line in pantry_fill.unlinked(recipe)]
            if not todo:
                print(f'#{recipe.id} {recipe.title}: every line is linked')
                continue
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
