"""Continue with Google (services/google_signin.py, routes/auth_routes.py): the trip to Google and back, the checks on
the way back, which user a Google account is, and the button that is hidden where Google refuses to sign in. Google is
never called: the token exchange and the token check stand in."""
import json
import os
import sys
import unittest
from unittest import mock
from urllib.parse import parse_qs, urlparse

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

os.environ['DB_BACKEND'] = 'local'
os.environ['DATABASE_URL'] = 'sqlite://'
os.environ['STORAGE_BACKEND'] = 'local'
os.environ.setdefault('SECRET_KEY', 'test-secret')
os.environ.setdefault('GOOGLE_API_KEY', 'test-key')
os.environ.pop('K_SERVICE', None)

from app import app  # noqa: E402
from database.models import Recipe, User, UserRecipeInteraction, db  # noqa: E402
from services import google_signin  # noqa: E402
from services.recipe_v2.store import save_v2  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
with open(os.path.join(ROOT, 'data', 'pilot_v2', 'fasit', 'carbonara.json'), encoding='utf-8') as f:
    CARBONARA = json.load(f)

KEYS = {'GOOGLE_OAUTH_CLIENT_ID': 'client.apps.googleusercontent.com', 'GOOGLE_OAUTH_CLIENT_SECRET': 'shh'}
IPHONE = 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148'
INSTAGRAM = IPHONE + ' Instagram 350.0.0.0 (iPhone15,2; iOS 18_0; nb_NO; nb; scale=3.00; 1179x2556)'


class GoogleSigninTests(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        self.ctx = app.app_context()
        self.ctx.push()
        db.drop_all()
        db.create_all()
        self.recipe = Recipe(title='Carbonara', status='approved', cuisine='Italian', difficulty='Simplistic')
        db.session.add(self.recipe)
        save_v2(self.recipe, CARBONARA)
        db.session.commit()
        self.client = app.test_client()
        self.env = mock.patch.dict(os.environ, KEYS)
        self.env.start()

    def tearDown(self):
        self.env.stop()
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def go_to_google(self, query=''):
        response = self.client.get('/login/google' + query)
        self.assertTrue(response.location.startswith(google_signin.AUTH_URL))
        return parse_qs(urlparse(response.location).query)

    def come_back(self, sent, claims, code='the-code'):
        """Google sends the browser back with a code; the exchange and the check of the token stand in for Google's."""
        token = mock.Mock(ok=True, **{'json.return_value': {'id_token': 'a-token'}})
        with mock.patch('services.google_signin.requests.post', return_value=token) as post, \
                mock.patch('services.google_signin.id_token.verify_oauth2_token', return_value=claims) as check:
            response = self.client.get('/login/google/done', query_string={'code': code, 'state': sent['state'][0]})
        return response, post, check

    def user(self, email):
        return db.session.execute(db.select(User).filter_by(email=email)).scalar()

    def test_a_new_google_account_signs_up_and_does_what_was_pressed(self):
        sent = self.go_to_google(f'?next=/recipe/{self.recipe.id}&do=made&recipe={self.recipe.id}')
        self.assertEqual(sent['scope'], ['openid email'])
        self.assertEqual(sent['redirect_uri'], ['http://localhost/login/google/done'])
        response, post, check = self.come_back(sent, {'sub': '111', 'email': 'Cook@Gmail.com', 'email_verified': True})
        self.assertEqual(response.location, f'/recipe/{self.recipe.id}')
        self.assertEqual(post.call_args.kwargs['data']['code'], 'the-code')
        self.assertEqual(check.call_args.args[2], KEYS['GOOGLE_OAUTH_CLIENT_ID'])  # a token for this app only
        user = self.user('cook@gmail.com')
        self.assertEqual(user.google_sub, '111')
        self.assertTrue(db.session.get(UserRecipeInteraction, (user.id, self.recipe.id)).is_made)
        self.assertIn('remember_token=', ''.join(response.headers.getlist('Set-Cookie')))

    def test_an_account_with_the_same_email_is_the_same_person(self):
        old = User(email='cook@gmail.com')
        old.set_password('pw')
        db.session.add(old)
        db.session.commit()
        response, _, _ = self.come_back(self.go_to_google(), {'sub': '111', 'email': 'cook@gmail.com',
                                                               'email_verified': True})
        self.assertEqual(response.location, '/recipes')
        self.assertEqual(len(db.session.execute(db.select(User)).scalars().all()), 1)
        self.assertEqual(self.user('cook@gmail.com').google_sub, '111')
        self.assertTrue(self.user('cook@gmail.com').check_password('pw'))  # the password still works

    def test_the_google_account_wins_when_the_address_has_changed(self):
        self.come_back(self.go_to_google(), {'sub': '111', 'email': 'old@gmail.com', 'email_verified': True})
        self.client.get('/logout')
        self.come_back(self.go_to_google(), {'sub': '111', 'email': 'new@gmail.com', 'email_verified': True})
        self.assertEqual(len(db.session.execute(db.select(User)).scalars().all()), 1)

    def test_nothing_signs_in_without_the_right_state_a_good_token_or_a_verified_email(self):
        sent = self.go_to_google()
        self.come_back(sent, {'sub': '111', 'email': 'cook@gmail.com', 'email_verified': False})
        self.assertIsNone(self.user('cook@gmail.com'))
        self.come_back({'state': ['someone-elses']}, {'sub': '111', 'email': 'cook@gmail.com', 'email_verified': True})
        self.assertIsNone(self.user('cook@gmail.com'))
        sent = self.go_to_google()
        with mock.patch('services.google_signin.requests.post', return_value=mock.Mock(ok=False)):
            response = self.client.get('/login/google/done', query_string={'code': 'x', 'state': sent['state'][0]})
        self.assertTrue(response.location.startswith('/login'))
        self.assertIsNone(self.user('cook@gmail.com'))

    def test_saying_no_at_google_goes_back_to_log_in_with_what_was_pressed(self):
        sent = self.go_to_google(f'?do=save&recipe={self.recipe.id}')
        response = self.client.get('/login/google/done', query_string={'error': 'access_denied',
                                                                       'state': sent['state'][0]})
        self.assertEqual(response.location, f'/login?do=save&recipe={self.recipe.id}')

    def test_the_button_is_there_only_when_set_up_and_not_in_an_apps_browser(self):
        page = self.client.get('/register', headers={'User-Agent': IPHONE}).get_data(as_text=True)
        self.assertIn('Continue with Google</a>', page)
        page = self.client.get('/login', headers={'User-Agent': INSTAGRAM}).get_data(as_text=True)
        self.assertNotIn('Continue with Google</a>', page)
        self.assertIn('works in Safari or Chrome', page)
        with mock.patch.dict(os.environ, {'GOOGLE_OAUTH_CLIENT_ID': ''}):
            self.assertNotIn('Continue with Google', self.client.get('/login').get_data(as_text=True))
            self.assertEqual(self.client.get('/login/google').status_code, 404)


if __name__ == '__main__':
    unittest.main()
