"""The site menu: one list (routes/_shared.MENU) drawn in the top bar, the phone menu and the Discover page's menu."""
import os
import sys
import unittest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from tests import test_recipe_v2_view as view_tests  # noqa: E402  (sets the test environment)
from database.models import User, db  # noqa: E402


class SiteMenuTests(unittest.TestCase):
    setUp, tearDown = view_tests.RecipeV2ViewTests.setUp, view_tests.RecipeV2ViewTests.tearDown

    def test_visitors_see_the_public_menu_and_sign_up(self):
        html = self.client.get('/recipes').get_data(as_text=True)
        for text in ('Discover recipes', 'All recipes', 'Collections', 'All ingredients', 'href="/learn"', 'Sign up', 'Log in'):
            self.assertIn(text, html)
        for text in ('Saved', 'Cook next', 'New recipe', 'Many recipes at once', 'Become a Chef', 'Get Started'):
            self.assertNotIn(text, html)

    def test_admins_see_everything_in_every_menu(self):
        self.client.post('/login', data={'email': 'admin@test', 'password': 'pw'})
        html = self.client.get('/recipes').get_data(as_text=True)
        # The top bar and the phone menu, from the same list
        for text in ('Saved', 'Made', 'Cook next', 'Recipe Mirror', 'Many recipes at once', 'Notes on recipes', 'New article'):
            self.assertEqual(html.count(f'{text}</a>'), 2, text)
        self.assertIn('Log out', html)
        # The Discover page has its own header and a slide-over menu: the same items again
        discover = self.client.get('/').get_data(as_text=True)
        self.assertEqual(discover.count('Many recipes at once</a>'), 2)

    def test_a_signed_in_user_sees_their_lists_but_not_admin(self):
        user = User(email='cook@test')
        user.set_password('pw')
        db.session.add(user)
        db.session.commit()
        self.client.post('/login', data={'email': 'cook@test', 'password': 'pw'})
        html = self.client.get('/recipes').get_data(as_text=True)
        self.assertIn('Cook next</a>', html)
        self.assertNotIn('New recipe</a>', html)

    def test_learn_has_both_addresses(self):
        self.assertEqual(self.client.get('/learn').status_code, 200)
        self.assertEqual(self.client.get('/become-a-chef').status_code, 200)


if __name__ == '__main__':
    unittest.main()
