"""An admin seeing the site as a signed-in user or a visitor (services/view_as.py, routes/view_as_routes.py)."""
import json
import os
import sys
import unittest
from types import SimpleNamespace

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(ROOT)

os.environ['DB_BACKEND'] = 'local'
os.environ['DATABASE_URL'] = 'sqlite://'
os.environ['STORAGE_BACKEND'] = 'local'
os.environ.setdefault('SECRET_KEY', 'test-secret')
os.environ.setdefault('GOOGLE_API_KEY', 'test-key')
os.environ.pop('K_SERVICE', None)

from flask import g  # noqa: E402
from flask.testing import FlaskClient  # noqa: E402

from app import app  # noqa: E402
from database.models import Recipe, ReferralVisit, User, UserLink, UserRecipeInteraction, db  # noqa: E402
from services import view_as  # noqa: E402
from services.recipe_v2 import generate, view  # noqa: E402

BAR = 'id="view-as-bar"'
HTML = {'Accept': 'text/html'}


class Client(FlaskClient):
    """Every request its own signed-in user: under the app context the tests keep open, requests would share g."""

    def open(self, *args, **kwargs):
        g.pop('_login_user', None)
        g.pop('view_as', None)
        return super().open(*args, **kwargs)


def client():
    return Client(app, app.response_class, use_cookies=True)


def recorded_call():
    with open(os.path.join(ROOT, 'data', 'pilot_v2', 'results_0b', 'opus-low', 'fasit', 'carbonara.json'), encoding='utf-8') as f:
        run = json.load(f)
    answers = [run['source_text'], json.dumps(run['recipe'], ensure_ascii=False)]

    def call(model, effort, messages, system=None, schema=None):
        msg = SimpleNamespace(content=[SimpleNamespace(type='text', text=answers.pop(0))], stop_reason='end_turn', model=model)
        return msg, {'cost_usd': 0.01, 'seconds': 1.0}
    return call


class ViewAsTests(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        self.ctx = app.app_context()
        self.ctx.push()
        db.drop_all()
        db.create_all()
        view.clear_cache()
        for email, is_admin in (('admin@test', True), ('user@test', False)):
            user = User(email=email, is_admin=is_admin)
            user.set_password('pw')
            db.session.add(user)
        db.session.commit()
        self.admin_id = db.session.execute(db.select(User.id).where(User.email == 'admin@test')).scalar()
        self.user_id = db.session.execute(db.select(User.id).where(User.email == 'user@test')).scalar()
        self.client = client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def sign_in(self, email='admin@test'):
        self.client.post('/login', data={'email': email, 'password': 'pw'})

    def view_as(self, role):
        return self.client.post('/view-as', data={'role': role, 'next': '/recipes'})

    def recipe(self, status='approved'):
        recipe, _ = generate.create_recipe('text', 'carbonara', call=recorded_call())
        recipe.status = status
        db.session.commit()
        return recipe

    def test_only_a_real_admin_can_switch(self):
        self.assertEqual(self.view_as('visitor').status_code, 403)  # nobody signed in
        self.sign_in('user@test')
        self.assertEqual(self.view_as('visitor').status_code, 403)
        with self.client.session_transaction() as s:
            self.assertNotIn(view_as.KEY, s)

    def test_a_value_left_in_a_regular_users_session_changes_nothing(self):
        self.sign_in('user@test')
        for value in ('user', 'visitor', 'admin', 'root'):
            with self.subTest(value=value):
                with self.client.session_transaction() as s:
                    s[view_as.KEY] = value
                page = self.client.get('/recipes').get_data(as_text=True)
                self.assertNotIn(BAR, page)
                self.assertIn('Log out', page)  # still signed in as themself
                self.assertEqual(self.client.get('/admin/funnel').status_code, 403)

    def test_a_forged_role_gives_an_admin_nothing_new(self):
        self.sign_in()
        self.assertEqual(self.view_as('root').status_code, 400)
        with self.client.session_transaction() as s:
            s[view_as.KEY] = 'root'
        self.assertNotIn(BAR, self.client.get('/recipes').get_data(as_text=True))

    def test_an_admin_who_is_no_longer_one_loses_the_way_back(self):
        self.sign_in()
        self.view_as('visitor')
        db.session.get(User, self.admin_id).is_admin = False
        db.session.commit()
        self.assertEqual(self.view_as('admin').status_code, 403)
        self.assertNotIn(BAR, self.client.get('/recipes').get_data(as_text=True))

    def test_admin_pages_are_closed_in_the_lower_roles_and_open_again_after(self):
        self.sign_in()
        self.assertEqual(self.client.get('/admin/funnel').status_code, 200)
        for role in view_as.ROLES:
            with self.subTest(role=role):
                self.view_as(role)
                closed = self.client.get('/admin/funnel', follow_redirects=True)  # a visitor goes to log in first
                self.assertEqual(closed.status_code, 403 if role == 'user' else 200)
                self.assertIn(BAR, closed.get_data(as_text=True))  # a plain error page has the bar too
                self.assertIn('name="viewport"', closed.get_data(as_text=True))
                self.assertNotIn('Funnel</h1>', closed.get_data(as_text=True))
                self.assertEqual(self.view_as('admin').status_code, 302)
                self.assertEqual(self.client.get('/admin/funnel').status_code, 200)
        self.assertNotIn(BAR, self.client.get('/admin/funnel').get_data(as_text=True))

    def test_the_visitor_role_is_anonymous_even_with_the_remember_cookie(self):
        self.sign_in()
        self.view_as('visitor')
        page = self.client.get('/recipes').get_data(as_text=True)
        self.assertIn(BAR, page)
        self.assertIn('Viewing as visitor', page)
        self.assertNotIn('Log out', page)
        self.assertNotIn('class="trialbar"', page)
        needs_login = self.client.get('/recipes/saved', headers=HTML)
        if needs_login.status_code == 302:
            self.assertIn('/login', needs_login.headers['Location'])
        self.assertIn(BAR, self.client.get('/login').get_data(as_text=True))

    def test_the_user_role_keeps_the_account_without_admin(self):
        self.sign_in()
        self.view_as('user')
        page = self.client.get('/recipes').get_data(as_text=True)
        self.assertIn('Viewing as signed-in user', page)
        self.assertIn('Log out', page)
        self.assertNotIn('class="trialbar"', page)
        with app.test_request_context():
            wrapped = view_as.SignedInView(db.session.get(User, self.admin_id))
            self.assertFalse(wrapped.is_admin)
            self.assertEqual(wrapped.email, 'admin@test')
            self.assertTrue(wrapped.is_authenticated)
            self.assertEqual(wrapped.get_id(), str(self.admin_id))
        self.assertIs(db.session.get(User, self.admin_id).is_admin, True)

    def test_drafts_are_hidden_and_a_cached_recipe_shows_each_role_its_own(self):
        draft, approved = self.recipe('draft'), self.recipe('approved')
        self.sign_in()
        self.assertEqual(self.client.get(f'/recipe/{draft.id}').status_code, 200)
        as_admin = self.client.get(f'/recipe/{approved.id}').get_data(as_text=True)
        self.assertIn('class="trialbar"', as_admin)
        self.assertIn('name="role" value="visitor"', as_admin)
        for role in view_as.ROLES:
            with self.subTest(role=role):
                self.view_as(role)
                self.assertNotIn('Spaghetti', self.client.get(f'/recipe/{draft.id}', follow_redirects=True).get_data(as_text=True))
                page = self.client.get(f'/recipe/{approved.id}').get_data(as_text=True)  # from view.page's cache
                self.assertIn(BAR, page)
                self.assertNotIn('class="trialbar"', page)
                self.assertIn(BAR, self.client.get(f'/recipe/{approved.id}/print').get_data(as_text=True))
                self.view_as('admin')

    def test_nothing_is_saved_and_the_answer_can_be_understood(self):
        recipe = self.recipe()
        self.sign_in()
        self.view_as('user')
        fetched = self.client.post(f'/api/interactions/recipe/{recipe.id}/favorite', headers={'Accept': '*/*'})
        self.assertEqual(fetched.status_code, 403)
        self.assertEqual(fetched.get_json()['error'], 'Not saved, because this is only a preview. For a real signed-in user this works as normal.')
        self.assertEqual(fetched.headers[view_as.HEADER], 'user')
        self.assertEqual(db.session.execute(db.select(db.func.count()).select_from(UserRecipeInteraction)).scalar(), 0)
        unit = self.client.post('/api/me/units', json={'units': 'us'})
        self.assertEqual(unit.status_code, 403)
        self.assertIsNone(db.session.get(User, self.admin_id).unit_system)
        form = self.client.post(f'/api/interactions/recipe/{recipe.id}/favorite', headers={**HTML, 'Referer': 'http://localhost/recipes?time=30'})
        self.assertEqual(form.status_code, 302)
        self.assertEqual(form.headers['Location'], '/recipes?time=30')
        self.assertIn('only a preview', self.client.get('/recipes').get_data(as_text=True))

    def test_no_account_is_made_or_signed_into_in_the_visitor_role(self):
        self.sign_in()
        self.view_as('visitor')
        self.client.post('/register', data={'email': 'new@test', 'password': 'pw'}, headers=HTML)
        refused = self.client.post('/register', data={'email': 'new@test', 'password': 'pw'})
        self.assertEqual(refused.get_json()['error'], 'Not saved, because this is only a preview.')  # no signed-in user here
        self.assertIsNone(db.session.execute(db.select(User).where(User.email == 'new@test')).scalar())
        self.client.post('/login', data={'email': 'user@test', 'password': 'pw'}, headers=HTML)
        self.assertIn('Viewing as visitor', self.client.get('/recipes').get_data(as_text=True))
        self.assertEqual(self.client.get('/login/google', headers=HTML).status_code, 302)
        self.assertEqual(self.client.get('/login/google', headers=HTML).headers['Location'], '/')

    def test_what_saves_on_a_get_saves_nothing_in_the_user_role(self):
        recipe = self.recipe()
        self.sign_in()
        self.view_as('user')
        self.client.get('/mirror', headers=HTML)
        self.assertEqual(db.session.execute(db.select(db.func.count()).select_from(UserLink)).scalar(), 0)
        self.client.get(f'/login?do=save&recipe={recipe.id}', headers=HTML)
        self.assertEqual(db.session.execute(db.select(db.func.count()).select_from(UserRecipeInteraction)).scalar(), 0)

    def test_the_safety_net_stops_a_save_nobody_knew_about(self):
        with app.test_request_context():
            g.view_as = 'user'
            db.session.get(User, self.user_id).email = 'changed@test'
            with self.assertRaises(view_as.ViewOnly):
                db.session.commit()
            db.session.rollback()
            g.view_as = None
        self.assertEqual(db.session.get(User, self.user_id).email, 'user@test')

    def test_leaving_works_and_forgets_the_role(self):
        self.sign_in()
        self.view_as('user')
        self.client.post('/logout', headers=HTML)
        with self.client.session_transaction() as s:
            self.assertNotIn(view_as.KEY, s)
        self.sign_in()
        self.assertNotIn(BAR, self.client.get('/recipes').get_data(as_text=True))

    def test_visits_are_not_counted_for_an_admin_looking_like_a_visitor(self):
        self.sign_in()
        self.view_as('visitor')
        for address in ('/recipes?ref=ig-1', '/tiktok/3', '/ig'):
            self.client.get(address)
        with self.client.session_transaction() as s:
            self.assertFalse(any(k.startswith('ref') for k in s))
        self.assertNotIn('/ref/seen', self.client.get('/recipes?ref=ig-1').get_data(as_text=True))
        self.client.post('/ref/seen', headers=HTML)
        self.assertEqual(db.session.execute(db.select(db.func.count()).select_from(ReferralVisit)).scalar(), 0)

    def test_a_real_visitor_is_still_counted(self):
        visitor = client()
        visitor.get('/recipes?ref=ig-1', headers={'User-Agent': 'Mozilla/5.0'})
        visitor.post('/ref/seen', headers={'User-Agent': 'Mozilla/5.0'})
        self.assertEqual(db.session.execute(db.select(db.func.count()).select_from(ReferralVisit)).scalar(), 1)

    def test_the_bar_is_on_pages_of_every_layout(self):
        self.sign_in()
        self.view_as('visitor')
        for address in ('/', '/recipes', '/login', '/privacy', '/this/does/not/exist'):
            with self.subTest(address=address):
                self.assertIn(BAR, self.client.get(address).get_data(as_text=True))

    def test_switching_on_an_admin_page_goes_home_rather_than_to_a_refusal(self):
        self.sign_in()
        res = self.client.post('/view-as', data={'role': 'visitor', 'next': '/admin/funnel'})
        self.assertEqual(res.headers['Location'], '/')
        res = self.client.post('/view-as', data={'role': 'admin', 'next': '/admin/funnel'})
        self.assertEqual(res.headers['Location'], '/admin/funnel')
        res = self.client.post('/view-as', data={'role': 'admin', 'next': 'https://elsewhere.example/'})
        self.assertEqual(res.headers['Location'], '/')


if __name__ == '__main__':
    unittest.main()
