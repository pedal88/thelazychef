"""The celebration after the last step (templates/recipe_v2_make.html, static/js/done.js): "I made this" marks the
recipe as made and counts the times (/api/interactions/recipe/<id>/cooked), once per meal."""
import datetime
import json
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
from database.models import Recipe, User, UserRecipeInteraction, db  # noqa: E402
from services.recipe_v2.store import save_v2  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
with open(os.path.join(ROOT, 'data', 'pilot_v2', 'fasit', 'carbonara.json'), encoding='utf-8') as f:
    CARBONARA = json.load(f)


class CookedTests(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        self.ctx = app.app_context()
        self.ctx.push()
        db.drop_all()
        db.create_all()
        self.user = User(email='cook@test')
        self.user.set_password('pw')
        self.recipe = Recipe(title='Carbonara', status='approved', cuisine='Italian', difficulty='Simplistic')
        db.session.add_all([self.user, self.recipe])
        save_v2(self.recipe, CARBONARA)
        db.session.commit()
        self.client = app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def login(self):
        self.client.post('/login', data={'email': 'cook@test', 'password': 'pw'})

    def cooked(self):
        return self.client.post(f'/api/interactions/recipe/{self.recipe.id}/cooked').get_json()

    def interaction(self):
        db.session.expire_all()
        return db.session.get(UserRecipeInteraction, (self.user.id, self.recipe.id))

    def test_needs_a_login(self):
        resp = self.client.post(f'/api/interactions/recipe/{self.recipe.id}/cooked')
        self.assertIn(resp.status_code, (302, 401))
        self.assertIsNone(self.interaction())

    def test_made_and_counted_once_per_meal(self):
        self.login()
        self.assertEqual(self.cooked()['made_count'], 1)
        i = self.interaction()
        self.assertTrue(i.is_made)
        self.assertIsNotNone(i.last_made_at)
        # Saved again in the same meal (steps unticked and done again): still once
        self.assertEqual(self.cooked()['made_count'], 1)
        # Another day: twice
        i.last_made_at -= datetime.timedelta(days=2)
        db.session.commit()
        self.assertEqual(self.cooked()['made_count'], 2)

    def test_marked_in_the_list_before_counts_once(self):
        self.login()
        self.client.patch(f'/api/interactions/recipe/{self.recipe.id}/made')
        self.assertEqual(self.interaction().made_count, 1)
        data = self.client.get(f'/api/interactions/recipe/{self.recipe.id}').get_json()
        self.assertEqual(data['made_count'], 1)
        self.assertIsNotNone(data['last_made_at'])

    def test_an_unknown_recipe(self):
        self.login()
        self.assertEqual(self.client.post('/api/interactions/recipe/9999/cooked').status_code, 404)

    def test_the_page_has_the_celebration(self):
        html = self.client.get(f'/recipe/{self.recipe.id}').get_data(as_text=True)
        self.assertIn('id="sheet-done"', html)
        self.assertIn('Log in</a> to keep it in your Made list', html)  # signed out: no form to save
        self.assertNotIn('data-done-made', html)
        self.login()
        html = self.client.get(f'/recipe/{self.recipe.id}').get_data(as_text=True)
        self.assertIn('data-done-made', html)
        self.assertIn('name="rating"', html)


if __name__ == '__main__':
    unittest.main()
