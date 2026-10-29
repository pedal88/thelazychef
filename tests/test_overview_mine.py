"""Saved and Cook next on the recipe page's first screen (components/overview_layouts.html, save_buttons), and
unsaving that keeps what else the cook stored about the dish (Made, the rating, the comment)."""
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
from database.models import Recipe, User, UserQueue, UserRecipeInteraction, db  # noqa: E402
from services.recipe_v2.store import save_v2  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
with open(os.path.join(ROOT, 'data', 'pilot_v2', 'fasit', 'carbonara.json'), encoding='utf-8') as f:
    CARBONARA = json.load(f)


class OverviewMineTests(unittest.TestCase):
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
        self.url = f'/recipe/{self.recipe.id}'

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def login(self):
        self.client.post('/login', data={'email': 'cook@test', 'password': 'pw'})

    def test_only_for_a_signed_in_cook(self):
        self.assertNotIn('data-mine=', self.client.get(self.url).get_data(as_text=True))
        self.login()
        html = self.client.get(self.url).get_data(as_text=True)
        self.assertIn('data-mine="save" aria-pressed="false"', html)
        self.assertIn('data-mine="queue" aria-pressed="false"', html)

    def test_the_buttons_show_what_is_saved_and_queued(self):
        self.login()
        self.assertEqual(self.client.post(f'/api/recipes/{self.recipe.id}/favorite').get_json()['status'], 'added')
        self.assertEqual(self.client.post(f'/api/queue/add/{self.recipe.id}').get_json()['action'], 'added')
        html = self.client.get(self.url).get_data(as_text=True)
        self.assertIn('data-mine="save" aria-pressed="true"', html)
        self.assertIn('>Saved</span>', html)
        self.assertIn('data-mine="queue" aria-pressed="true"', html)
        self.assertIn('>In Cook next</span>', html)

    def test_unsaving_keeps_made_and_the_rating(self):
        self.login()
        self.client.post(f'/api/recipes/{self.recipe.id}/favorite')
        self.client.post(f'/api/interactions/recipe/{self.recipe.id}/cooked')
        self.client.post(f'/api/interactions/recipe/{self.recipe.id}/feedback', data={'rating': '4', 'comment': 'Less salt'})
        self.assertEqual(self.client.post(f'/api/recipes/{self.recipe.id}/favorite').get_json()['status'], 'removed')
        db.session.expire_all()
        mark = db.session.get(UserRecipeInteraction, (self.user.id, self.recipe.id))
        self.assertEqual((mark.status, mark.is_made, mark.made_count, mark.rating, mark.comment), ('pass', True, 1, 4, 'Less salt'))
        self.assertIn('data-mine="save" aria-pressed="false"', self.client.get(self.url).get_data(as_text=True))
        # Saved again, and only saved: unsaving then removes the row as before
        other = Recipe(title='Lasagne', status='approved', cuisine='Italian', difficulty='Simplistic')
        db.session.add(other)
        db.session.commit()
        self.client.post(f'/api/recipes/{other.id}/favorite')
        self.client.post(f'/api/recipes/{other.id}/favorite')
        self.assertIsNone(db.session.get(UserRecipeInteraction, (self.user.id, other.id)))
        self.assertEqual(db.session.execute(db.select(UserQueue)).first(), None)


if __name__ == '__main__':
    unittest.main()
