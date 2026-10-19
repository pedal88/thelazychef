"""The pantry review script: sorting, gaps and the review sheet, with Claude replaced by a stand-in."""
import csv
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

from scripts import pantry_review  # noqa: E402

ROWS = [
    {'id': 1, 'name': 'basil', 'main_category': 'Produce', 'sub_category': 'Herbs'},
    {'id': 2, 'name': 'thai basil', 'main_category': 'Produce', 'sub_category': 'Herbs'},
    {'id': 3, 'name': 'cabernet sauvignon', 'main_category': 'Beverages', 'sub_category': 'Wine'},
    {'id': 4, 'name': 'spring onions', 'main_category': 'Produce', 'sub_category': 'Vegetables'},
    {'id': 5, 'name': 'scallion', 'main_category': 'Produce', 'sub_category': 'Vegetables'},
]
SORTED = {'items': [
    {'id': 1, 'label': 'core', 'of': '', 'base': '', 'reason': 'everyday herb'},
    {'id': 2, 'label': 'long_tail', 'of': '', 'base': 'basil', 'reason': 'thai dishes'},
    {'id': 3, 'label': 'not_cooking', 'of': '', 'base': '', 'reason': 'a wine to drink'},
    {'id': 4, 'label': 'core', 'of': '', 'base': 'lemongrass', 'reason': 'base is not in the pantry'},
    {'id': 5, 'label': 'duplicate', 'of': 'spring onions', 'base': '', 'reason': 'same thing'},
    {'id': 99, 'label': 'core', 'of': '', 'base': '', 'reason': 'not asked for'},
]}
GAPS = {'new': [
    {'name': 'fresh ginger', 'main_category': 'Produce', 'sub_category': 'Vegetables', 'base': '', 'cuisines': ['thai', 'indian'], 'why': 'aromatic'},
    {'name': 'Basil', 'main_category': 'Produce', 'sub_category': 'Herbs', 'base': '', 'cuisines': ['italian'], 'why': 'already there'},
], 'aliases': [
    {'alias': 'green onions', 'of': 'spring onions', 'why': 'same'},
    {'alias': 'vegetable oil', 'of': 'canola oil', 'why': 'target is missing'},
]}


def fake(answer, seen=None):
    def call(model, effort, messages, system=None, schema=None):
        if seen is not None:
            seen.append({'system': system, 'user': messages[0]['content'], 'schema': schema})
        msg = SimpleNamespace(content=[SimpleNamespace(type='text', text=json.dumps(answer))], stop_reason='end_turn', model=model)
        return msg, {'cost_usd': 0.01}
    return call


class PantryReviewTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.run = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_classify_keeps_only_asked_ids_and_names_from_the_pantry(self):
        seen = []
        done = pantry_review.classify(self.run, ROWS, call=fake(SORTED, seen), workers=1)
        self.assertEqual(sorted(done), ['1', '2', '3', '4', '5'])
        self.assertEqual(done['2']['base'], 'basil')
        self.assertEqual(done['4']['base'], '')  # lemongrass is not in the pantry
        self.assertIn('not in the pantry', done['4']['reason'])
        self.assertIn('5 | scallion', seen[0]['user'])
        self.assertIn('3 | cabernet sauvignon | Beverages / Wine', seen[0]['system'])
        self.assertIn('NOT A COOKING INGREDIENT', seen[0]['system'])
        self.assertEqual(json.loads((self.run / 'classify.json').read_text()), done)

    def test_classify_resumes_without_asking_again(self):
        pantry_review.classify(self.run, ROWS, call=fake(SORTED), workers=1)

        def broken(*args, **kwargs):
            raise AssertionError('called again')
        pantry_review.classify(self.run, ROWS, call=broken, workers=1)

    def test_gaps_drop_what_exists_and_aliases_to_missing_entries(self):
        pantry_review.classify(self.run, ROWS, call=fake(SORTED), workers=1)
        seen = []
        data = pantry_review.gaps(self.run, ROWS, call=fake(GAPS, seen))
        self.assertEqual([n['name'] for n in data['new']], ['fresh ginger'])
        self.assertEqual([a['alias'] for a in data['aliases']], ['green onions'])
        self.assertIn('thai basil | long_tail', seen[0]['system'])
        self.assertIn('Produce / Herbs', seen[0]['system'])

    def test_review_sheet_has_every_group_and_the_proposals(self):
        pantry_review.classify(self.run, ROWS, call=fake(SORTED), workers=1)
        pantry_review.gaps(self.run, ROWS, call=fake(GAPS))
        page = pantry_review.review(self.run, ROWS).read_text()
        for words in ('Not a cooking ingredient', 'Duplicates', 'Long tail', 'fresh ginger', 'green onions', 'Export decisions'):
            self.assertIn(words, page)
        self.assertLess(page.index('cabernet sauvignon'), page.index('thai basil'))  # inactive first, long tail last

    def decisions(self, **changes):
        items = {str(i['id']): {k: i[k] for k in ('label', 'of', 'base')} for i in SORTED['items'] if i['id'] != 99}
        items['4']['base'] = ''
        for rid, change in changes.items():
            items[rid].update(change)
        return {'items': items, 'new': [dict(GAPS['new'][0], base='basil')],
                'aliases': [GAPS['aliases'][0], {'alias': 'scallion', 'of': 'spring onions', 'why': ''}]}

    def test_plan_follows_duplicates_and_refuses_a_loop(self):
        rows = [dict(r, food_id=f'00000{r["id"]}') for r in ROWS]
        p = pantry_review.plan(rows, self.decisions())
        self.assertEqual(p['tiers'], {'000001': 'core', '000002': 'long_tail', '000004': 'core'})
        self.assertEqual(p['inactive'], ['000003'])
        self.assertEqual(p['merge'], {'000005': ('000004', True)})
        self.assertEqual(p['bases'], {'000002': '000001'})
        self.assertEqual(p['new'], [('fresh ginger', 'Produce', 'Vegetables', '000001')])
        self.assertEqual(p['aliases'], [('green onions', '000004'), ('scallion', '000004')])
        loop = self.decisions(**{'4': {'label': 'duplicate', 'of': 'scallion'}})
        with self.assertRaises(SystemExit):
            pantry_review.plan(rows, loop)

    def test_the_migration_runs_up_and_down_without_deleting(self):
        import importlib.util

        from alembic.migration import MigrationContext
        from alembic.operations import Operations
        import sqlalchemy as sa
        from database.models import Ingredient, IngredientAlias, RecipeIngredient, Recipe, db

        rows = [dict(r, food_id=f'00000{r["id"]}') for r in ROWS]
        decisions = self.decisions(**{'5': {'alias': False}})
        out = pantry_review.apply(self.run, rows, decisions, 'd232f75eb691', versions=self.run)
        spec = importlib.util.spec_from_file_location('m', out)
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)

        engine = sa.create_engine('sqlite://')
        db.metadata.create_all(engine, tables=[t for t in db.metadata.sorted_tables if t.name in (
            'ingredient', 'ingredient_alias', 'recipe', 'recipe_ingredient', 'recipe_line', 'recipe_step', 'recipe_component')])
        with engine.begin() as conn:
            for r in rows:
                conn.execute(sa.insert(Ingredient).values(id=r['id'], food_id=r['food_id'], name=r['name'], status='active'))
            conn.execute(sa.insert(Recipe).values(id=1, title='x', cuisine='', difficulty='', status='draft'))
            conn.execute(sa.insert(RecipeIngredient).values(recipe_id=1, ingredient_id=5, amount=1, unit='pc'))

            def run(step):
                with Operations.context(MigrationContext.configure(conn)):
                    step()

            run(m.upgrade)
            status = dict(conn.execute(sa.select(Ingredient.name, Ingredient.status)).all())
            self.assertEqual((status['cabernet sauvignon'], status['scallion'], status['fresh ginger']), ('inactive', 'inactive', 'active'))
            self.assertEqual(conn.execute(sa.select(RecipeIngredient.ingredient_id)).scalar(), 4)
            aliases = dict(conn.execute(sa.select(IngredientAlias.name, IngredientAlias.ingredient_id)).all())
            self.assertEqual(aliases, {'green onions': 4, 'scallion': 4})  # from gaps; the merge itself adds none here
            ginger = conn.execute(sa.select(Ingredient).where(Ingredient.name == 'fresh ginger')).one()
            self.assertEqual((ginger.food_id, ginger.tier, ginger.base_ingredient_id), ('000006', 'core', 1))

            run(m.downgrade)
            self.assertEqual(set(conn.execute(sa.select(Ingredient.status)).scalars()), {'active'})
            self.assertEqual(conn.execute(sa.select(sa.func.count()).select_from(Ingredient)).scalar(), 5)
            self.assertEqual(conn.execute(sa.select(sa.func.count()).select_from(IngredientAlias)).scalar(), 0)
            self.assertEqual(set(conn.execute(sa.select(Ingredient.tier)).scalars()), {None})

    def test_the_csv_from_the_symbols_export_is_read(self):
        path = self.run / 'ingredients.csv'
        with open(path, 'w', newline='') as f:
            w = csv.DictWriter(f, fieldnames=['id', 'food_id', 'name', 'main_category', 'sub_category'])
            w.writeheader()
            w.writerow({'id': '7', 'food_id': '\\N', 'name': 'salt', 'main_category': 'Pantry', 'sub_category': ''})
        self.assertEqual(pantry_review.read_csv(path), [{'id': 7, 'food_id': None, 'name': 'salt', 'main_category': 'Pantry', 'sub_category': None}])


if __name__ == '__main__':
    unittest.main()
