"""Make the symbols of the galaxies' concepts (28.10.2026), in the style of the ingredient symbols.

--kind ingredient_category (the default): the main ingredient categories, each a small still life of three typical
things (data/constraints/category_symbols.json), for the ingredient galaxy. --kind cuisine: the cuisines, each a
dish it is known for (data/constraints/cuisine_symbols.json), for the recipe galaxy. Each is saved to the bucket
(pantry/categories or pantry/cuisines) and kept in concept_visual under its kind. Those that have a symbol are
skipped unless named with --only, or all made again with --all (older symbols may be in concept_visual from
before). About 0.04 USD each.

It saves to the bucket, so it needs GOOGLE_API_KEY (Gemini), STORAGE_BACKEND=gcs, GCS_BUCKET_NAME and Google
application default credentials, as scripts/fill_pantry.py --symbols.

    SSL_CERT_FILE=... DB_PASS=... DB_BACKEND=cloudsql ... GOOGLE_API_KEY=... STORAGE_BACKEND=gcs GCS_BUCKET_NAME=thelazychef-assets ./venv/bin/python -m scripts.category_symbols
    ... -m scripts.category_symbols --only "vegetables,meat"
    ... -m scripts.category_symbols --kind cuisine --all
"""
import argparse
import getpass
import os
import re
import time

FOLDERS = {'ingredient_category': 'pantry/categories', 'cuisine': 'pantry/cuisines'}


def main():
    ap = argparse.ArgumentParser(description="Make the galaxies' category and cuisine symbols.")
    ap.add_argument('--kind', choices=sorted(FOLDERS), default='ingredient_category')
    ap.add_argument('--only', help='comma-separated names to make (again), e.g. "vegetables,meat" or "Nordic"')
    ap.add_argument('--all', action='store_true', help='make every one again, also those that have a symbol')
    args = ap.parse_args()
    if not os.getenv('GOOGLE_API_KEY') or os.getenv('STORAGE_BACKEND') != 'gcs':
        ap.error('needs GOOGLE_API_KEY and STORAGE_BACKEND=gcs with GCS_BUCKET_NAME')
    if os.getenv('DB_BACKEND', 'local').lower() == 'cloudsql' and not os.getenv('DB_PASS'):
        os.environ['DB_PASS'] = getpass.getpass('Database password (not shown, not stored): ')

    from app import app, db
    from database.models import ConceptVisual, Ingredient, Recipe
    from routes._shared import get_storage
    from services.ingredient_symbols import concept_symbol, web_image

    kind = args.kind
    with app.app_context():
        if kind == 'cuisine':
            from schemas.recipe_v2 import CUISINES
            used = list(CUISINES)
            used += sorted(c for c, in db.session.execute(db.select(Recipe.cuisine).distinct()
                                                          .where(Recipe.status == 'approved')).all() if c and c not in used)
        else:
            used = sorted(c for c, in db.session.execute(db.select(Ingredient.main_category).distinct()
                                                          .where(Ingredient.status == 'active')).all() if c)
        only = [c.strip() for c in (args.only or '').split(',') if c.strip()]
        storage = get_storage()
        made, failed = [], []
        for cat in only or used:
            row = db.session.execute(db.select(ConceptVisual).filter_by(concept_type=kind, concept_name=cat)).scalar()
            if row and row.image_url and not only and not args.all:
                continue
            try:
                png, _prompt, _meta = concept_symbol(kind, cat)
            except Exception as e:  # noqa: BLE001 - reported, the others go on
                failed.append(f'{cat} ({e})')
                continue
            slug = re.sub(r'[^a-z0-9]+', '_', cat.lower()).strip('_')
            url = storage.save(web_image(png), f'{slug}_{int(time.time())}.webp', FOLDERS[kind])
            if row is None:
                row = ConceptVisual(concept_type=kind, concept_name=cat)
                db.session.add(row)
            row.image_url = url
            db.session.commit()
            made.append(cat)
            print(f'{cat}: {url}')
        print(f'\nMade {len(made)}' + (f'; failed: {", ".join(failed)}' if failed else '') + '.')


if __name__ == '__main__':
    main()
