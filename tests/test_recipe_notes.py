"""Admin notes on a recipe: written in the admin chip, kept, and copied out as text (routes/recipe_notes_routes.py)."""
import datetime
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
os.environ.pop('K_SERVICE', None)

from app import app  # noqa: E402
from database.models import Recipe, RecipeNote, User, db  # noqa: E402
from services.recipe_notes import as_text  # noqa: E402
from services.recipe_v2.generate import refresh  # noqa: E402
from services.recipe_v2.store import save_v2  # noqa: E402

FETCH = {'X-Requested-With': 'fetch'}


class RecipeNoteTests(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        self.ctx = app.app_context()
        self.ctx.push()
        db.drop_all()
        db.create_all()
        for email, is_admin in (('admin@test', True), ('user@test', False)):
            u = User(email=email, is_admin=is_admin)
            u.set_password('pw')
            db.session.add(u)
        with open(os.path.join(ROOT, 'data', 'pilot_v2', 'fasit', 'carbonara.json'), encoding='utf-8') as f:
            data = json.load(f)
        recipe = Recipe(title=data['title'], cuisine='', difficulty='', status='approved', schema_version=2, language='nb',
                        settings=['vegetarian'])
        db.session.add(recipe)
        save_v2(recipe, data, {})
        db.session.flush()
        refresh(recipe)
        db.session.commit()
        self.recipe_id = recipe.id
        self.client = app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def login(self, email='admin@test'):
        self.client.post('/login', data={'email': email, 'password': 'pw'})

    def add(self, text, place='cook · step 5 (Brown it)'):
        return self.client.post(f'/recipe/{self.recipe_id}/notes', data={'text': text, 'place': place, 'page': 'cook'}, headers=FETCH)

    def test_a_note_is_kept_with_where_it_was_written_and_the_chip_part_comes_back(self):
        self.login()
        res = self.add('The timer should start when the sauce boils')
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)
        self.assertIn('data-notes', html)
        self.assertIn('The timer should start when the sauce boils', html)
        self.assertIn('1 open', html)
        note = db.session.execute(db.select(RecipeNote)).scalar_one()
        self.assertEqual(note.place, 'cook · step 5 (Brown it)')
        self.assertFalse(note.done)

    def test_an_empty_note_is_not_kept(self):
        self.login()
        self.add('   ')
        self.assertEqual(db.session.execute(db.select(db.func.count(RecipeNote.id))).scalar(), 0)

    def test_without_the_script_the_form_goes_back_to_the_page_but_never_off_the_site(self):
        self.login()
        res = self.client.post(f'/recipe/{self.recipe_id}/notes', data={'text': 'x', 'next': f'/recipe/{self.recipe_id}/cook'})
        self.assertTrue(res.headers['Location'].endswith(f'/recipe/{self.recipe_id}/cook'))
        res = self.client.post(f'/recipe/{self.recipe_id}/notes', data={'text': 'y', 'next': '//evil.example/x'})
        self.assertTrue(res.headers['Location'].endswith(f'/recipe/{self.recipe_id}'))

    def test_only_admins_write_notes(self):
        self.login('user@test')
        self.add('Not mine to write')
        self.assertEqual(db.session.execute(db.select(db.func.count(RecipeNote.id))).scalar(), 0)

    def test_done_takes_a_note_out_of_the_open_ones_and_back(self):
        self.login()
        self.add('First')
        note = db.session.execute(db.select(RecipeNote)).scalar_one()
        html = self.client.post(f'/recipe/notes/{note.id}/done', data={'page': 'cook'}, headers=FETCH).get_data(as_text=True)
        self.assertNotIn('First', html)
        db.session.refresh(note)
        self.assertTrue(note.done)
        self.assertNotIn('First', self.client.get('/admin/notes').get_data(as_text=True))
        self.assertIn('First', self.client.get('/admin/notes?all=1').get_data(as_text=True))
        self.client.post(f'/recipe/notes/{note.id}/done', headers=FETCH)
        db.session.refresh(note)
        self.assertFalse(note.done)

    def test_the_notes_are_in_the_admin_chip_on_the_recipe_pages_and_not_for_others(self):
        self.login()
        self.add('Less salt')
        html = self.client.get(f'/recipe/{self.recipe_id}').get_data(as_text=True)
        self.assertIn('data-note-form', html)
        self.assertIn('Less salt', html)
        self.client.get('/logout')
        self.login('user@test')
        self.assertNotIn('data-note-form', self.client.get(f'/recipe/{self.recipe_id}').get_data(as_text=True))

    def test_the_text_to_copy_names_the_recipe_its_address_and_each_note(self):
        recipe = db.session.get(Recipe, self.recipe_id)
        notes = [RecipeNote(recipe_id=recipe.id, place='prep', text='Onion in wedges\nnot chopped',
                            created_at=datetime.datetime(2026, 10, 23, 16, 40)),
                 RecipeNote(recipe_id=recipe.id, text='Too much pepper', created_at=datetime.datetime(2026, 10, 23, 17, 5))]
        text = as_text(recipe, notes, f'https://thelazychef.app/recipe/{recipe.id}')
        self.assertEqual(text.splitlines(), [
            f'Recipe {recipe.id}: {recipe.title} (vegetarian; rev {recipe.revision})',
            f'https://thelazychef.app/recipe/{recipe.id}',
            '- [prep] Onion in wedges',
            '  not chopped (23.10 18:40)',
            '- Too much pepper (23.10 19:05)',
        ])

    def test_the_notes_go_with_the_recipe(self):
        self.login()
        self.add('Gone with it')
        db.session.delete(db.session.get(Recipe, self.recipe_id))
        db.session.commit()
        self.assertEqual(db.session.execute(db.select(db.func.count(RecipeNote.id))).scalar(), 0)


if __name__ == '__main__':
    unittest.main()
