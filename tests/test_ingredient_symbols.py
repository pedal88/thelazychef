"""Ingredient symbols: the prompt, and the batch flow generate, review, decide, promote.

A fake generator stands in for the image model, nothing is uploaded, and
the written migration runs against an in-memory SQLite table.
"""
import importlib.util
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
os.environ.setdefault('GOOGLE_API_KEY', 'test-key')

import sqlalchemy as sa  # noqa: E402
from alembic.migration import MigrationContext  # noqa: E402
from alembic.operations import Operations  # noqa: E402
from PIL import Image  # noqa: E402

from scripts import ingredient_symbols as batch  # noqa: E402
from services.ingredient_symbols import symbol_prompt  # noqa: E402

ROWS = [
    {'id': 1, 'food_id': '000001', 'name': 'garlic', 'main_category': 'vegetables', 'sub_category': 'vegetables',
     'image_form': None, 'image_notes': 'A whole bulb.', 'image_url': 'https://example.com/old/garlic.png'},
    {'id': 2, 'food_id': '000002', 'name': 'beef stock cube', 'main_category': 'pantry', 'sub_category': 'other sauces & condiments',
     'image_form': 'Show one unwrapped stock cube with nothing else, no container.', 'image_notes': None, 'image_url': None},
    {'id': 3, 'food_id': '000003', 'name': 'flour', 'main_category': 'bakery and baking', 'sub_category': 'flour',
     'image_form': None, 'image_notes': None, 'image_url': 'https://example.com/old/flour.png'},
]


def png():
    out = io.BytesIO()
    Image.new('RGB', (64, 64), 'white').save(out, 'PNG')
    return out.getvalue()


class FakeGenerator:
    def __init__(self, fail=()):
        self.fail, self.calls = set(fail), []

    def __call__(self, ing):
        self.calls.append(dict(ing))
        if ing['id'] in self.fail:
            raise RuntimeError('503 overloaded')
        return png(), symbol_prompt(ing), {'model': 'fake'}


class SymbolPromptTests(unittest.TestCase):
    def test_form_overrides_the_category_rule(self):
        prompt = symbol_prompt(ROWS[1])
        self.assertIn('unwrapped stock cube', prompt)
        self.assertNotIn('cork stopper', prompt)

    def test_category_rule_and_notes(self):
        self.assertIn('paper bag', symbol_prompt(ROWS[2]))
        self.assertIn('A whole bulb.', symbol_prompt(ROWS[0]))


class BatchTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.run = Path(self.tmp.name) / 'symbols-test'
        self.rows = [dict(r) for r in ROWS]

    def tearDown(self):
        self.tmp.cleanup()

    def decisions(self, decisions, run=None):
        path = Path(self.tmp.name) / 'decisions.json'
        path.write_text(json.dumps({'run': run or self.run.name, 'decisions': decisions}))
        return path

    def test_read_ingredients_turns_cloud_sql_nulls_into_none(self):
        path = Path(self.tmp.name) / 'in.csv'
        path.write_text(','.join(batch.COLUMNS) + '\n7,000007,salt,spices,salts,\\N,\\N,\n')
        row = batch.read_ingredients(path)[0]
        self.assertEqual(row['id'], 7)
        self.assertIsNone(row['image_form'])
        self.assertIsNone(row['image_url'])

    def test_generate_is_resumable_and_retries_failures(self):
        fake = FakeGenerator(fail={2})
        manifest = batch.generate(self.run, self.rows, generate_one=fake, workers=1)
        self.assertEqual(len(fake.calls), 3)
        self.assertTrue((self.run / manifest['1']['image']).exists())
        self.assertIn('503', manifest['2']['error'])

        again = FakeGenerator()
        manifest = batch.generate(self.run, self.rows, generate_one=again, workers=1)
        self.assertEqual([c['id'] for c in again.calls], [2])
        self.assertIsNone(manifest['2']['error'])

    def test_review_decide_redo_promote(self):
        batch.generate(self.run, self.rows, generate_one=FakeGenerator(), workers=1)
        page = batch.review(self.run).read_text()
        self.assertEqual(page.count('class="card'), 3)
        self.assertIn('https://example.com/old/garlic.png', page)

        with self.assertRaises(SystemExit):
            batch.decide(self.run, self.decisions({}, run='symbols-other'))
        batch.decide(self.run, self.decisions({
            '1': {'status': 'approved', 'notes': ''},
            '2': {'status': 'approved', 'notes': ''},
            '3': {'status': 'rejected', 'notes': 'No bag, a heap.', 'form': 'Show a small heap of it.'},
        }))
        self.assertNotIn('flour', batch.review(self.run).read_text())

        redo = FakeGenerator()
        manifest = batch.generate(self.run, self.rows, redo=True, generate_one=redo, workers=1)
        self.assertEqual([c['id'] for c in redo.calls], [3])
        self.assertIn('No bag, a heap.', manifest['3']['prompt'])
        self.assertIn('Show a small heap of it.', manifest['3']['prompt'])
        self.assertNotIn('paper bag', manifest['3']['prompt'])
        self.assertEqual(manifest['3']['version'], 2)

        versions = Path(self.tmp.name) / 'versions'
        versions.mkdir()
        with self.assertRaises(SystemExit):
            batch.promote(self.run, upload=False, versions=versions, down='abc')  # flour not reviewed again
        batch.decide(self.run, self.decisions({'3': {'status': 'rejected', 'notes': 'Still a bag.'}}))
        path = batch.promote(self.run, upload=False, versions=versions, down='abc')
        self.assertTrue((self.run / 'web' / '000001-v1.webp').exists())
        with self.assertRaises(SystemExit):
            batch.promote(self.run, upload=False, versions=versions, down='abc')

        self.check_migration(path)

    def check_migration(self, path):
        spec = importlib.util.spec_from_file_location('symbols_migration', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertEqual(module.down_revision, 'abc')

        engine = sa.create_engine('sqlite://')
        with engine.begin() as conn:
            conn.execute(sa.text('CREATE TABLE ingredient (id INTEGER PRIMARY KEY, food_id TEXT, image_url TEXT, '
                                 'image_prompt TEXT, image_notes TEXT, image_form TEXT, has_transparent_image BOOLEAN)'))
            for r in self.rows:
                conn.execute(sa.text('INSERT INTO ingredient VALUES '
                                     '(:id, :food_id, :image_url, NULL, :image_notes, :image_form, true)'), r)
            state = lambda: {r[0]: r[1:] for r in conn.execute(sa.text(  # noqa: E731
                'SELECT id, image_url, image_notes, image_form, image_prompt IS NOT NULL FROM ingredient'))}
            before = state()
            with Operations.context(MigrationContext.configure(conn)):
                module.upgrade()
                after = state()
                self.assertEqual(after[1][0], 'https://storage.googleapis.com/thelazychef-assets/pantry/symbols/symbols-test/000001-v1.webp')
                self.assertTrue(after[1][3])
                self.assertEqual(after[3][0], 'https://example.com/old/flour.png')
                self.assertEqual(after[3][1:3], ('No bag, a heap. Still a bag.', 'Show a small heap of it.'))
                module.downgrade()
            restored = state()
        self.assertEqual({i: v[:3] for i, v in restored.items()}, {i: v[:3] for i, v in before.items()})

    def test_decide_waits_for_a_running_generate(self):
        batch.generate(self.run, self.rows, generate_one=FakeGenerator(), workers=1)
        batch.lock_path(self.run).write_text(str(os.getpid()))  # this process is alive
        with self.assertRaises(SystemExit):
            batch.decide(self.run, self.decisions({'1': {'status': 'approved'}}))
        batch.lock_path(self.run).write_text('999999999')  # a dead process: the lock is stale
        batch.decide(self.run, self.decisions({'1': {'status': 'approved'}}))
        self.assertFalse(batch.lock_path(self.run).exists())


if __name__ == '__main__':
    unittest.main()
