"""Pages stay fast: a v2 recipe is loaded in a handful of queries, Overview, Prep and Cook share one built
recipe (services/recipe_v2/view.page), and the recipe list does not query once per card."""
import os
import sys
import unittest
from contextlib import contextmanager

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(ROOT)

from tests import test_recipe_v2_view as view_tests  # noqa: E402  (sets the test environment)
from sqlalchemy import event  # noqa: E402
from database.models import Ingredient, Recipe, RecipeDiet, RecipeIngredient, db  # noqa: E402


class PageSpeedTests(unittest.TestCase):
    setUp, tearDown, page = (view_tests.RecipeV2ViewTests.setUp, view_tests.RecipeV2ViewTests.tearDown,
                             view_tests.RecipeV2ViewTests.page)

    @contextmanager
    def queries(self):
        seen = []

        def count(*a, **k):
            seen.append(1)
        event.listen(db.engine, 'before_cursor_execute', count)
        try:
            yield seen
        finally:
            event.remove(db.engine, 'before_cursor_execute', count)

    def test_a_recipe_takes_a_handful_of_queries_and_the_other_tabs_reuse_it(self):
        with self.queries() as first:
            self.assertEqual(self.page('tikka')[0], 200)
        self.assertLessEqual(len(first), 15)  # it was one per step and per line: 50+
        for part in ('/prep', '/cook', ''):
            with self.queries() as again:
                self.assertEqual(self.page('tikka', part)[0], 200)
            self.assertLessEqual(len(again), 4, part)

    def test_a_change_to_the_recipe_shows_at_once(self):
        self.page('carbonara')
        recipe = db.session.get(Recipe, self.ids['carbonara'])
        recipe.chef_note = 'Use the pasta water.'
        db.session.commit()
        self.assertIn('Use the pasta water.', self.page('carbonara')[1])
        self.assertIn('6 servings', self.page('carbonara', servings=6)[1])  # servings are part of the key

    def test_the_recipe_list_does_not_query_per_card(self):
        def list_queries():
            with self.queries() as seen:
                self.assertEqual(self.client.get('/recipes').status_code, 200)
            return len(seen)
        few = list_queries()
        for n in range(6):
            r = Recipe(title=f'Dish {n}', cuisine='', difficulty='', status='approved')
            r.diets.append(RecipeDiet(diet='vegetarian'))
            db.session.add(r)
        db.session.commit()
        self.assertEqual(list_queries(), few)

    def test_an_old_recipe_does_not_query_per_ingredient(self):
        def v1_with(n):
            r = Recipe(title=f'Old dish {n}', cuisine='', difficulty='', status='approved', schema_version=1)
            db.session.add(r)
            for k in range(n):
                ing = Ingredient(food_id=f'T{n}-{k}', name=f'thing {n} {k}', status='active', default_unit='g',
                                 main_category='vegetables', sub_category=f'sub {k % 3}')
                db.session.add(ing)
                db.session.flush()
                db.session.add(RecipeIngredient(recipe_id=r.id, ingredient_id=ing.id, amount=1, unit='g'))
            db.session.commit()
            with self.queries() as seen:
                self.assertEqual(self.client.get(f'/recipe/{r.id}').status_code, 200)
            return len(seen)
        self.assertEqual(v1_with(3), v1_with(12))


if __name__ == '__main__':
    unittest.main()
