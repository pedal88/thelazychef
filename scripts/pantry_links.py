"""What links recipe lines to pantry items without Pål having seen it (04.11.2026). Until #292 the pantry job could alias
a line to "what a shopper would buy in its place", and an alias holds for every recipe. Until the fix after it, the
structuring model could link a line to the nearest item by itself. Both leave a line with one food's name and another's
nutrition and symbol.

The report has two parts, and costs nothing (no AI): the aliases the pantry job made, with its reason and how many lines
use them, and the lines linked to an item their name does not match. It runs in a read-only transaction.

    SSL_CERT_FILE=... DB_PASS=... DB_BACKEND=cloudsql ... ./venv/bin/python -m scripts.pantry_links

--remove takes aliases away, given as comma-separated names. Without --apply nothing is saved. Lines with that
name in recipes not yet approved are unlinked as well; run scripts.fill_pantry on the printed ids to have the pantry job
decide them. Approved recipes keep their link: saved recipes do not change by themselves.

    ... -m scripts.pantry_links --remove "yogurt butter,panini bread"
    ... -m scripts.pantry_links --remove "yogurt butter,panini bread" --apply
"""
import argparse
import contextlib
import getpass
import io
import os

from services.recipe_v2.pantry_links import report


def remove(names, aliases, recipes):
    """Delete the aliases and unlink their lines in recipes not approved. Returns (names removed, recipe ids to decide)."""
    from database.models import db

    removed = []
    for alias in aliases:
        if alias.name in names:
            removed.append(alias.name)
            db.session.delete(alias)
    ids = set()
    for recipe in recipes:
        if recipe.status == 'approved':
            continue
        for line in recipe.lines:
            if line.name.strip().lower() in removed and line.ingredient_id:
                line.ingredient = None
                ids.add(recipe.id)
    db.session.flush()
    return removed, sorted(ids)


def main():
    ap = argparse.ArgumentParser(description='Pantry links nobody has looked at: a report, and removing aliases.')
    ap.add_argument('--remove', help='comma-separated alias names to remove')
    ap.add_argument('--apply', action='store_true', help='save what --remove does; without it nothing is saved')
    args = ap.parse_args()
    if args.apply and not args.remove:
        ap.error('--apply goes with --remove')

    if os.getenv('DB_BACKEND', 'local').lower() == 'cloudsql' and not os.getenv('DB_PASS'):
        os.environ['DB_PASS'] = getpass.getpass('Database password (not shown, not stored): ')
    os.environ.setdefault('GOOGLE_API_KEY', 'not-used')  # app.py wants one; nothing here calls Google

    from sqlalchemy import text
    from app import app, db
    from database.models import IngredientAlias, Recipe

    with app.app_context():
        conn = db.session.connection()
        if not args.apply and conn.dialect.name == 'postgresql':
            conn.execute(text('SET TRANSACTION READ ONLY'))
        recipes = db.session.execute(db.select(Recipe).where(Recipe.schema_version == 2).order_by(Recipe.id)).scalars().all()
        aliases = db.session.execute(db.select(IngredientAlias)).scalars().all()
        if not args.remove:
            with contextlib.redirect_stdout(io.StringIO()):  # the matcher prints every miss
                lines = report(recipes, aliases)
            print('\n'.join(lines))
            db.session.rollback()
            return
        if not args.apply:  # the read-only transaction cannot take the trial run
            wanted = {n.strip().lower() for n in args.remove.split(',') if n.strip()}
            found = sorted(a.name for a in aliases if a.name in wanted)
            ids = sorted({r.id for r in recipes if r.status != 'approved' for line in r.lines if line.name.strip().lower() in found and line.ingredient_id})
            print(f'Would remove {found or "nothing"}, and unlink their lines in recipes {ids or "none"}. Nothing saved: add --apply.')
            db.session.rollback()
            return
        removed, ids = remove({n.strip().lower() for n in args.remove.split(',') if n.strip()}, aliases, recipes)
        db.session.commit()
        print(f'Removed {removed or "nothing"}. Unlinked lines in recipes {ids or "none"}.')
        if ids:
            print(f'Next: python -m scripts.fill_pantry --ids {",".join(map(str, ids))} --apply')


if __name__ == '__main__':
    main()
