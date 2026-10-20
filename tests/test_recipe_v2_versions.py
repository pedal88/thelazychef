"""Versions of a dish by chef personas, and the public persona pages.

Claude is replaced by the recorded carbonara from the pilot, as in test_recipe_v2_routes.
"""
import json
import os
import sys
import unittest
from unittest import mock

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(ROOT)

from tests import test_recipe_v2_routes as route_tests  # noqa: E402  (sets the test environment)
from database.models import Chef, Recipe, db  # noqa: E402
from services.recipe_v2 import claude  # noqa: E402
from services.recipe_v2.persona import badges  # noqa: E402
from services.recipe_v2.view import as_text  # noqa: E402


def add_chef(chef_id):
    with open(os.path.join(ROOT, 'data', 'agents', 'chefs.json'), encoding='utf-8') as f:
        c = next(c for c in json.load(f)['chefs'] if c['id'] == chef_id)
    db.session.add(Chef(id=c['id'], name=c['name'], archetype=c['archetype'], description=c['description'],
                        image_filename='', **{k: json.dumps(c[k]) for k in ('constraints', 'diet_preferences',
                        'cooking_style', 'ingredient_logic', 'instruction_style')}))
    db.session.commit()


class VersionTests(unittest.TestCase):
    # The same app, database and admin login as the route tests, without running their tests again
    setUp, tearDown, login = (route_tests.RecipeV2RouteTests.setUp, route_tests.RecipeV2RouteTests.tearDown,
                              route_tests.RecipeV2RouteTests.login)

    def _base(self):
        """A finished v2 carbonara, made the normal way."""
        self.login()
        with mock.patch.object(claude, 'call', route_tests.fake_claude()):
            self.client.post('/new-recipe/v2', data={'source': 'Spaghetti carbonara for four'})
        return db.session.execute(db.select(Recipe)).scalar_one()

    def _version(self, of, chef_id):
        asked = []
        call = route_tests.fake_claude()
        with mock.patch.object(claude, 'call', lambda *a, **kw: asked.append(a[2]) or call(*a, **kw)):
            res = self.client.post(f'/new-recipe/v2/version/{of.id}', data={'chef_id': chef_id})
        version = db.session.execute(db.select(Recipe).order_by(Recipe.id.desc())).scalars().first()
        return res, version, asked

    def test_as_text_reads_like_a_recipe(self):
        base = self._base()
        text = as_text(base)
        self.assertTrue(text.startswith(f'{base.title}\n\nServings: 4\n\nIngredients\n- 400 g spaghetti'), text[:120])
        self.assertIn('\nMethod\n1. ', text)
        self.assertNotIn('{i', text)

    def test_a_version_is_made_by_the_chef_from_the_base_recipe(self):
        add_chef('family_cook')
        base = self._base()
        res, version, asked = self._version(base, 'family_cook')
        self.assertEqual(res.headers['Location'], f'/new-recipe/v2/{version.id}')
        self.assertEqual((version.chef_id, version.base_recipe_id, version.source_type, version.status),
                         ('family_cook', base.id, 'version', 'draft'))
        self.assertTrue(version.steps)
        self.assertEqual(version.source_input, f'Version of recipe {base.id} by The Family Cook')
        prompt = asked[0][0]['content']
        self.assertIn('THE COOK\nWrite it as The Family Cook', prompt)
        self.assertIn(f'THE RECIPE\n{base.title}\n\nServings: 4', prompt)
        # The admin sees the family on both pages
        page = self.client.get(f'/recipe/{base.id}').get_data(as_text=True)
        self.assertIn('Version by The Family Cook', page)
        self.assertIn('Make the version', page)

    def test_a_version_of_a_version_links_to_the_base_dish(self):
        add_chef('family_cook')
        add_chef('speezy_gonzales')
        base = self._base()
        _, first, _ = self._version(base, 'family_cook')
        _, second, _ = self._version(first, 'speezy_gonzales')
        self.assertEqual(second.base_recipe_id, base.id)
        self.assertEqual(sorted(r.id for r in base.versions), [first.id, second.id])

    def test_a_version_needs_a_known_chef(self):
        base = self._base()
        res, last, _ = self._version(base, 'nobody')
        self.assertEqual(res.headers['Location'], f'/recipe/{base.id}')
        self.assertEqual(last.id, base.id)  # nothing new was made

    def test_recalculate_applies_changed_rules_without_claude(self):
        add_chef('speezy_gonzales')
        self.login()
        with mock.patch.object(claude, 'call', route_tests.fake_claude()):
            self.client.post('/new-recipe/v2', data={'source': 'Spaghetti carbonara for four', 'chef_id': 'speezy_gonzales'})
        recipe = db.session.execute(db.select(Recipe)).scalar_one()
        self.assertTrue(any(e['rule'] == 'persona' for e in recipe.validation_errors))
        page = self.client.get(f'/recipe/{recipe.id}').get_data(as_text=True)
        self.assertIn('Recalculate', page)
        # Loosen Speezy's rules in the editor, then recalculate: the notes go, and Claude is not asked
        chef = db.session.get(Chef, 'speezy_gonzales')
        chef.constraints = json.dumps({'max_total_minutes': None, 'max_cleanup': None, 'difficulties': []})
        db.session.commit()
        with mock.patch.object(claude, 'call', side_effect=AssertionError('Claude was called')):
            res = self.client.post(f'/new-recipe/v2/recalculate/{recipe.id}')
        self.assertEqual(res.headers['Location'], f'/recipe/{recipe.id}')
        db.session.refresh(recipe)
        self.assertEqual([e for e in recipe.validation_errors if e['rule'] == 'persona'], [])
        self.assertIsNotNone(recipe.prep_time_mins)

    def test_recalculate_is_for_admins_and_v2_recipes(self):
        old = Recipe(title='Old', cuisine='', difficulty='', schema_version=1)
        db.session.add(old)
        db.session.commit()
        self.assertEqual(self.client.post(f'/new-recipe/v2/recalculate/{old.id}').status_code, 302)  # to login
        self.login()
        self.assertEqual(self.client.post(f'/new-recipe/v2/recalculate/{old.id}').status_code, 400)

    def test_the_persona_pages_show_the_chefs_and_their_published_recipes(self):
        add_chef('the_green_chef')
        db.session.add(Chef(id='bare', name='Bare', archetype='', description='', image_filename=''))
        base = self._base()
        base.chef_id, base.status = 'the_green_chef', 'approved'
        db.session.commit()
        self.client.get('/logout')
        page = self.client.get('/chefs').get_data(as_text=True)
        self.assertIn('The Green Chef', page)
        self.assertIn('Vegetarian', page)
        self.assertIn('1 recipe →', page)
        self.assertNotIn('>Bare<', page)
        page = self.client.get('/chefs/the_green_chef').get_data(as_text=True)
        self.assertIn('Spaghetti carbonara', page)
        self.assertEqual(self.client.get('/chefs/nobody').status_code, 404)


def test_badges_say_the_rules_in_plain_words():
    with open(os.path.join(ROOT, 'data', 'agents', 'chefs.json'), encoding='utf-8') as f:
        chefs = {c['id']: c for c in json.load(f)['chefs']}
    assert badges(chefs['speezy_gonzales']) == ['Under 20 minutes', 'Little washing-up', 'Easy']
    assert badges(chefs['family_cook']) == ['Under 45 minutes', 'Mild', 'Little washing-up', 'Easy or Medium']
    assert badges(chefs['the_green_chef']) == ['Vegetarian']


if __name__ == '__main__':
    unittest.main()
