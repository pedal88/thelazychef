"""A local SQLite database to look at the recipe pages without production: the pantry from an ingredients export
and the five fasit recipes (data/pilot_v2/fasit), matched to it.

    python scripts/ingredient_symbols.py export --out <csv>     # the pantry from production (read only), once
    python scripts/local_db.py --csv <csv> [--db ~/code/.thelazychef-local/local.db]

Then run the app against it:

    DB_BACKEND=local DATABASE_URL=sqlite:///<db> STORAGE_BACKEND=local GOOGLE_API_KEY=x SECRET_KEY=x python app.py

It makes an admin delta@local with password pw. The export has names, categories and images, not nutrition or
tiers, so the pages show no nutrition. Keep the database outside /tmp: macOS clears files there after three days.
Nothing here is written to production, and the database is not committed.
"""
import argparse
import csv
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# The fasit recipes are in Norwegian; the pantry is in English.
NB = {'spaghetti': 'spaghetti', 'guanciale eller pancetta': 'pancetta', 'egg': 'eggs', 'eggeplomme': 'egg yolks',
      'pecorino romano': 'pecorino romano', 'sort pepper': 'ground black pepper', 'vann': 'water', 'salt': 'table salt',
      'kjøttdeig av storfe': 'ground beef', 'løk': 'onion', 'gulrot': 'carrots', 'hvitløk': 'garlic', 'olivenolje': 'olive oil',
      'tomatpuré': 'tomato paste', 'hermetiske tomater': 'canned tomatoes', 'oksebuljong': 'beef stock', 'tørket oregano': 'dried oregano',
      'smør': 'butter', 'hvetemel': 'all-purpose flour', 'helmelk': 'whole milk', 'revet muskat': 'ground nutmeg',
      'lasagneplater': 'lasagna sheets', 'revet ost': 'grated white cheese', 'parmesan': 'parmesan', 'hjertesalat': 'romaine lettuce',
      'agurk': 'cucumber', 'cherrytomater': 'cherry tomatoes', 'rødvinseddik': 'red wine vinegar', 'dijonsennep': 'dijon mustard',
      'honning': 'honey', 'kyllinglårfilet': 'chicken thigh', 'gresk yoghurt': 'greek yogurt', 'sitron': 'lemon', 'ingefær': 'fresh ginger',
      'paprikapulver': 'ground paprika', 'gurkemeie': 'ground turmeric', 'malt spisskummen': 'ground cumin', 'chilipulver': 'chili powder',
      'nøytral olje': 'canola oil', 'kremfløte': 'heavy cream', 'sukker': 'white sugar', 'frisk koriander': 'cilantro',
      'basmatiris': 'basmati rice', 'garam masala': 'garam masala', 'mørk sjokolade': 'dark chocolate', 'kakao': 'cocoa powder',
      'vaniljesukker': 'vanilla sugar', 'bakepulver': 'baking powder'}


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--csv', type=Path, required=True)
    p.add_argument('--db', type=Path, default=Path.home() / 'code' / '.thelazychef-local' / 'local.db')
    args = p.parse_args()
    args.db.parent.mkdir(parents=True, exist_ok=True)
    if args.db.exists():
        args.db.unlink()
    os.environ.update(DB_BACKEND='local', DATABASE_URL=f'sqlite:///{args.db}', STORAGE_BACKEND='local',
                      GOOGLE_API_KEY=os.environ.get('GOOGLE_API_KEY', 'not-used'), SECRET_KEY='local')

    from app import app
    from database.models import Ingredient, Recipe, User, db
    from services.recipe_v2.generate import refresh
    from services.recipe_v2.store import save_v2

    with app.app_context():
        db.create_all()
        rows = list(csv.DictReader(open(args.csv, encoding='utf-8')))
        by_name = {}
        for r in rows:
            ing = Ingredient(food_id=r['food_id'], name=r['name'], main_category=r['main_category'] or None,
                             sub_category=r['sub_category'] or None, image_url=r['image_url'] or None, status='active',
                             default_unit='g', data_source='local')
            db.session.add(ing)
            by_name[r['name'].lower()] = ing
        db.session.flush()
        user = User(email='delta@local', is_admin=True)
        user.set_password('pw')
        db.session.add(user)
        for name in ('carbonara', 'lasagne', 'tikka', 'brownies', 'burger'):
            data = json.loads((ROOT / 'data' / 'pilot_v2' / 'fasit' / f'{name}.json').read_text())
            links = {}
            for line in data['ingredients']:
                ing = by_name.get(NB.get(line['name'], line['name']).lower())
                if ing is not None:
                    links[line['local_id']] = ing.id
            recipe = Recipe(title=data['title'], cuisine='', difficulty='', status='approved', schema_version=2, language='nb')
            db.session.add(recipe)
            save_v2(recipe, data, links)
            db.session.flush()
            refresh(recipe)
            print(f"{name}: recipe {recipe.id}, {len(links)} of {len(data['ingredients'])} lines in the pantry")
        db.session.commit()
    print(f'Database: {args.db} ({len(rows)} ingredients). Admin: delta@local / pw')


if __name__ == '__main__':
    main()
