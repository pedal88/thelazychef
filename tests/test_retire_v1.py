"""Retiring the v1 recipes (scripts/retire_v1.py): the batch lines, and archive and restore."""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(ROOT)

from tests import test_recipe_v2_view as view_tests  # noqa: E402  (sets the test environment)
from database.models import Recipe, RecipeDiet, db  # noqa: E402
from scripts import retire_v1  # noqa: E402


def row(**k):
    base = {'id': 1, 'title': 'Teriyaki Beef Wok', 'status': 'approved', 'cuisine': 'Japanese', 'chef_id': None,
            'servings': 4, 'source': None, 'diets': []}
    return {**base, **k}


class LineTests(unittest.TestCase):
    def test_a_title_becomes_an_idea_with_cuisine_and_servings(self):
        self.assertEqual(retire_v1.line_of(row()), (None, 'Teriyaki Beef Wok, Japanese, serves 4'))

    def test_old_chefs_and_diets_become_chefs_and_settings(self):
        _, line = retire_v1.line_of(row(chef_id='family_cook', diets=['vegan']))
        self.assertEqual(line, 'Teriyaki Beef Wok, Japanese, serves 4 | smart | kid, vegetarian')
        _, line = retire_v1.line_of(row(chef_id='the_minimalist', cuisine='Other'))
        self.assertEqual(line, 'Teriyaki Beef Wok, serves 4 | minimalist')

    def test_a_recipe_from_a_link_is_its_link(self):
        note, line = retire_v1.line_of(row(source='https://www.tiktok.com/@cook/video/1', chef_id='the_smart_cook'))
        self.assertEqual((note, line), ('# Teriyaki Beef Wok', 'https://www.tiktok.com/@cook/video/1 | smart'))

    def test_drafts_are_notes(self):
        md = retire_v1.markdown([row(), row(id=2, title='Old draft', status='draft')])
        self.assertIn('\nTeriyaki Beef Wok, Japanese, serves 4\n', md)
        self.assertIn('# [draft] Old draft', md)


class ArchiveTests(unittest.TestCase):
    setUp, tearDown = view_tests.RecipeV2ViewTests.setUp, view_tests.RecipeV2ViewTests.tearDown

    def test_export_archive_and_restore(self):
        old = Recipe(title='Old stew', status='approved', cuisine='Nordic', difficulty='', schema_version=1)
        draft = Recipe(title='Old draft', status='draft', cuisine='', difficulty='', schema_version=1)
        db.session.add_all([old, draft])
        db.session.flush()
        db.session.add(RecipeDiet(recipe_id=old.id, diet='vegetarian'))
        db.session.commit()
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            retire_v1.export(out)
            plan = json.loads((out / 'plan.json').read_text())
            self.assertEqual({p['title'] for p in plan}, {'Old stew', 'Old draft'})  # only v1, not the v2 fixtures
            self.assertIn('\nOld stew, Nordic, serves 4 |  | vegetarian\n', (out / 'v1-recipes.md').read_text())  # no chef: the page's
            draft.status = 'rejected'  # changed since the plan: left alone
            db.session.commit()
            retire_v1.change(out / 'plan.json')
            self.assertEqual((db.session.get(Recipe, old.id).status, db.session.get(Recipe, draft.id).status), ('archived', 'rejected'))
            self.assertEqual(db.session.get(Recipe, self.ids['carbonara']).status, 'approved')  # v2 untouched
            retire_v1.change(out / 'plan.json', restore=True)
            db.session.expire_all()  # the script wrote in its own session
            self.assertEqual(db.session.get(Recipe, old.id).status, 'approved')


if __name__ == '__main__':
    unittest.main()
