"""Photos on feedback ("I made this" and the recipe list's drawer): POST /api/interactions/recipe/<id>/feedback stores
them, turns HEIC into JPEG, and answers with the stored URLs and the names of the photos it could not save, so the form
can show the stored photos instead of a preview the browser cannot draw."""
import io
import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

os.environ['DB_BACKEND'] = 'local'
os.environ['DATABASE_URL'] = 'sqlite://'
os.environ['STORAGE_BACKEND'] = 'local'
os.environ.setdefault('SECRET_KEY', 'test-secret')
os.environ.setdefault('GOOGLE_API_KEY', 'test-key')
os.environ.pop('K_SERVICE', None)

import pillow_heif  # noqa: E402
from PIL import Image  # noqa: E402

from app import app  # noqa: E402
from database.models import Recipe, User, UserRecipeInteraction, db  # noqa: E402
from services.storage_service import LocalStorageProvider  # noqa: E402

pillow_heif.register_heif_opener()


def image_bytes(fmt):
    buf = io.BytesIO()
    Image.new('RGB', (8, 8), 'orange').save(buf, format=fmt)
    return buf.getvalue()


class FeedbackPhotoTests(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        self.ctx = app.app_context()
        self.ctx.push()
        db.drop_all()
        db.create_all()
        self.user = User(email='cook@test')
        self.user.set_password('pw')
        self.recipe = Recipe(title='Soft-boiled eggs', status='approved', cuisine='Nordic', difficulty='Simplistic')
        db.session.add_all([self.user, self.recipe])
        db.session.commit()
        self.root = tempfile.mkdtemp()
        self.storage = app.extensions['storage_provider']
        app.extensions['storage_provider'] = LocalStorageProvider(self.root)
        self.client = app.test_client()
        self.client.post('/login', data={'email': 'cook@test', 'password': 'pw'})
        self.url = f'/api/interactions/recipe/{self.recipe.id}/feedback'

    def tearDown(self):
        app.extensions['storage_provider'] = self.storage
        shutil.rmtree(self.root, ignore_errors=True)
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def stored(self, url):
        with open(os.path.join(self.root, url.lstrip('/')), 'rb') as f:
            return Image.open(io.BytesIO(f.read()))

    def test_heic_is_stored_as_jpeg_and_the_answer_says_where(self):
        res = self.client.post(self.url, data={
            'comment': '11, 12 and 13 minutes next time',
            'photos': [(io.BytesIO(image_bytes('HEIF')), 'IMG_0420.HEIC'),
                       (io.BytesIO(image_bytes('PNG')), 'plate.png'),
                       (io.BytesIO(b'not a photo'), 'broken.heic'),
                       (io.BytesIO(b'notes'), 'notes.txt')],
        }, content_type='multipart/form-data').get_json()

        self.assertTrue(res['success'])
        self.assertEqual(res['skipped'], ['broken.heic', 'notes.txt'])
        heic, png = res['user_photos']
        self.assertTrue(heic.startswith('/static/user_uploads/') and heic.endswith('.jpg'))
        self.assertEqual(self.stored(heic).format, 'JPEG')
        self.assertEqual(self.stored(png).format, 'PNG')
        mark = db.session.get(UserRecipeInteraction, (self.user.id, self.recipe.id))
        self.assertEqual(mark.user_photos, res['user_photos'])
        self.assertEqual(self.client.get(f'/api/interactions/recipe/{self.recipe.id}').get_json()['user_photos'],
                         res['user_photos'])

    def test_saving_again_with_the_stored_photos_kept_adds_none(self):
        first = self.client.post(self.url, data={'photos': [(io.BytesIO(image_bytes('PNG')), 'plate.png')]},
                                 content_type='multipart/form-data').get_json()['user_photos']
        # The form now holds the stored URL, not the file, and sends it as kept
        again = self.client.post(self.url, data={'keep_photos': json.dumps(first)},
                                 content_type='multipart/form-data').get_json()
        self.assertEqual((again['user_photos'], again['skipped']), (first, []))


if __name__ == '__main__':
    unittest.main()
