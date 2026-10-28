"""The taxonomy cleanup migration (migrations/versions/b3d7e9f1a2c4_taxonomy_cleanup.py), run on a test database."""
import importlib.util
import json
import os
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(ROOT)

os.environ['DB_BACKEND'] = 'local'
os.environ['DATABASE_URL'] = 'sqlite://'
os.environ['STORAGE_BACKEND'] = 'local'
os.environ.setdefault('SECRET_KEY', 'test-secret')
os.environ.setdefault('GOOGLE_API_KEY', 'test-key')

from alembic.migration import MigrationContext  # noqa: E402
from alembic.operations import Operations  # noqa: E402

from app import app  # noqa: E402
from database.models import Ingredient, Recipe, db  # noqa: E402
from services.recipe_v2.store import save_v2  # noqa: E402

spec = importlib.util.spec_from_file_location(
    'taxonomy', os.path.join(ROOT, 'migrations', 'versions', 'b3d7e9f1a2c4_taxonomy_cleanup.py'))
migration = importlib.util.module_from_spec(spec)
spec.loader.exec_module(migration)


class TaxonomyMigrationTests(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        self.ctx = app.app_context()
        self.ctx.push()
        db.drop_all()
        db.create_all()

        def ing(food_id, name, main, sub, status='active'):
            db.session.add(Ingredient(food_id=food_id, name=name, main_category=main, sub_category=sub, status=status))
        ing('1', 'cod', 'fish and seafood', 'fish')
        ing('2', 'Jasmine rice', 'cereal grains and pasta', 'refined grains')
        ing('3', 'butter', 'fats and oils', 'animal fats')
        ing('4', 'chicken stock', 'sauces and condiments', 'other sauces & condiments')
        ing('5', 'shrimps', 'meat', 'pork')  # not where the migration expects it: left alone
        ing('6', 'canned tuna', 'canned and preserved', 'canned\xa0fish\xa0& seafood')
        ing('7', 'carbonara', 'sauces and condiments', 'cream & cheese sauces')
        ing('8', 'lemon juice', 'fruit and fruit products', 'juices')
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def run_migration(self, step):
        with db.engine.begin() as conn:
            migration.op = Operations(MigrationContext.configure(conn))
            step()
        db.session.expire_all()

    def place(self, name):
        i = db.session.execute(db.select(Ingredient).where(db.func.lower(Ingredient.name) == name.lower())).scalar_one()
        return i.main_category, i.sub_category, i.status

    def test_upgrade_moves_what_it_expects_and_downgrade_moves_it_back(self):
        self.run_migration(migration.upgrade)
        self.assertEqual(self.place('cod')[:2], ('fish and seafood', 'white fish'))
        self.assertEqual(self.place('Jasmine rice')[:2], ('cereal grains and pasta', 'rice'))  # names match lower case
        self.assertEqual(self.place('butter')[:2], ('dairy and egg', 'butter and spreads'))
        self.assertEqual(self.place('chicken stock')[:2], ('sauces and condiments', 'stocks & broths'))
        self.assertEqual(self.place('lemon juice')[:2], ('fruit and fruit products', 'citrus fruits'))
        self.assertEqual(self.place('shrimps')[:2], ('meat', 'pork'))
        self.assertEqual(self.place('canned tuna')[:2], ('canned and preserved', 'canned fish & seafood'))
        self.assertEqual(self.place('carbonara')[2], 'inactive')

        self.run_migration(migration.downgrade)
        self.assertEqual(self.place('cod')[:2], ('fish and seafood', 'fish'))
        self.assertEqual(self.place('butter')[:2], ('fats and oils', 'animal fats'))
        self.assertEqual(self.place('carbonara')[2], 'active')

    def test_an_ingredient_a_recipe_uses_stays_active(self):
        carbonara = db.session.execute(db.select(Ingredient).where(Ingredient.name == 'carbonara')).scalar_one()
        with open(os.path.join(ROOT, 'data', 'pilot_v2', 'fasit', 'carbonara.json'), encoding='utf-8') as f:
            data = json.load(f)
        recipe = Recipe(title='Pasta', cuisine='Italian', difficulty='Simplistic', status='draft')
        db.session.add(recipe)
        save_v2(recipe, data, {'i1': carbonara.id})
        db.session.commit()
        self.run_migration(migration.upgrade)
        self.assertEqual(self.place('carbonara')[2], 'active')

    def test_every_move_ends_in_the_catalog(self):
        with open(os.path.join(ROOT, 'data', 'constraints', 'categories.json'), encoding='utf-8') as f:
            subs = json.load(f)['sub_categories']
        for name, _, _, main, sub in migration.MOVES:
            self.assertIn(sub, subs[main], name)


if __name__ == '__main__':
    unittest.main()
