"""scripts/clean_chef_notes.py: what the model decided leaves the public note and stays for the admin."""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(ROOT)

os.environ['DB_BACKEND'] = 'local'
os.environ['DATABASE_URL'] = 'sqlite://'
os.environ['STORAGE_BACKEND'] = 'local'
os.environ.setdefault('SECRET_KEY', 'test-secret')
os.environ.setdefault('GOOGLE_API_KEY', 'test-key')

from app import app  # noqa: E402
from database.models import Recipe, db  # noqa: E402
from scripts import clean_chef_notes as script  # noqa: E402
from services.recipe_v2 import translation  # noqa: E402
from services.recipe_v2.generate import INFORMATION  # noqa: E402

OLD = 'Water estimated at 3 l. Dry the shrimp well.'


class TestCleanChefNotes(unittest.TestCase):
    def setUp(self):
        self.ctx = app.app_context()
        self.ctx.push()
        db.drop_all()
        db.create_all()
        self.recipe = Recipe(title='Shrimp', cuisine='', difficulty='', chef_note=OLD, schema_version=2, validation_errors=[{'rule': 'pantry', 'message': 'kept'}])
        db.session.add(self.recipe)
        db.session.commit()
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def _run(self, *args, new='Dry the shrimp well.', old=OLD):
        path = Path(self.dir.name) / 'notes.json'
        path.write_text(json.dumps({str(self.recipe.id): {'old': old, 'new': new, 'moved': ['Water estimated at 3 l.']}}), encoding='utf-8')
        with mock.patch.object(sys, 'argv', ['clean_chef_notes', '--from-file', str(path), *args]), mock.patch('builtins.print'):
            script.main()
        db.session.expire_all()

    def test_without_apply_nothing_changes(self):
        self._run()
        self.assertEqual(self.recipe.chef_note, OLD)
        self.assertEqual(len(self.recipe.validation_errors), 1)

    def test_the_decision_moves_to_a_note_that_does_not_flag_the_recipe(self):
        self._run('--apply')
        self.assertEqual(self.recipe.chef_note, 'Dry the shrimp well.')
        self.assertEqual(self.recipe.validation_errors, [{'rule': 'pantry', 'message': 'kept'}, {'rule': 'estimate', 'message': 'Water estimated at 3 l.'}])
        self.assertIn('estimate', INFORMATION)

    def test_an_empty_note_is_none(self):
        self._run('--apply', new='')
        self.assertIsNone(self.recipe.chef_note)

    def test_a_note_that_has_changed_is_left_alone_so_a_second_run_changes_nothing(self):
        self._run('--apply')
        self._run('--apply')
        self.assertEqual(len(self.recipe.validation_errors), 2)

    def test_a_new_note_makes_a_translation_out_of_date(self):
        before = translation.source_hash(translation.source(self.recipe))
        self._run('--apply')
        self.assertNotEqual(translation.source_hash(translation.source(self.recipe)), before)


if __name__ == '__main__':
    unittest.main()
