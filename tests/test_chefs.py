"""The chef editor reads from and saves to the chef table."""
import json
import os
import sys
import unittest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Same setup as test_smoke: must be set before app is imported
os.environ['DB_BACKEND'] = 'local'
os.environ['DATABASE_URL'] = 'sqlite://'
os.environ['STORAGE_BACKEND'] = 'local'
os.environ.setdefault('SECRET_KEY', 'test-secret')
os.environ.setdefault('GOOGLE_API_KEY', 'test-key')
os.environ.pop('K_SERVICE', None)

from app import app  # noqa: E402
from database.models import db, Chef, User  # noqa: E402


class ChefEditorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config['TESTING'] = True
        with app.app_context():
            db.create_all()
            admin = User(email='chef-admin@test', is_admin=True)
            admin.set_password('pw')
            db.session.add(admin)
            db.session.commit()
            cls.admin_id = admin.id

    def setUp(self):
        with app.app_context():
            db.session.add(Chef(
                id='test_full', name='Full Chef', archetype='Old School', description='desc',
                image_filename='full.jpg',
                constraints=json.dumps({'taste_range': {'min': 4, 'max': 5}}),
                diet_preferences='[]',
                cooking_style=json.dumps({'preferred_methods': ['Searing'], 'avoid_methods': []}),
                ingredient_logic=json.dumps({'staples': ['Butter'], 'banned_ingredients': []}),
                instruction_style=json.dumps({'tone': 'Strict', 'example_phrase': 'Sear it.'}),
            ))
            # Like the rows scripts/fix_missing_chefs.py creates: no persona data
            db.session.add(Chef(id='test_bare', name='Bare Chef', archetype='', description='',
                                image_filename=''))
            db.session.commit()
        self.client = app.test_client()
        with self.client.session_transaction() as session:
            session['_user_id'] = str(self.admin_id)
            session['_fresh'] = True

    def tearDown(self):
        with app.app_context():
            db.session.execute(db.delete(Chef).where(Chef.id.in_(['test_full', 'test_bare'])))
            db.session.commit()

    def _chef(self, chef_id):
        with app.app_context():
            return db.session.get(Chef, chef_id)

    def test_editor_lists_chefs_from_db(self):
        res = self.client.get('/admin/chefs')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Full Chef', res.data)
        self.assertIn(b'Bare Chef', res.data)

    def test_save_updates_db_and_keeps_image(self):
        res = self.client.post('/admin/chefs/save', json={'chefs': [{
            'id': 'test_full',
            'name': 'Renamed Chef',
            'constraints': {'taste_range': {'min': 1, 'max': 2}},
            'instruction_style': {'tone': 'Gentle', 'example_phrase': ''},
        }]})
        self.assertEqual(res.status_code, 200, res.data)
        chef = self._chef('test_full')
        self.assertEqual(chef.name, 'Renamed Chef')
        self.assertEqual(json.loads(chef.constraints), {'taste_range': {'min': 1, 'max': 2}})
        self.assertEqual(json.loads(chef.instruction_style)['tone'], 'Gentle')
        # Not in the payload, so unchanged
        self.assertEqual(chef.image_filename, 'full.jpg')
        self.assertEqual(chef.archetype, 'Old School')

    def test_unknown_id_saves_nothing(self):
        res = self.client.post('/admin/chefs/save', json={'chefs': [
            {'id': 'test_full', 'name': 'Should Not Save'},
            {'id': 'no_such_chef', 'name': 'Ghost'},
        ]})
        self.assertEqual(res.status_code, 404)
        self.assertIn('no_such_chef', res.get_json()['error'])
        self.assertEqual(self._chef('test_full').name, 'Full Chef')

    def test_invalid_payload(self):
        for body in ({}, {'chefs': 'x'}, ['not', 'an', 'object']):
            res = self.client.post('/admin/chefs/save', json=body)
            self.assertEqual(res.status_code, 400, body)


if __name__ == '__main__':
    unittest.main()
