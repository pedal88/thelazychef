"""Make the symbols of the main ingredient categories for the ingredient galaxy (28.10.2026).

Each is a small still life of three typical things (data/constraints/category_symbols.json), drawn with the
ingredient symbol prompt, saved to the bucket (pantry/categories) and kept in concept_visual with concept_type
"ingredient_category". Categories that have a symbol are skipped unless named with --only. About 0.04 USD each.

It saves to the bucket, so it needs GOOGLE_API_KEY (Gemini), STORAGE_BACKEND=gcs, GCS_BUCKET_NAME and Google
application default credentials, as scripts/fill_pantry.py --symbols.

    SSL_CERT_FILE=... DB_PASS=... DB_BACKEND=cloudsql ... GOOGLE_API_KEY=... STORAGE_BACKEND=gcs GCS_BUCKET_NAME=thelazychef-assets ./venv/bin/python -m scripts.category_symbols
    ... -m scripts.category_symbols --only "vegetables,meat"
"""
import argparse
import getpass
import os
import re
import time

TYPE = 'ingredient_category'


def main():
    ap = argparse.ArgumentParser(description='Make the main ingredient category symbols.')
    ap.add_argument('--only', help='comma-separated categories to make (again), e.g. "vegetables,meat"')
    args = ap.parse_args()
    if not os.getenv('GOOGLE_API_KEY') or os.getenv('STORAGE_BACKEND') != 'gcs':
        ap.error('needs GOOGLE_API_KEY and STORAGE_BACKEND=gcs with GCS_BUCKET_NAME')
    if os.getenv('DB_BACKEND', 'local').lower() == 'cloudsql' and not os.getenv('DB_PASS'):
        os.environ['DB_PASS'] = getpass.getpass('Database password (not shown, not stored): ')

    from app import app, db
    from database.models import ConceptVisual, Ingredient
    from routes._shared import get_storage
    from services.ingredient_symbols import category_symbol, web_image

    with app.app_context():
        used = sorted(c for c, in db.session.execute(db.select(Ingredient.main_category).distinct()
                                                      .where(Ingredient.status == 'active')).all() if c)
        only = [c.strip() for c in (args.only or '').split(',') if c.strip()]
        storage = get_storage()
        made, failed = [], []
        for cat in only or used:
            row = db.session.execute(db.select(ConceptVisual).filter_by(concept_type=TYPE, concept_name=cat)).scalar()
            if row and row.image_url and not only:
                continue
            try:
                png, _prompt, _meta = category_symbol(cat)
            except Exception as e:  # noqa: BLE001 - reported, the others go on
                failed.append(f'{cat} ({e})')
                continue
            slug = re.sub(r'[^a-z0-9]+', '_', cat.lower()).strip('_')
            url = storage.save(web_image(png), f'{slug}_{int(time.time())}.webp', 'pantry/categories')
            if row is None:
                row = ConceptVisual(concept_type=TYPE, concept_name=cat)
                db.session.add(row)
            row.image_url = url
            db.session.commit()
            made.append(cat)
            print(f'{cat}: {url}')
        print(f'\nMade {len(made)}' + (f'; failed: {", ".join(failed)}' if failed else '') + '.')


if __name__ == '__main__':
    main()
