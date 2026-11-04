"""The ingredients page (services/ingredient_library.py): what the recipes use first, search, the shortcuts, Staples, and
the sheet with the dishes, with what is not active and drafts kept from visitors."""
import os
import sys
import unittest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

os.environ['DB_BACKEND'] = 'local'
os.environ['DATABASE_URL'] = 'sqlite://'
os.environ['STORAGE_BACKEND'] = 'local'
os.environ.setdefault('SECRET_KEY', 'test-secret')
os.environ.setdefault('GOOGLE_API_KEY', 'test-key')
os.environ.pop('K_SERVICE', None)

from app import app  # noqa: E402
from database.models import Ingredient, Recipe, RecipeComponent, RecipeLine, RecipeStep, User, db  # noqa: E402


class IngredientsPageTests(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        self.ctx = app.app_context()
        self.ctx.push()
        db.drop_all()
        db.create_all()
        self.chicken = self.ingredient('chicken breast', 'meat', calories=165)
        self.salt = self.ingredient('sea salt', 'spices and herbs', staple=True)
        self.amaretto = self.ingredient('amaretto', 'alcoholic beverages')
        self.spare = self.ingredient('saffron threads', 'spices and herbs', staple=True)
        self.pending = self.ingredient('pending thing', 'meat', status='pending')
        self.approved = self.recipe('Roast chicken', 'approved', [self.chicken, self.salt])
        self.other = self.recipe('Chicken soup', 'approved', [self.chicken])
        self.draft = self.recipe('Secret draft', 'draft', [self.chicken, self.amaretto])
        admin = User(email='admin@test', is_admin=True)
        admin.set_password('pw')
        db.session.add(admin)
        db.session.commit()
        self.client = app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def ingredient(self, name, category, staple=False, status='active', calories=None):
        ing = Ingredient(food_id=name.replace(' ', '_'), name=name, main_category=category, is_staple=staple, status=status,
                         calories_per_100g=calories)
        db.session.add(ing)
        db.session.flush()
        return ing

    def recipe(self, title, status, ingredients):
        recipe = Recipe(title=title, status=status, cuisine='Any', difficulty='Simplistic', schema_version=2)
        db.session.add(recipe)
        db.session.flush()
        part = RecipeComponent(recipe_id=recipe.id, local_id='c1', name='Main', sort_order=0)
        db.session.add(part)
        db.session.flush()
        step = RecipeStep(recipe_id=recipe.id, component_id=part.id, local_id='s1', phase='cook', short='Cook', text='Cook', method='boil')
        db.session.add(step)
        db.session.flush()
        for n, ing in enumerate(ingredients):
            db.session.add(RecipeLine(recipe_id=recipe.id, component_id=part.id, step_id=step.id, local_id=f'i{n}', name=ing.name,
                                      ingredient_id=ing.id, sort_order=n))
        db.session.flush()
        return recipe

    def page(self, query=''):
        return self.client.get(f'/ingredients{query}').get_data(as_text=True)

    def test_the_ones_in_dishes_come_first_and_alone(self):
        html = self.page()
        self.assertLess(html.index('chicken breast'), html.index('sea salt'))
        self.assertIn('2 dishes', html)
        self.assertNotIn('saffron threads', html)
        self.assertIn('Show all', html)

    def test_show_all_and_a_search_look_through_everything(self):
        self.assertIn('saffron threads', self.page('?all=1'))
        self.assertIn('saffron threads', self.page('?q=SAFFRON'))
        self.assertNotIn('chicken breast', self.page('?q=saffron'))

    def test_a_draft_recipe_counts_for_nothing(self):
        self.assertNotIn('amaretto', self.page())
        sheet = self.client.get(f'/ingredients/{self.chicken.id}/card').get_data(as_text=True)
        self.assertIn('Roast chicken', sheet)
        self.assertNotIn('Secret draft', sheet)

    def test_shortcuts_and_staples(self):
        protein = self.page('?group=protein')
        self.assertIn('chicken breast', protein)
        self.assertNotIn('sea salt', protein)
        staples = self.page('?staples=1')
        self.assertIn('sea salt', staples)
        self.assertNotIn('chicken breast', staples)
        self.assertIn('saffron threads', self.page('?staples=1&all=1'))
        self.assertNotIn('chicken breast', self.page('?staples=1&group=protein&all=1'))

    def test_an_unknown_group_is_no_group(self):
        self.assertIn('chicken breast', self.page('?group=nonsense'))

    def test_show_more_pages_the_list(self):
        for n in range(60):
            self.recipe(f'Dish {n}', 'approved', [self.ingredient(f'item {n:02}', 'meat')])
        db.session.commit()
        html = self.page()
        self.assertEqual(html.count('data-ing="'), 48)
        self.assertIn('shown=96', html)
        self.assertEqual(self.page('?shown=96').count('data-ing="'), 62)

    def test_a_visitor_sees_neither_the_inside_nor_what_is_not_active(self):
        html = self.page('?all=1')
        self.assertNotIn('pending thing', html)
        self.assertNotIn(f'#{self.chicken.id}<', html)
        self.assertNotIn('Date Added', html)
        self.assertNotIn('Manage', html)
        self.assertEqual(self.client.get(f'/ingredients/{self.pending.id}/card').status_code, 404)

    def test_an_admin_sees_what_is_not_active_and_the_way_to_the_tools(self):
        self.client.post('/login', data={'email': 'admin@test', 'password': 'pw'})
        html = self.page('?all=1')
        self.assertIn('pending thing', html)
        self.assertIn('Manage', html)
        self.assertEqual(self.client.get(f'/ingredients/{self.pending.id}/card').status_code, 200)

    def test_the_admin_page_has_the_tools_the_page_gave_up(self):
        self.client.post('/login', data={'email': 'admin@test', 'password': 'pw'})
        html = self.client.get('/admin/ingredients-management/').get_data(as_text=True)
        self.assertIn('toggleStaple(', html)
        self.assertIn('/new-ingredient?edit_id=', html)
        self.assertIn('deleteIngredient(', html)
        self.assertIn('inspectIngredient(', html)

    def test_the_staple_switch_answers_after_saving(self):
        self.client.post('/login', data={'email': 'admin@test', 'password': 'pw'})
        answer = self.client.post(f'/api/ingredient/{self.amaretto.id}/toggle_basic')
        self.assertEqual(answer.status_code, 200)
        self.assertTrue(answer.get_json()['new_status'])


if __name__ == '__main__':
    unittest.main()
