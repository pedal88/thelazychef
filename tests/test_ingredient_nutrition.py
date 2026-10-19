"""Nutrition for ingredients without it: the checks, and the migration up and down."""
import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(ROOT)
os.environ.setdefault('GOOGLE_API_KEY', 'test-key')

from scripts import ingredient_nutrition as nutrition  # noqa: E402

ROWS = [{'id': '1', 'food_id': '000001', 'name': 'fresh ginger', 'main_category': 'vegetables', 'sub_category': 'root',
         'default_unit': 'g', 'data_source': 'pantry-review'},
        {'id': '2', 'food_id': '000002', 'name': 'sake', 'main_category': 'beverages', 'sub_category': 'wine',
         'default_unit': 'g', 'data_source': 'pantry-review'}]


def item(fid, unit='g', **values):
    base = dict(food_id=fid, unit=unit, grams_per_ml=1.0, alcohol_g=0, basis='USDA', calories=80, protein=1.8, fat=0.75,
                fat_saturated=0.2, carbs=17.8, sugar=1.7, fiber=2, sodium_mg=13, cholesterol_mg=0, calcium_mg=16, potassium_mg=415)
    return dict(base, **values)


class NutritionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.run = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_energy_that_does_not_fit_the_macros_is_flagged(self):
        self.assertEqual(nutrition.problems(item('1')), [])
        self.assertIn('energy', nutrition.problems(item('1', calories=300))[0])
        sake = item("2", calories=134, protein=0.5, fat=0, fat_saturated=0, carbs=5, sugar=0, alcohol_g=16)
        self.assertEqual(nutrition.problems(sake), [])  # alcohol counts
        self.assertIn('a part is larger than its whole', nutrition.problems(item('1', sugar=20)))

    def test_estimate_and_the_migration(self):
        from alembic.migration import MigrationContext
        from alembic.operations import Operations
        import sqlalchemy as sa
        from database.models import Ingredient, db

        answer = {'items': [item('000001'), item('000002', unit='ml', grams_per_ml=0.98, calories=134, protein=0.5,
                                                 fat=0, fat_saturated=0, carbs=5, sugar=0, alcohol_g=16), item("000099")]}

        def call(model, effort, messages, system=None, schema=None):
            msg = SimpleNamespace(content=[SimpleNamespace(type='text', text=json.dumps(answer))], stop_reason='end_turn')
            return msg, {'cost_usd': 0.01}

        done = nutrition.estimate(self.run, ROWS, call=call)
        self.assertEqual(sorted(done), ['000001', '000002'])
        out = nutrition.apply(self.run, ROWS, versions=self.run, down_revision='0d4f84fc82e7')
        spec = importlib.util.spec_from_file_location('m', out)
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)

        engine = sa.create_engine('sqlite://')
        db.metadata.create_all(engine, tables=[Ingredient.__table__])
        with engine.begin() as conn:
            for r in ROWS:
                conn.execute(sa.insert(Ingredient).values(food_id=r['food_id'], name=r['name'], default_unit='g',
                                                          data_source='pantry-review', status='active'))

            def run(step):
                with Operations.context(MigrationContext.configure(conn)):
                    step()

            run(m.upgrade)
            got = {r.food_id: r for r in conn.execute(sa.select(Ingredient)).all()}
            self.assertEqual((got['000001'].calories_per_100g, got['000001'].data_source, got['000001'].average_g_per_unit),
                             (80, 'ai_estimate', 1.0))
            self.assertEqual((got['000002'].default_unit, got['000002'].average_g_per_unit), ('ml', 0.98))
            run(m.downgrade)
            got = {r.food_id: r for r in conn.execute(sa.select(Ingredient)).all()}
            self.assertEqual((got['000002'].calories_per_100g, got['000002'].default_unit, got['000002'].data_source),
                             (None, 'g', 'pantry-review'))


if __name__ == '__main__':
    unittest.main()
