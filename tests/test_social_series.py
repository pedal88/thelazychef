"""The post series (services/social_series.py, /social/post): each renders in both sizes with its slide sequence, the
hooks state the post's own numbers and come out the same every time, bad values fall back, the address stays on the
last slide, and the picking keeps a recipe out of a series for a week."""
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
from database.models import Recipe, SocialPost, db  # noqa: E402
from services import social, social_series as series  # noqa: E402
from services.recipe_v2.generate import refresh  # noqa: E402
from services.recipe_v2.store import save_v2  # noqa: E402
from services.recipe_v2.view import page  # noqa: E402

FIXTURES = ('carbonara', 'lasagne', 'tikka', 'brownies', 'burger')


class SeriesTests(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        self.ctx = app.app_context()
        self.ctx.push()
        db.drop_all()
        db.create_all()
        self.ids = []
        for name in FIXTURES:
            with open(os.path.join(ROOT, 'data', 'pilot_v2', 'fasit', f'{name}.json'), encoding='utf-8') as f:
                data = json.load(f)
            recipe = Recipe(title=data['title'], cuisine='Italian', difficulty='', status='approved', schema_version=2,
                            image_filename=f'{name}.png')
            db.session.add(recipe)
            save_v2(recipe, data, {})
            db.session.flush()
            refresh(recipe)
            # What refresh() derived is replaced by what the series need: every dish a 500 kcal, 40 g protein beef
            # dinner in the air fryer with two things to wash
            recipe.heat_source, recipe.protein_type, recipe.cleanup_factor = 'airfryer', 'Beef', 1
            recipe.cuisine = 'Italian'
            recipe.total_calories, recipe.total_protein, recipe.total_carbs, recipe.total_fat = 2000, 160, 200, 80
            recipe.base_servings = 4
            self.ids.append(recipe.id)
        db.session.commit()
        self.client = app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def get(self, **args):
        return self.client.get('/social/post', query_string=args)

    def kinds(self, size='ig', **args):
        first = self.get(size=size, **args)
        self.assertEqual(first.status_code, 200, first.get_data(as_text=True)[:200])
        count = int(first.headers['X-Slides'])
        return [self.get(size=size, slide=n, **args).get_data(as_text=True)
                .split('class="slide size-', 1)[1].split('"', 1)[0].split(' kind-')[1] for n in range(1, count + 1)]

    # The series

    def test_every_series_renders_in_both_sizes_with_its_slides(self):
        one, three, five = str(self.ids[0]), ','.join(map(str, self.ids[:3])), ','.join(map(str, self.ids))
        expected = {
            'airfryer': (one, ['cover', 'airfryer', 'ingredients', 'timebar', 'shop_split', 'end']),
            'got': (three, ['got_cover', 'day', 'day', 'day', 'shop', 'end']),
            'protein': (one, ['cover', 'numbers', 'ingredients', 'timebar', 'shop_split', 'end']),
            'dishes': (one, ['cover', 'wash', 'ingredients', 'timebar', 'timers', 'end']),
            'guess': (one, ['collage', 'ingredients', 'dish', 'end']),
            'cuisine': (five, ['week_cover', 'day', 'day', 'day', 'day', 'day', 'shop', 'end']),
        }
        self.assertEqual(sorted(expected), sorted(series.SERIES))
        for slug, (ids, kinds) in expected.items():
            for size in ('ig', 'tt'):
                with self.subTest(series=slug, size=size):
                    self.assertEqual(self.kinds(size, series=slug, ids=ids, n=3), kinds)
                    html = self.get(size=size, series=slug, ids=ids, n=3, slide=1).get_data(as_text=True)
                    self.assertIn('#3', html)  # the series' number on the first slide
                    self.assertIn(f'width:1080px; height:{social.SIZES[size][1]}px', html)

    def test_the_answer_says_what_the_post_was_made_of(self):
        r = self.get(series='airfryer', ids=self.ids[0], n=7, hook='lazy', cta='save', code=9, size='tt')
        self.assertEqual((r.headers['X-Recipes'], r.headers['X-N'], r.headers['X-Hook'], r.headers['X-Cta']),
                         (str(self.ids[0]), '7', 'lazy', 'save'))
        self.assertEqual(r.headers['X-Views'], 'cover airfryer ingredients timebar shop_split end')
        self.assertEqual(r.headers['X-Look'], 'd')
        self.assertEqual(r.headers['X-Robots-Tag'], 'noindex')
        caption = self.get(series='airfryer', ids=self.ids[0], n=7, cta='save', code=9, size='tt', caption=1)
        text = caption.get_data(as_text=True)
        self.assertIn('thelazychef.app/tiktok/9', text)
        self.assertIn('#airfryer', text)
        self.assertIn('Save', text)

    def test_the_hook_states_the_posts_own_numbers_and_stays_the_same(self):
        view = page(db.session.get(Recipe, self.ids[0]))
        texts = set()
        for _ in range(3):
            r = self.get(series='airfryer', ids=self.ids[0], n=2, hook='lazy')
            texts.add(r.headers['X-Hook-Text'])
        self.assertEqual(len(texts), 1)
        text = texts.pop()
        self.assertIn(str(view['active_min']), text)
        self.assertLessEqual(len(text.split()), series.HOOK_WORDS)
        self.assertIn(text, self.get(series='airfryer', ids=self.ids[0], n=2, hook='lazy', slide=1).get_data(as_text=True))
        number = self.get(series='protein', ids=self.ids[0], n=2, hook='number').headers['X-Hook-Text']
        self.assertIn('40', number)  # 160 g over 4 servings
        self.assertIn(self.get(series='dishes', ids=self.ids[0], n=1).headers['X-Hook-Text'],
                      ('Dishes to wash: 4', '4 dishes to wash. 16 min of work.', 'One dinner, 4 dishes to wash.'))

    def test_every_phrasing_is_at_most_eight_words(self):
        facts = {'n': 7, 'dishes': 3, 'many': True, 'count': 12, 'symbols': 12, 'total': 40, 'active': 9, 'idle': 31,
                 'doer': 'the air fryer', 'doer_cap': 'The air fryer', 'vessels': 2, 'protein': 46, 'kcal': 425, 'ingredient': 'chicken thighs',
                 'ingredient_cap': 'Chicken thighs', 'cuisine': 'Middle Eastern', 'few': True, 'quick': True,
                 'one_two': True}
        lists = [HOOKS for HOOKS in series.HOOKS.values()] + [h for s in series.SERIES.values() for h in s.get('hooks', {}).values()]
        for phrasings in lists:
            for text, needs in phrasings:
                with self.subTest(text=text):
                    self.assertLessEqual(len(text.format(**facts).split()), series.HOOK_WORDS)
                    self.assertTrue(set(needs) <= set(facts))

    def test_a_group_the_post_cannot_say_truly_falls_back(self):
        # Contrast promises a short list and a quick dinner: a long one says a number instead
        facts = {'count': 25, 'total': 90, 'vessels': 5, 'few': False, 'quick': False, 'one_two': False, 'n': 1}
        self.assertIsNone(series.hook('contrast', facts, 'x'))
        group, text = series.hook_for('contrast', facts, 'x', 'dishes')
        self.assertEqual((group, '5' in text), ('number', True))  # the series' own group, with its own numbers
        self.assertEqual(series.hook_for('contrast', facts, 'x')[0], 'number')
        self.assertEqual(series.hook_for('contrast', {**facts, 'count': 6, 'few': True}, 'x', 'dishes'),
                         ('contrast', 'Not 30 ingredients. Just 6.'))

    def test_bad_hook_cta_series_or_recipes_fall_back_or_are_not_found(self):
        r = self.get(series='airfryer', ids=self.ids[0], hook='shout', cta='buy')
        self.assertEqual((r.headers['X-Hook'], r.headers['X-Cta']), ('lazy', 'follow'))
        self.assertEqual(self.get(series='soup', ids=self.ids[0]).status_code, 404)
        self.assertEqual(self.get(series='got', ids=self.ids[0]).status_code, 404)  # got takes three
        self.assertEqual(self.get(series='airfryer', ids='a').status_code, 404)
        self.assertEqual(self.get(series='airfryer', ids=999).status_code, 404)
        self.assertEqual(self.get(series='airfryer', ids=self.ids[0], slide=9).status_code, 404)
        db.session.get(Recipe, self.ids[0]).status = 'draft'
        db.session.commit()
        self.assertEqual(self.get(series='airfryer', ids=self.ids[0]).status_code, 404)

    def test_the_address_stays_on_the_last_slide_small_unless_the_cta_is_the_site(self):
        for cta, small in (('follow', True), ('send', True), ('site', False)):
            with self.subTest(cta=cta):
                html = self.get(series='airfryer', ids=self.ids[0], cta=cta, code=4, size='tt', slide=6).get_data(as_text=True)
                self.assertIn('thelazychef.app/tiktok/4', html)
                self.assertEqual('class="address small"' in html, small)
        bio = self.get(series='airfryer', ids=self.ids[0], cta='bio', code=4, size='ig', slide=6)
        self.assertEqual(bio.headers['X-Cta'], 'bio')
        self.assertIn('link in bio', bio.get_data(as_text=True))
        self.assertEqual(self.get(series='airfryer', ids=self.ids[0], cta='bio', size='tt').headers['X-Cta'], 'site')

    def test_got_asks_for_the_shared_ingredient_and_lists_the_rest_per_dinner(self):
        ids = ','.join(map(str, self.ids[:3]))
        cover = self.get(series='got', ids=ids, n=1, slide=1).get_data(as_text=True)
        self.assertIn('Got beef?', cover)
        self.assertIn('3 dinners', cover)
        shop = self.get(series='got', ids=ids, n=1, slide=5).get_data(as_text=True)
        self.assertIn('One list for all 3', shop)

    def test_the_cuisine_week_is_five_weeknights_and_one_list(self):
        ids = ','.join(map(str, self.ids))
        cover = self.get(series='cuisine', ids=ids, n=2, slide=1).get_data(as_text=True)
        self.assertIn('5 weeknights of Italian #2', cover)
        self.assertIn('Italian', self.get(series='cuisine', ids=ids, n=2).headers['X-Hook-Text'])
        self.assertIn('Mon', self.get(series='cuisine', ids=ids, n=2, slide=2).get_data(as_text=True))

    # The slide kinds

    def test_the_delta_goes_on_a_slide_only_when_small_else_the_time_bar(self):
        self.assertTrue(social.delta_fits({'max_depth': 2, 'leaves': 2, 'nodes': [], 'edges': []}))
        self.assertFalse(social.delta_fits({'max_depth': 3, 'leaves': 2, 'nodes': [], 'edges': []}))
        self.assertFalse(social.delta_fits({'max_depth': 1, 'leaves': 3, 'nodes': [], 'edges': []}))
        self.assertFalse(social.delta_fits(None))
        view = {'delta': {'max_depth': 1, 'leaves': 2, 'edges': [['a', 'c'], ['b', 'c']], 'nodes': [
            {'id': 'a', 'depth': 1, 'span': [0, 1]}, {'id': 'b', 'depth': 1, 'span': [1, 2]},
            {'id': 'c', 'depth': 0, 'span': [0, 2]}]}, 'total': '30 min'}
        slide = social.delta_slide(view)
        self.assertEqual((slide['cols'], slide['rows']), (2, 2))
        self.assertEqual([(c['row'], c['col'], c['flows']) for c in slide['cells']],
                         [(1, (1, 2), True), (1, (2, 3), True), (2, (1, 3), False)])
        recipe = db.session.get(Recipe, self.ids[0])
        kinds = self.kinds(series='dishes', ids=recipe.id)
        self.assertEqual(kinds[3], 'delta' if social.delta_fits(page(recipe)['delta']) else 'timebar')

    def test_the_time_bar_the_numbers_the_timers_and_the_wash(self):
        view = page(db.session.get(Recipe, self.ids[0]))
        bar = social.timebar_slide(view, 'oven')
        self.assertEqual(bar['active'] + bar['idle'], view['total_min'])
        self.assertEqual(bar['other'], f"{bar['idle']} min the oven")
        self.assertEqual(social.timebar_slide(view, None)['other'], f"{bar['idle']} min hands off")
        numbers = social.numbers_slide(view)
        self.assertEqual([(i['value'], i['unit']) for i in numbers['items']], [(40, 'g'), (500, ''), (view['total_min'], 'min')])
        timers = social.timers_slide(view)
        self.assertLessEqual(len(timers['steps']), social.TIMER_STEPS + 1)
        self.assertEqual(len(timers['steps']) + timers['more'], len(view['steps']))
        wash = social.wash_slide(view, {'frying_pan': 'pan.webp'})
        self.assertEqual([e['name'] for e in wash['items']], ['Large pot', 'Bowl', 'Frying pan', 'Colander'])
        self.assertEqual(wash['title'], 'Dishes to wash: 4')
        self.assertEqual(wash['items'][2]['img'], 'pan.webp')
        split = social.shop_split_slide(view, 'ig')
        self.assertTrue(split['tiles'] and split['have'])
        self.assertNotIn('Salt', [t['name'] for t in split['tiles']])

    def test_the_air_fryer_slide_reads_the_heat_steps_when_no_step_names_it(self):
        view = page(db.session.get(Recipe, self.ids[0]))
        slide = social.airfryer_slide(view, {'airfryer': 'af.webp'})
        self.assertEqual(slide['img'], 'af.webp')
        self.assertGreater(slide['minutes'], 0)

    # Picking

    def test_a_recipe_goes_at_most_once_a_week_per_series_never_used_first(self):
        today = datetime.date(2026, 11, 2)
        self.assertEqual(series.candidates('airfryer').keys(), set(self.ids))
        for rid in self.ids[1:]:
            db.session.get(Recipe, rid).heat_source = 'oven'
        db.session.commit()
        self.assertEqual(series.pick('airfryer', today), [self.ids[0]])
        db.session.add(SocialPost(platform='tiktok', code='1', format='series', title='x', series='airfryer',
                                  series_n=4, recipe_ids=str(self.ids[0]), posted_on=today - datetime.timedelta(days=2)))
        db.session.commit()
        self.assertEqual(series.pick('airfryer', today), [])  # used this week, and nothing else in the air fryer
        self.assertEqual(series.next_n('airfryer'), 5)
        self.assertEqual(series.next_n('got'), 1)
        self.assertEqual(series.pick('airfryer', today + datetime.timedelta(days=6)), [self.ids[0]])
        # Lighter dinners first in High-protein; a logged one goes after the never used
        for rid in (self.ids[0], self.ids[3], self.ids[4]):
            db.session.get(Recipe, rid).total_calories = 2400
        db.session.get(Recipe, self.ids[1]).total_calories = 1200
        db.session.add(SocialPost(platform='instagram', code='2', format='series', title='x', series='protein',
                                  recipe_id=self.ids[1], posted_on=today - datetime.timedelta(days=30)))
        db.session.commit()
        self.assertEqual(series.pick('protein', today), [self.ids[2]])
        db.session.get(Recipe, self.ids[2]).total_protein = 100  # 25 g: not high-protein
        db.session.commit()
        self.assertNotIn(self.ids[2], series.candidates('protein'))

    def test_got_and_the_cuisine_week_pick_a_group_with_enough_dinners(self):
        today = datetime.date(2026, 11, 2)
        self.assertEqual(len(series.pick('got', today)), 3)
        for rid in self.ids[:3]:
            db.session.get(Recipe, rid).protein_type = 'Chicken'
        db.session.get(Recipe, self.ids[3]).protein_type = 'Vegetarian'
        db.session.commit()
        self.assertEqual(series.pick('got', today), self.ids[:3])  # beef has one dinner left, vegetarian is no ingredient
        self.assertEqual(len(series.pick('cuisine', today)), 5)
        db.session.get(Recipe, self.ids[0]).cuisine = 'Thai'
        db.session.commit()
        self.assertEqual(series.pick('cuisine', today), [])
        self.assertEqual(self.get(series='cuisine').status_code, 404)  # the series has run out: it pauses

    def test_a_post_without_recipes_picks_them_and_says_which(self):
        r = self.get(series='dishes')
        self.assertEqual(r.status_code, 200)
        self.assertEqual((r.headers['X-Recipes'], r.headers['X-N']), (str(self.ids[0]), '1'))


if __name__ == '__main__':
    unittest.main()
