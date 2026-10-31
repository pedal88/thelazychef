"""Signing up where you are (services/signup.py, routes/auth_routes.py): a visitor's Save, Cook next and I made this
send them to sign up, which does what they pressed and brings them back; signing in keeps them signed in; emails are
one account whatever their case; and next never leaves the site."""
import json
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
from database.models import Recipe, User, UserQueue, UserRecipeInteraction, db  # noqa: E402
from services.recipe_v2.store import save_v2  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
with open(os.path.join(ROOT, 'data', 'pilot_v2', 'fasit', 'carbonara.json'), encoding='utf-8') as f:
    CARBONARA = json.load(f)


class SignupTests(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        self.ctx = app.app_context()
        self.ctx.push()
        db.drop_all()
        db.create_all()
        self.recipe = Recipe(title='Carbonara', status='approved', cuisine='Italian', difficulty='Simplistic')
        self.draft = Recipe(title='Draft', status='draft', cuisine='', difficulty='')
        db.session.add_all([self.recipe, self.draft])
        save_v2(self.recipe, CARBONARA)
        db.session.commit()
        self.client = app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def register(self, email='cook@test', query=''):
        return self.client.post('/register' + query, data={'email': email, 'password': 'pw'})

    def user(self, email='cook@test'):
        return db.session.execute(db.select(User).filter_by(email=email)).scalar()

    def mark(self, user):
        db.session.expire_all()
        return db.session.get(UserRecipeInteraction, (user.id, self.recipe.id))

    def query(self, action, recipe=None):
        return f'?next=/recipe/{self.recipe.id}&do={action}&recipe={(recipe or self.recipe).id}'

    # Doing what was pressed

    def test_i_made_this_signs_up_marks_it_made_and_comes_back(self):
        response = self.register(query=self.query('made'))
        self.assertEqual(response.location, f'/recipe/{self.recipe.id}')
        mark = self.mark(self.user())
        self.assertTrue(mark.is_made)
        self.assertEqual(mark.made_count, 1)
        self.assertIn(f'You made {self.recipe.title}', self.client.get(response.location).get_data(as_text=True))

    def test_save_and_cook_next_are_done_once_signed_up(self):
        self.register(query=self.query('save'))
        user = self.user()
        self.assertEqual(self.mark(user).status, 'favorite')
        self.client.get('/logout')
        self.client.post('/login' + self.query('queue'), data={'email': 'cook@test', 'password': 'pw'})
        self.client.post('/login' + self.query('queue'), data={'email': 'cook@test', 'password': 'pw'})  # adds once
        self.assertEqual(len(db.session.execute(db.select(UserQueue).filter_by(user_id=user.id)).scalars().all()), 1)
        self.assertEqual(self.mark(user).status, 'favorite')  # Cook next does not take the save away

    def test_an_existing_email_goes_to_log_in_with_what_was_pressed(self):
        self.register()
        self.client.get('/logout')
        response = self.register('Cook@Test ', query=self.query('made'))
        self.assertTrue(response.location.startswith('/login?'))
        self.assertIn('do=made', response.location)
        self.assertEqual(len(db.session.execute(db.select(User)).scalars().all()), 1)

    def test_nothing_is_done_for_a_recipe_a_visitor_cannot_see_or_an_unknown_action(self):
        self.register(query=self.query('made', self.draft))
        self.assertIsNone(db.session.get(UserRecipeInteraction, (self.user().id, self.draft.id)))
        self.client.get('/logout')
        self.register('other@test', query=f'?do=delete&recipe={self.recipe.id}')
        self.assertIsNone(self.mark(self.user('other@test')))

    def test_the_forms_carry_what_was_pressed(self):
        page = self.client.get('/register' + self.query('made')).get_data(as_text=True)
        self.assertIn(f'Make an account and {self.recipe.title} goes in your Made list', page)
        self.assertIn(f'action="/register?next=/recipe/{self.recipe.id}&amp;do=made&amp;recipe={self.recipe.id}"', page)
        self.assertIn(f'href="/login?next=/recipe/{self.recipe.id}&amp;do=made&amp;recipe={self.recipe.id}"', page)

    def test_a_visitor_is_offered_sign_up_on_the_recipe(self):
        page = self.client.get(f'/recipe/{self.recipe.id}').get_data(as_text=True)
        for action in ('save', 'queue', 'made'):
            self.assertIn(f'/register?next=/recipe/{self.recipe.id}&amp;do={action}&amp;recipe={self.recipe.id}', page)

    # Signing in

    def test_signing_in_keeps_you_signed_in(self):
        response = self.register()
        self.assertIn('remember_token=', response.headers.get('Set-Cookie', '') + ''.join(
            response.headers.getlist('Set-Cookie')))

    def test_an_email_is_one_account_whatever_its_case_and_spaces(self):
        self.register(' Cook@Test ')
        self.assertIsNotNone(self.user('cook@test'))
        self.client.get('/logout')
        response = self.client.post('/login', data={'email': 'COOK@test', 'password': 'pw'})
        self.assertEqual(response.location, '/recipes')

    def test_an_account_from_before_with_capitals_still_logs_in(self):
        old = User(email='Old@Test')
        old.set_password('pw')
        db.session.add(old)
        db.session.commit()
        response = self.client.post('/login', data={'email': 'old@test', 'password': 'pw'})
        self.assertEqual(response.location, '/recipes')

    def test_next_never_leaves_the_site(self):
        for target in ('https://evil.example/', '//evil.example/', '/\\evil.example'):
            with self.subTest(target=target):
                client = app.test_client()
                response = client.post('/register?next=' + target, data={'email': f'{len(target)}@test', 'password': 'pw'})
                self.assertEqual(response.location, '/recipes')


if __name__ == '__main__':
    unittest.main()
