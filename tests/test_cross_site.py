"""CSRF (utils/cross_site.py): nothing is written from another site's page, on any route, and what must keep working
does: this site's forms and fetch calls, Cloud Tasks, the API, Google's way back and the browsers inside TikTok and
Instagram."""
import os
import sys
import unittest
from unittest import mock

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

os.environ['DB_BACKEND'] = 'local'
os.environ['DATABASE_URL'] = 'sqlite://'
os.environ['STORAGE_BACKEND'] = 'local'
os.environ.setdefault('SECRET_KEY', 'test-secret')
os.environ.setdefault('GOOGLE_API_KEY', 'test-key')
os.environ.pop('K_SERVICE', None)

from app import app  # noqa: E402
from database.models import User, db  # noqa: E402
from tests.test_smoke import WRITE_METHODS, _build_url, _rules  # noqa: E402
REFUSED = 'This request came from another site, so it was not carried out. Go back to the page and try again.'

HOST = 'thelazychef.app'
BASE = f'https://{HOST}'
SAME = {'Sec-Fetch-Site': 'same-origin', 'Origin': BASE}
ELSEWHERE = {'Sec-Fetch-Site': 'cross-site', 'Origin': 'https://evil.example'}
TIKTOK_APP = 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 musical_ly_37 BytedanceWebview'
INSTAGRAM_APP = 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 Instagram 350.0.0'


class CrossSiteTests(unittest.TestCase):
    def setUp(self):
        # No app context kept open around the requests: Flask-Login would keep the signed-in user in it between them
        app.config['TESTING'] = True
        with app.app_context():
            db.create_all()
            admin = User(email='admin@test', is_admin=True)
            admin.set_password('pw')
            db.session.add(admin)
            db.session.commit()
            self.admin_id = admin.id
        self.client = app.test_client()

    def tearDown(self):
        with app.app_context():
            db.session.remove()
            db.drop_all()

    def _sign_in(self):
        with self.client.session_transaction(base_url=BASE) as s:
            s['_user_id'], s['_fresh'] = str(self.admin_id), True

    def _signed_in(self, client=None):
        with (client or self.client).session_transaction(base_url=BASE) as s:
            return '_user_id' in s

    def _user(self, email):
        with app.app_context():
            return db.session.execute(db.select(User.id).filter_by(email=email)).scalar()

    def _post(self, url, headers, **kwargs):
        return self.client.post(url, base_url=BASE, headers=headers, **kwargs)

    def _refused(self, response):
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.get_data(as_text=True), REFUSED)

    def test_every_write_route_refuses_another_site_for_a_signed_in_admin(self):
        self._sign_in()
        checked = 0
        for rule in _rules():
            url = _build_url(rule)
            for method in sorted(rule.methods & WRITE_METHODS):
                with self.subTest(method=method, url=url):
                    checked += 1
                    self._refused(self.client.open(url, method=method, base_url=BASE, headers=ELSEWHERE))
        self.assertGreater(checked, 70)  # guards against the loop silently checking nothing

    def test_what_a_browser_says_about_another_site_is_refused(self):
        self._sign_in()
        for headers in ({'Sec-Fetch-Site': 'cross-site'},
                        {'Sec-Fetch-Site': 'same-site'},  # another address under this domain is not this site
                        {'Origin': 'https://evil.example'},
                        {'Origin': f'https://{HOST}.evil.example'},
                        {'Origin': 'null'},  # a sandboxed frame
                        {'Sec-Fetch-Site': 'cross-site', 'Origin': BASE}):  # Sec-Fetch-Site decides
            with self.subTest(headers=headers):
                self._refused(self._post('/admin/funnel/fetch', headers))

    def test_nothing_is_done_when_refused(self):
        self._refused(self._post('/register', ELSEWHERE, data={'email': 'new@test', 'password': 'pw'}))
        self.assertIsNone(self._user('new@test'))

    def test_logging_in_to_someone_elses_account_from_another_site_is_refused(self):
        self._refused(self._post('/login', ELSEWHERE, data={'email': 'admin@test', 'password': 'pw'}))
        self.assertFalse(self._signed_in())

    def test_reading_from_another_site_still_works(self):
        for url in ('/login', '/privacy'):
            self.assertEqual(self.client.get(url, base_url=BASE, headers=ELSEWHERE).status_code, 200)

    def test_this_sites_login_and_register_work(self):
        for headers in (SAME, {'Origin': BASE}, {}):
            with self.subTest(headers=headers):
                client = app.test_client()
                response = client.post('/login', base_url=BASE, headers=headers, data={'email': 'admin@test', 'password': 'pw'})
                self.assertEqual(response.status_code, 302)
                self.assertTrue(self._signed_in(client))
        response = self._post('/register', SAME, data={'email': 'new@test', 'password': 'pw'})
        self.assertEqual(response.status_code, 302)
        self.assertIsNotNone(self._user('new@test'))

    def test_a_fetch_from_this_site_works(self):
        self._sign_in()
        response = self._post('/api/me/units', SAME, json={'units': 'us'})
        self.assertEqual(response.status_code, 200)

    def test_an_address_with_a_port_is_its_own_site(self):
        response = self.client.post('/login', base_url='http://localhost:8000', headers={'Origin': 'http://localhost:8000'},
                                    data={'email': 'admin@test', 'password': 'pw'})
        self.assertEqual(response.status_code, 302)
        response = self.client.post('/login', base_url='http://localhost:8000', headers={'Origin': 'http://localhost:9000'},
                                    data={'email': 'admin@test', 'password': 'pw'})
        self._refused(response)

    def test_cloud_tasks_reach_their_own_check(self):
        # No browser headers: past this check, and then the OIDC token decides
        response = self.client.post('/internal/tasks/social-stats', base_url=BASE)
        self.assertEqual(response.status_code, 401)
        self.assertNotEqual(response.get_data(as_text=True), REFUSED)

    def test_the_api_reaches_its_key_check(self):
        with mock.patch.dict(os.environ, {'CONTENT_API_KEY': 'the-key'}):
            without = self.client.post('/api/content/packages', base_url=BASE, json={})
            with_key = self.client.post('/api/content/packages', base_url=BASE, json={},
                                        headers={'Authorization': 'Bearer the-key'})
        self.assertEqual(without.status_code, 401)
        self.assertNotIn(with_key.status_code, (401, 403))

    def test_google_sends_the_visitor_back_from_another_site(self):
        # A GET from Google's page. No state in this session, so it goes to log in, not to a refusal.
        with mock.patch('services.google_signin.enabled', return_value=True):
            response = self.client.get('/login/google/done?code=c&state=s', base_url=BASE,
                                       headers={'Sec-Fetch-Site': 'cross-site'})
        self.assertEqual(response.status_code, 302)

    def test_the_browsers_inside_tiktok_and_instagram_can_sign_up_and_log_in(self):
        for number, agent in enumerate((TIKTOK_APP, INSTAGRAM_APP)):
            with self.subTest(agent=agent):
                client = app.test_client()
                # They arrive by a link from the app, then send this site's own form
                self.assertEqual(client.get('/register', base_url=BASE, headers={'User-Agent': agent, 'Sec-Fetch-Site': 'cross-site'}).status_code, 200)
                response = client.post('/register', base_url=BASE, headers={'User-Agent': agent, **SAME},
                                       data={'email': f'app{number}@test', 'password': 'pw'})
                self.assertEqual(response.status_code, 302)
                self.assertIn('remember_token=', ''.join(response.headers.getlist('Set-Cookie')))
                self.assertIsNotNone(self._user(f'app{number}@test'))

    def test_the_session_cookie_is_not_sent_on_a_post_from_another_site(self):
        response = self.client.get('/login?ref=tiktok', base_url=BASE)
        cookie = next(c for c in response.headers.getlist('Set-Cookie') if c.startswith('session='))
        self.assertIn('SameSite=Lax', cookie)
        self.assertIn('HttpOnly', cookie)

    def test_logging_out_takes_a_post(self):
        self._sign_in()
        self.assertEqual(self.client.get('/logout', base_url=BASE).status_code, 405)
        self._refused(self._post('/logout', ELSEWHERE))
        self.assertTrue(self._signed_in())
        self.assertEqual(self._post('/logout', SAME).status_code, 302)
        self.assertFalse(self._signed_in())


if __name__ == '__main__':
    unittest.main()
