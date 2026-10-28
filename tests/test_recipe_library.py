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
from werkzeug.datastructures import MultiDict  # noqa: E402

from services.recipe_library import Filters, counts, feed_ids, for_the_day, from_args, quick, recipe_page  # noqa: E402
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
        self.assertIn(f'data-made="{made.id}" aria-pressed="true"', html)

    def test_the_list_page_with_search_and_more(self):
        for n in range(3):
            self.recipe(f'Dish {n}')
        html = self.client.get('/recipes?q=dish&time=30&sort=quick').get_data(as_text=True)
        self.assertIn('3 dishes', html)
        self.assertNotIn('Show more', html)
        self.assertEqual(self.client.get('/recipes?shown=abc').status_code, 200)

    def test_chips_from_the_address(self):
        f, groups = from_args(MultiDict([('protein', 'Seafood'), ('diet', 'vegan'), ('diet', 'martian'),
                                         ('time', '30'), ('spice', '0'), ('q', ' pasta ')]))
        self.assertIn('Salmon', f.proteins)  # a protein group filters on its labels
        self.assertEqual((f.diets, f.time, f.spice, f.q), (['vegan'], '30', ['0'], 'pasta'))  # unknown values dropped
        by_key = {g['key']: g for g in groups}
        self.assertTrue(by_key['time']['single'])
        self.assertTrue(by_key['cuisine']['more'])
        self.assertIn(('Seafood', 'Seafood', True), by_key['protein']['options'])
        self.assertEqual(from_args(MultiDict())[0], Filters())  # nothing chosen filters nothing

    def test_heat_filter_counts_unknown_as_mild(self):
        hot = self.recipe('Vindaloo')
        hot.spice_level = 3
        mild = self.recipe('Porridge')
        mild.spice_level = None
        db.session.commit()
        self.assertEqual(self.titles(f=Filters(spice=['3'])), ['Vindaloo'])
        self.assertEqual(self.titles(f=Filters(spice=['0'])), ['Porridge'])

    def test_the_list_has_chips_and_no_table_or_bulk_delete(self):
        self.recipe('Dish')
        html = self.client.get('/recipes?diet=vegan').get_data(as_text=True)
        self.assertIn('name="diet" value="vegan" checked', html)
        self.assertIn('1 in use', html)
        self.assertIn('Clear all', html)
        for gone in ('Table', 'bulk-action-bar', 'recipe-select-cb', 'inspectorModal'):
            self.assertNotIn(gone, html)

    def pictured(self, title, **kw):
        r = self.recipe(title, **kw)
        r.image_filename = f'{title}.webp'
        db.session.commit()
        return r

    def test_discover_shows_a_dish_once(self):
        root = self.pictured('Carbonara')
        for n in range(3):
            self.pictured(f'Carbonara {n}', base=root)
        other = self.pictured('Lasagne')
        shown = [r['id'] for r in self.client.get('/api/feed/recipes').get_json()['recipes']]
        self.assertCountEqual(shown, [root.id, other.id])  # the base recipe stands for its versions

        root.image_filename = None  # without a picture a version stands in
        db.session.commit()
        self.assertEqual(len(feed_ids()), 2)
        self.assertNotIn(root.id, feed_ids())

    def test_discover_skips_dishes_seen_in_any_version(self):
        root = self.pictured('Carbonara')
        version = self.pictured('Carbonara by the gourmet', base=root)
        other = self.pictured('Lasagne')
        db.session.add(UserRecipeInteraction(user_id=self.user.id, recipe_id=version.id, status='pass'))
        db.session.commit()
        self.assertEqual(feed_ids(self.user), [other.id])
        db.session.add(UserRecipeInteraction(user_id=self.user.id, recipe_id=other.id, status='favorite'))
        db.session.commit()
        self.assertEqual(feed_ids(self.user), [version.id])  # all seen: the passed ones again

    def test_shortcuts_switch_one_choice(self):
        links = {label: (args, on) for label, args, on in quick(MultiDict([('diet', 'vegan'), ('time', '45'), ('shown', '96')]))}
        args, on = links['Vegetarian']
        self.assertFalse(on)
        self.assertEqual(args.getlist('diet'), ['vegan', 'vegetarian'])
        self.assertNotIn('shown', args)  # back to the first page
        self.assertEqual(links['Under 30 min'][0].getlist('time'), ['30'])  # one time at a time
        args, on = dict((l, (a, o)) for l, a, o in quick(MultiDict([('diet', 'vegetarian')])))['Vegetarian']
        self.assertTrue(on)
        self.assertEqual(args.getlist('diet'), [])

    def test_admins_can_switch_the_list_layout(self):
        self.recipe('Dish')
        admin = User(email='admin@test', is_admin=True)
        admin.set_password('pw')
        db.session.add(admin)
        db.session.commit()
        self.client.set_cookie('library_layout', 'drawer')
        self.client.post('/login', data={'email': 'cook@test', 'password': 'pw'})
        self.assertNotIn('lv-drawer', self.client.get('/recipes').get_data(as_text=True))  # not for other people
        self.client.get('/logout')
        self.client.post('/login', data={'email': 'admin@test', 'password': 'pw'})
        for layout, mark in (('pills', 'data-lv-pill'), ('rail', 'lv-rail'), ('drawer', 'data-lv-drawer'), ('today', 'lib-head')):
            self.client.set_cookie('library_layout', layout)
            html = self.client.get('/recipes?diet=vegan&q=dish').get_data(as_text=True)
            self.assertIn(mark, html, layout)
            self.assertIn('data-lib-switch', html)
        self.client.set_cookie('library_layout', 'drawer')
        self.assertIn('Under 30 min', self.client.get('/recipes').get_data(as_text=True))

    def admin(self):
        admin = User(email='admin@test', is_admin=True)
        admin.set_password('pw')
        db.session.add(admin)
        db.session.commit()
        self.client.post('/login', data={'email': 'admin@test', 'password': 'pw'})

    def test_the_drawer_counts_and_finds_empty_choices(self):
        quick_dish = self.recipe('Quick', minutes=15)
        quick_dish.heat_source = 'pan'
        self.recipe('Slow', minutes=90).heat_source = 'oven'
        db.session.commit()
        got = counts('discover', MultiDict([('time', '20')]))
        self.assertEqual(got['total'], 1)
        self.assertIn(['heat_source', 'oven'], got['empty'])  # nothing quick in the oven
        self.assertNotIn(['heat_source', 'pan'], got['empty'])
        self.assertNotIn(['time', '20'], got['empty'])  # already chosen

        self.assertEqual(self.client.get('/api/recipes/count').status_code, 403)  # admins only, as a trial
        self.admin()
        self.assertEqual(self.client.get('/api/recipes/count?time=20').get_json()['total'], 1)

    def test_shortcuts_for_the_day(self):
        from datetime import date
        labels = lambda day: [label for _, _, label in for_the_day(day)]  # noqa: E731
        self.assertEqual(labels(date(2026, 12, 15)), ['Christmas', 'Weeknight'])  # a Tuesday
        self.assertEqual(labels(date(2026, 7, 3)), ['Summer BBQ', 'Weekend'])  # a Friday
        self.assertEqual(labels(date(2026, 10, 28)), ['Weeknight'])
        shown = [label for label, _, _ in quick(MultiDict(), date(2026, 10, 31))]
        self.assertEqual(shown[0], 'Weekend')
        self.assertNotIn('Weeknight', shown)

    def test_admins_switch_the_drawer_tweaks(self):
        self.recipe('Dish', diets=('vegan',))
        self.admin()
        self.client.set_cookie('library_layout', 'drawer')
        html = self.client.get('/recipes?diet=vegan').get_data(as_text=True)  # all on until switched off
        for mark in ('tw-active', 'tw-calm', 'data-instant', 'data-count=', 'Remove Vegan', 'data-tw-switch'):
            self.assertIn(mark, html)
        self.client.set_cookie('library_tweaks', 'calm')
        html = self.client.get('/recipes?diet=vegan').get_data(as_text=True)
        self.assertIn('tw-calm', html)
        for mark in ('tw-active', 'data-instant', 'data-count=', 'Remove Vegan'):
            self.assertNotIn(mark, html)
        self.client.set_cookie('library_layout', 'pills')  # the tweaks are the drawer's
        self.assertNotIn('tw-calm', self.client.get('/recipes').get_data(as_text=True))

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
