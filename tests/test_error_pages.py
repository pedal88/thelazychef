"""Pages for an address that does not exist and an error on our side (routes/error_routes.py), and the short addresses
from the posts when they are typed a little differently."""
import os
import sys
import unittest

from werkzeug.exceptions import InternalServerError

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

os.environ['DB_BACKEND'] = 'local'
os.environ['DATABASE_URL'] = 'sqlite://'
os.environ['STORAGE_BACKEND'] = 'local'
os.environ.setdefault('SECRET_KEY', 'test-secret')
os.environ.setdefault('GOOGLE_API_KEY', 'test-key')
os.environ.pop('K_SERVICE', None)

from app import app  # noqa: E402
from database.models import db  # noqa: E402
from routes.error_routes import server_error  # noqa: E402


class ErrorPageTests(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        self.ctx = app.app_context()
        self.ctx.push()
        db.drop_all()
        db.create_all()
        self.client = app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def test_an_address_that_does_not_exist_has_a_page_with_a_way_on(self):
        response = self.client.get('/no-such-page')
        self.assertEqual(response.status_code, 404)
        html = response.get_data(as_text=True)
        self.assertIn('That page is not here', html)
        self.assertIn('See all recipes', html)
        self.assertIn('id="mobile-menu"', html)

    def test_a_short_address_typed_differently_goes_to_the_real_one(self):
        for typed, real in (('/TikTok/4', '/tiktok/4'), ('/tiktok/4/', '/tiktok/4'), ('/TIKTOK', '/tiktok'),
                            ('/tiktok/', '/tiktok'), ('/IG/4', '/ig/4'), ('/Ig', '/ig'), ('/instagram/4', '/ig/4'),
                            ('/tt/4', '/tiktok/4'), ('/TikTok/4?x=1', '/tiktok/4?x=1')):
            with self.subTest(typed):
                response = self.client.get(typed)
                self.assertEqual((response.status_code, response.location), (302, real))

    def test_other_addresses_are_not_sent_anywhere(self):
        for typed in ('/tiktok/4/5', '/TikTokk/4', '/recipes/', '/post/tiktok/4', '//tiktok.example/4'):
            with self.subTest(typed):
                self.assertEqual(self.client.get(typed).status_code, 404)

    def test_scripts_and_files_keep_the_plain_answer(self):
        for typed in ('/api/no-such', '/static/no-such.png', '/internal/no-such'):
            with self.subTest(typed):
                response = self.client.get(typed)
                self.assertEqual(response.status_code, 404)
                self.assertNotIn('That page is not here', response.get_data(as_text=True))

    def test_an_error_on_our_side_has_a_page_that_needs_no_database(self):
        with app.test_request_context('/recipes'):
            html, status = server_error(InternalServerError())
        self.assertEqual(status, 500)
        self.assertIn('Something went wrong on our side', html)
        self.assertNotIn('mobile-menu', html)
        with app.test_request_context('/api/recipes/count'):
            self.assertIsInstance(server_error(InternalServerError()), InternalServerError)


if __name__ == '__main__':
    unittest.main()
