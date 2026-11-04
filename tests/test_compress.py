"""Answers in gzip (utils/compress.py): text that is big enough, when the browser takes it, and the same content."""
import gzip
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
from database.models import db  # noqa: E402

GZIP = {'Accept-Encoding': 'gzip, deflate, br'}


class CompressTests(unittest.TestCase):
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

    def test_a_page_comes_in_gzip_and_says_so(self):
        plain = self.client.get('/privacy')
        packed = self.client.get('/privacy', headers=GZIP)
        self.assertNotIn('Content-Encoding', plain.headers)
        self.assertEqual(packed.headers['Content-Encoding'], 'gzip')
        self.assertIn('Accept-Encoding', packed.headers['Vary'])
        self.assertLess(len(packed.data), len(plain.data))
        self.assertEqual(gzip.decompress(packed.data), plain.data)
        self.assertEqual(int(packed.headers['Content-Length']), len(packed.data))

    def test_a_static_file_too(self):
        plain = self.client.get('/static/css/library.css')
        packed = self.client.get('/static/css/library.css', headers=GZIP)
        self.assertEqual(packed.headers['Content-Encoding'], 'gzip')
        self.assertEqual(gzip.decompress(packed.data), plain.data)

    def test_an_image_stays_as_it_is(self):
        answer = self.client.get('/static/brand/avatar.png', headers=GZIP)
        self.assertEqual(answer.status_code, 200)
        self.assertNotIn('Content-Encoding', answer.headers)

    def test_a_file_not_changed_still_answers_304(self):
        first = self.client.get('/static/css/library.css', headers=GZIP)
        again = self.client.get('/static/css/library.css', headers={**GZIP, 'If-None-Match': first.headers['ETag']})
        self.assertEqual(again.status_code, 304)
        self.assertEqual(again.data, b'')


if __name__ == '__main__':
    unittest.main()
