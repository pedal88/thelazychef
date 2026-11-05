"""Amounts the source did not give: the mark on the line, what the reader sees, and approval that waits."""
import json
import os
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(ROOT)

os.environ['DB_BACKEND'] = 'local'
os.environ['DATABASE_URL'] = 'sqlite://'
os.environ['STORAGE_BACKEND'] = 'local'
os.environ.setdefault('SECRET_KEY', 'test-secret')
os.environ.setdefault('GOOGLE_API_KEY', 'test-key')

from app import app  # noqa: E402
from flask import g  # noqa: E402

from database.models import Recipe, User, db  # noqa: E402
from services.recipe_v2 import claude, estimated  # noqa: E402
from services.recipe_v2.store import save_v2, to_v2  # noqa: E402

with open(os.path.join(ROOT, 'data', 'pilot_v2', 'fasit', 'carbonara.json'), encoding='utf-8') as f:
    CARBONARA = json.load(f)


class EstimatedTests(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        self.ctx = app.app_context()
        self.ctx.push()
        db.drop_all()
        db.create_all()
        self.recipe = Recipe(title='Carbonara', cuisine='Italian', difficulty='Simplistic', status='draft')
        db.session.add(self.recipe)
        save_v2(self.recipe, CARBONARA)
        admin = User(email='admin@example.com', is_admin=True)
        admin.set_password('test-password')
        db.session.add(admin)
        db.session.commit()
        self.client = app.test_client()
        self.client.post('/login', data={'email': admin.email, 'password': 'test-password'})

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def _mark(self, *names):
        for line in self.recipe.lines:
            line.estimated = True if not names or line.name in names else None
        db.session.commit()

    def _status(self):
        return self.client.post(f'/admin/recipes/{self.recipe.id}/status', json={'status': 'approved'})

    def _page(self):
        return self.client.get(f'/recipe/{self.recipe.id}').get_data(as_text=True)

    def test_the_mark_is_saved_and_read_back_and_the_model_may_set_it(self):
        data = json.loads(json.dumps(CARBONARA))
        data['ingredients'][0]['estimated'] = True
        save_v2(self.recipe, data)
        db.session.commit()
        back = to_v2(self.recipe)['ingredients']
        self.assertTrue(back[0]['estimated'])
        self.assertNotIn('estimated', back[1])
        self.assertIn('estimated', json.dumps(claude.recipe_json_schema()))
        with open(os.path.join(ROOT, 'data', 'prompts', 'recipe_v2', 'structure.jinja2'), encoding='utf-8') as f:
            self.assertIn('set estimated to true on that line', f.read())

    def test_a_recipe_without_marks_is_not_held(self):
        self.assertEqual(estimated.share(self.recipe.lines), 0)
        self.assertFalse(estimated.holds(self.recipe))
        self.assertEqual(self._status().status_code, 200)
        self.assertNotIn('<b class="amt">about ', self._page())

    def test_much_estimated_waits_until_it_is_accepted(self):
        self._mark()
        self.assertEqual(estimated.share(self.recipe.lines), 1)
        held = self._status()
        self.assertEqual(held.status_code, 409)
        self.assertIn('100 %', held.get_json()['error'])
        self.assertEqual(db.session.get(Recipe, self.recipe.id).status, 'draft')
        page = self._page()
        self.assertIn('I have tried it, or accept it', page)
        self.assertIn('The amounts are estimated', page)
        self.assertIn('<b class="amt">about ', page)

        self.assertEqual(self.client.post(f'/new-recipe/v2/accept-estimates/{self.recipe.id}').status_code, 302)
        self.assertFalse(estimated.holds(db.session.get(Recipe, self.recipe.id)))
        self.assertEqual(sum(e['rule'] == 'estimates_accepted' for e in self.recipe.validation_errors), 1)
        self.assertFalse(self.recipe.is_flagged_for_review)
        self.assertEqual(self._status().status_code, 200)
        self.assertEqual(db.session.get(Recipe, self.recipe.id).status, 'approved')
        self.assertIn('The amounts are estimated', self._page())  # the reader is still told

    def test_a_small_estimate_is_marked_but_not_held(self):
        lightest = min((line for line in self.recipe.lines if line.gram_weight), key=lambda line: line.gram_weight)
        self._mark(lightest.name)
        self.assertLess(estimated.share(self.recipe.lines), estimated.HOLD_SHARE)
        self.assertFalse(estimated.holds(self.recipe))
        page = self._page()
        self.assertNotIn('The amounts are estimated', page)
        self.assertIn('<b class="amt">about ', page)
        self.assertEqual(self._status().status_code, 200)

    def test_accepting_needs_an_admin(self):
        g.pop('_login_user', None)  # this test's app context, with who is signed in, is shared by the clients
        self.assertEqual(app.test_client().post(f'/new-recipe/v2/accept-estimates/{self.recipe.id}').status_code, 302)
        self.assertFalse(estimated.accepted(db.session.get(Recipe, self.recipe.id)))
