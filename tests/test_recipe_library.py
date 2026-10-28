"""The recipe library (/recipes, services/recipe_library.py): one card per dish, its versions, time, search, the
pages, and the Made mark in every list."""
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

import json  # noqa: E402

from app import app  # noqa: E402
from database.models import Recipe, RecipeDiet, User, UserRecipeInteraction, db  # noqa: E402
from services.recipe_library import Filters, recipe_page  # noqa: E402
from services.recipe_v2.store import save_v2  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
with open(os.path.join(ROOT, 'data', 'pilot_v2', 'fasit', 'carbonara.json'), encoding='utf-8') as f:
    CARBONARA = json.load(f)


class RecipeLibraryTests(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        self.ctx = app.app_context()
        self.ctx.push()
        db.drop_all()
        db.create_all()
        self.user = User(email='cook@test')
        self.user.set_password('pw')
        db.session.add(self.user)
        db.session.commit()
        self.client = app.test_client()

    def tearDown(self):
        # Other test modules share the in-memory database; leave it empty.
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def recipe(self, title, status='approved', base=None, minutes=30, diets=()):
        r = Recipe(title=title, status=status, cuisine='Italian', difficulty='Simplistic',
                   base_recipe_id=base.id if base else None)
        db.session.add(r)
        save_v2(r, CARBONARA)  # writes the fixture's title and metadata: set ours after it
        r.title, r.cuisine, r.difficulty, r.prep_time_mins = title, 'Italian', 'Simplistic', minutes
        r.diets = [RecipeDiet(diet=d) for d in diets]
        db.session.commit()
        return r

    def titles(self, view='discover', f=None, **kw):
        return [r.title for r in recipe_page(view, f or Filters(), **kw).recipes]

    def test_a_dish_and_its_versions_are_one_card(self):
        root = self.recipe('Carbonara')
        self.recipe('Carbonara by the gourmet', base=root)
        self.recipe('Carbonara draft', status='draft', base=root)
        page = recipe_page('discover', Filters())
        self.assertEqual([r.title for r in page.recipes], ['Carbonara'])
        self.assertEqual(page.recipes[0].version_count, 2)  # the draft does not count
        self.assertEqual(page.total, 1)

    def test_a_version_stands_in_when_the_base_recipe_is_not_shown(self):
        root = self.recipe('Carbonara', status='draft')
        self.recipe('Carbonara by the gourmet', base=root)
        self.assertEqual(self.titles(), ['Carbonara by the gourmet'])

        meaty = self.recipe('Lasagne', diets=())
        self.recipe('Vegetarian lasagne', base=meaty, diets=('Vegetarian',))
        self.assertEqual(self.titles(f=Filters(diets=['Vegetarian'])), ['Vegetarian lasagne'])

    def test_saved_shows_the_very_version_saved(self):
        root = self.recipe('Carbonara')
        version = self.recipe('Carbonara by the gourmet', base=root)
        for r in (root, version):
            db.session.add(UserRecipeInteraction(user_id=self.user.id, recipe_id=r.id, status='favorite'))
        db.session.commit()
        self.assertCountEqual(self.titles('saved', user=self.user), ['Carbonara', 'Carbonara by the gourmet'])

    def test_time_filter_order_and_hands_on_minutes(self):
        self.recipe('Slow', minutes=90)
        self.recipe('Quick', minutes=15)
        self.recipe('Middle', minutes=40)
        self.assertEqual(self.titles(f=Filters(time='20')), ['Quick'])
        self.assertEqual(self.titles(f=Filters(time='long')), ['Slow'])
        self.assertEqual(self.titles(sort='quick'), ['Quick', 'Middle', 'Slow'])
        self.assertEqual(self.titles(), ['Middle', 'Quick', 'Slow'])  # newest first
        active = sum(s.get('active_minutes') or 0 for s in CARBONARA['steps'])
        self.assertEqual({r.active_mins for r in recipe_page('discover', Filters()).recipes}, {active})

    def test_search_by_title_or_ingredient(self):
        self.recipe('Spaghetti carbonara')
        self.recipe('Pasta 100%')
        self.assertEqual(self.titles(f=Filters(q='CARBO')), ['Spaghetti carbonara'])
        self.assertEqual(len(self.titles(f=Filters(q='guanciale'))), 2)  # a line in both
        self.assertEqual(self.titles(f=Filters(q='100%')), ['Pasta 100%'])  # % is a character, not a wildcard

    def test_a_page_at_a_time(self):
        for n in range(5):
            self.recipe(f'Dish {n}')
        page = recipe_page('discover', Filters(), shown=1)
        self.assertEqual((len(page.recipes), page.total, page.more), (1, 5, True))
        self.assertFalse(recipe_page('discover', Filters(), shown=48).more)

    def test_made_is_marked_in_all_and_cook_next(self):
        made = self.recipe('Made dish')
        db.session.add(UserRecipeInteraction(user_id=self.user.id, recipe_id=made.id, status='pass', is_made=True))
        db.session.commit()
        page = recipe_page('discover', Filters(), user=self.user)
        self.assertTrue(page.recipes[0].interaction.is_made)

        self.client.post('/login', data={'email': 'cook@test', 'password': 'pw'})
        html = self.client.get('/recipes').get_data(as_text=True)
        self.assertIn('data-is-made="true"', html)

    def test_the_list_page_with_search_and_more(self):
        for n in range(3):
            self.recipe(f'Dish {n}')
        html = self.client.get('/recipes?q=dish&time=30&sort=quick').get_data(as_text=True)
        self.assertIn('3 dishes', html)
        self.assertNotIn('Show more', html)
        self.assertEqual(self.client.get('/recipes?shown=abc').status_code, 200)

    def test_the_recipe_page_shows_the_approved_versions(self):
        root = self.recipe('Carbonara')
        version = self.recipe('Carbonara by the gourmet', base=root)
        draft = self.recipe('Carbonara draft', status='draft', base=root)
        html = self.client.get(f'/recipe/{root.id}').get_data(as_text=True)
        self.assertIn(f'/recipe/{version.id}"', html)
        self.assertNotIn(f'/recipe/{draft.id}"', html)
        self.assertIn('Versions · 2', html)
        alone = self.recipe('Alone')
        self.assertNotIn('Versions ·', self.client.get(f'/recipe/{alone.id}').get_data(as_text=True))


if __name__ == '__main__':
    unittest.main()
