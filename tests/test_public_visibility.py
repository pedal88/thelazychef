"""Anonymous visitors see only published content; admins see everything.

Drafts and pending or inactive ingredients must not leak through the public pages and JSON endpoints.
"""
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

import json  # noqa: E402

from app import app  # noqa: E402
from database.models import Ingredient, Recipe, User, db  # noqa: E402
from services.recipe_v2.store import save_v2  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
with open(os.path.join(ROOT, 'data', 'pilot_v2', 'fasit', 'carbonara.json'), encoding='utf-8') as f:
    CARBONARA = json.load(f)


class PublicVisibilityTests(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        self.ctx = app.app_context()
        self.ctx.push()
        db.drop_all()
        db.create_all()

        admin = User(email='admin@test', is_admin=True)
        admin.set_password('pw')
        db.session.add(admin)

        def recipe(title, status):
            r = Recipe(title=title, status=status, cuisine='Italian', difficulty='Easy',
                       protein_type='Vegetarian', chef_id='gourmet')
            db.session.add(r)
            save_v2(r, CARBONARA)
            return r

        self.approved = recipe('Approved', 'approved')
        self.draft = recipe('Draft', 'draft')
        self.linked_draft = recipe('Linked draft', 'draft')
        db.session.flush()

        def ingredient(name, status, **kw):
            i = Ingredient(food_id=f'id-{name}', name=name, status=status, default_unit='g',
                           main_category='vegetables', **kw)
            db.session.add(i)
            return i

        self.active = ingredient('onion active', 'active', sub_recipe_id=self.linked_draft.id)
        self.pending = ingredient('onion pending', 'pending')
        self.inactive = ingredient('onion inactive', 'inactive')

        db.session.commit()
        self.client = app.test_client()

    def tearDown(self):
        # Other test modules share the in-memory database; leave it empty.
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def _login_admin(self):
        self.client.post('/login', data={'email': 'admin@test', 'password': 'pw'})

    def _shows_recipe(self, url):
        return self.client.get(url).status_code == 200

    def test_discover_shows_approved_recipes_with_a_picture_only(self):
        pictured = Recipe(title='Pictured', status='approved', cuisine='Italian', difficulty='Easy',
                          image_filename='dish_x.webp')
        drafted = Recipe(title='Pictured draft', status='draft', cuisine='Italian', difficulty='Easy',
                         image_filename='dish_y.webp')
        db.session.add_all([pictured, drafted])
        db.session.commit()
        shown = [r['id'] for r in self.client.get('/api/feed/recipes').get_json()['recipes']]
        self.assertEqual(shown, [pictured.id])  # not self.approved, which has no picture yet
        self._login_admin()
        shown = [r['id'] for r in self.client.get('/api/feed/recipes').get_json()['recipes']]
        self.assertEqual(shown, [pictured.id])

    def test_recipe_pages_hide_drafts_from_anonymous(self):
        self.assertTrue(self._shows_recipe(f'/recipe/{self.approved.id}'))
        self.assertFalse(self._shows_recipe(f'/recipe/{self.draft.id}'))

    def test_admin_sees_draft_recipes(self):
        self._login_admin()
        self.assertTrue(self._shows_recipe(f'/recipe/{self.draft.id}'))

    def test_missing_recipe_redirects_instead_of_crashing(self):
        self.assertEqual(self.client.get('/recipe/9999').status_code, 302)

    def test_a_retired_v1_recipe_is_gone_even_for_admins(self):
        old = Recipe(title='Old', status='archived', cuisine='', difficulty='', schema_version=1)
        db.session.add(old)
        db.session.commit()
        self._login_admin()
        self.assertEqual(self.client.get(f'/recipe/{old.id}').status_code, 404)
        self.assertEqual(self.client.get(f'/api/sub-recipe/{old.id}').status_code, 404)

    def test_sub_recipe_api_allows_approved_and_linked_drafts_only(self):
        self.assertEqual(self.client.get(f'/api/sub-recipe/{self.approved.id}').status_code, 200)
        self.assertEqual(self.client.get(f'/api/sub-recipe/{self.linked_draft.id}').status_code, 200)
        self.assertEqual(self.client.get(f'/api/sub-recipe/{self.draft.id}').status_code, 404)

    def test_ingredient_endpoints_show_only_active_to_anonymous(self):
        page = self.client.get('/ingredients').get_data(as_text=True)
        self.assertIn('onion active', page)
        self.assertNotIn('onion pending', page)
        self.assertNotIn('onion inactive', page)

        self.assertEqual(self.client.get(f'/api/ingredient/{self.active.id}').status_code, 200)
        self.assertEqual(self.client.get(f'/api/ingredient/{self.pending.id}').status_code, 404)

        names = [r['name'] for r in self.client.post('/api/search-ingredients', json={'query': 'onion'}).get_json()['results']]
        self.assertEqual(names, ['onion active'])

        nodes = self.client.get('/api/graph/ingredient-galaxy').get_json()['nodes']
        labels = {n.get('name') or n.get('label') or n.get('id') for n in nodes}
        self.assertFalse(any('pending' in str(label) or 'inactive' in str(label) for label in labels))

    def test_admin_sees_all_ingredients(self):
        self._login_admin()
        page = self.client.get('/ingredients').get_data(as_text=True)
        self.assertIn('onion pending', page)
        self.assertEqual(self.client.get(f'/api/ingredient/{self.pending.id}').status_code, 200)


if __name__ == '__main__':
    unittest.main()
