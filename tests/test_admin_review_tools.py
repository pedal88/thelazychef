"""Admin tools for reviewing recipes: the chef editor keeps rules it has no field for, the cuisine can be changed in
Recipes Management, and an alias can be added in Ingredients Management."""
import json
import os
import sys
import unittest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from tests import test_recipe_v2_view as view_tests  # noqa: E402  (sets the test environment)
from database.models import Chef, Ingredient, IngredientAlias, Recipe, db  # noqa: E402


class AdminReviewToolTests(unittest.TestCase):
    setUp, tearDown = view_tests.RecipeV2ViewTests.setUp, view_tests.RecipeV2ViewTests.tearDown

    def login(self):
        self.client.post('/login', data={'email': 'admin@test', 'password': 'pw'})

    def test_saving_a_chef_keeps_the_rules_the_editor_does_not_show(self):
        db.session.add(Chef(id='the_minimalist', name='The Minimalist', archetype='The Essentialist', description='x', image_filename='minimalist.jpg', constraints=json.dumps(
            {'max_total_minutes': 35, 'max_ingredients': 6, 'max_extra': 1, 'max_active_minutes': 15, 'forms': 'shortcut'})))
        db.session.commit()
        self.login()
        page = self.client.get('/admin/chefs').get_data(as_text=True)
        for field in ('rule-ingredients', 'rule-extra', 'rule-active'):
            self.assertIn(field, page)
        # What the editor sends: its fields, the new ingredient limit among them
        rules = {'max_total_minutes': 35, 'max_cleanup': 2, 'max_spice': None, 'max_carbs_per_serving': None, 'diet': None,
                 'difficulties': ['Simplistic'], 'max_active_minutes': 15, 'max_ingredients': 8, 'max_extra': 1}
        res = self.client.post('/admin/chefs/save', json={'chefs': [{'id': 'the_minimalist', 'constraints': rules}]})
        self.assertTrue(res.get_json()['success'])
        stored = json.loads(db.session.get(Chef, 'the_minimalist').constraints)
        self.assertEqual((stored['max_ingredients'], stored['forms']), (8, 'shortcut'))  # forms has no field: kept

    def test_the_cuisine_is_changed_from_the_list(self):
        rid = self.ids['carbonara']
        self.assertEqual(self.client.post(f'/admin/recipes/{rid}/cuisine', json={'cuisine': 'Nordic'}).status_code, 302)
        self.login()
        self.assertIn('recipe-cuisine-dropdown', self.client.get('/admin/recipes-management').get_data(as_text=True))
        self.assertEqual(self.client.post(f'/admin/recipes/{rid}/cuisine', json={'cuisine': 'Martian'}).status_code, 400)
        self.assertTrue(self.client.post(f'/admin/recipes/{rid}/cuisine', json={'cuisine': 'Nordic'}).get_json()['success'])
        self.assertEqual(db.session.get(Recipe, rid).cuisine, 'Nordic')

    def test_an_alias_is_added_from_ingredients_management(self):
        self.login()
        self.assertIn('data-alias-food', self.client.get('/admin/ingredients-management/').get_data(as_text=True))
        spaghetti = db.session.execute(db.select(Ingredient).filter_by(name='spaghetti')).scalar_one()
        res = self.client.post('/api/add-synonym', json={'name': 'spaghettini', 'food_id': spaghetti.food_id})
        self.assertTrue(res.get_json()['added'])
        self.assertEqual(db.session.execute(db.select(IngredientAlias.ingredient_id).filter_by(name='spaghettini')).scalar(), spaghetti.id)


if __name__ == '__main__':
    unittest.main()
