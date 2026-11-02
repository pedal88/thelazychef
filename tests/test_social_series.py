"""The post series (services/social_series.py, the cards in data/social/series, /social/post): the cards are checked,
each series renders in both sizes with its slide sequence, the hooks state the post's own numbers and come out the
same every time, time is said only when short, bad values fall back, the address stays on the last slide, and the
picking keeps a recipe out of a series for a week."""
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
from database.models import Recipe, RecipeMealType, SocialPost, User, db  # noqa: E402
from routes._shared import SITE_LOOK  # noqa: E402
from services import social, social_series as series, social_week  # noqa: E402
from services.recipe_v2.generate import refresh  # noqa: E402
from services.recipe_v2.store import save_v2  # noqa: E402
from services.recipe_v2.view import page  # noqa: E402

FIXTURES = ('carbonara', 'lasagne', 'tikka', 'brownies', 'burger')


def view_of(active, standing, title='Gyros', heat='airfryer'):
    """A view as the hooks and slides read one: a prep step of active minutes and a cook step standing in the heat
    source (equipment id heat), two minutes of work at it."""
    steps = [{'n': 1, 'short': 'Cut', 'duration': '', 'phase': 'prep', 'equipment_ids': [], 'passive_min': 0,
              'temp_c': None, 'minutes': active, 'heat': False},
             {'n': 2, 'short': 'Cook', 'duration': '', 'phase': 'cook', 'equipment_ids': [heat],
              'passive_min': standing, 'temp_c': 200, 'minutes': standing + 2, 'heat': True}]
    return {'title': title, 'total_min': active + standing + 2, 'active_min': active + 2, 'steps': steps,
            'equipment': [], 'nutrition': None, 'shop_groups': [], 'units': 'metric', 'parts': [], 'delta': None}


def post_of(view, heat_source='airfryer', rid=1):
    return {'id': rid, 'view': view, 'heat_source': heat_source, 'image': None, 'eq': {}, 'protein': 'Chicken',
            'cuisine': 'Greek'}


class CardTests(unittest.TestCase):
    def test_the_cards_in_the_repo_pass_the_check(self):
        self.assertEqual(series.check_cards(), [])
        self.assertEqual(sorted(series.SERIES), ['airfryer', 'cuisine', 'dishes', 'got', 'guess', 'protein'])
        for slug, card in series.SERIES.items():
            with self.subTest(series=slug):
                self.assertIn(card['status'], series.STATUSES)
                self.assertTrue(card['hook'] in series.HOOKS)
                self.assertEqual(card['slides'][-1], 'end')

    def test_the_check_fails_a_hook_too_long_a_fact_no_post_has_and_a_slide_kind_that_is_not_one(self):
        good = series.SERIES['airfryer']
        bad = {**good, 'status': 'maybe', 'slides': ['cover', 'carousel', 'end'],
               'hooks': {'lazy': [('A hook that goes on for more than eight words. {active} min.', ('active',)),
                         ('{active} min, {wait} min standing.', ('active', 'wait')),
                         ('{active} min and {total} min.', ('active',))],
                         'shout': [('Dinner!', ())]},
               'retired_hooks': [{'text': 'old', 'why': ''}], 'purpose': ''}
        problems = '\n'.join(series.check_cards({'x': bad}))
        for text in ('is 12 words, over 8', 'needs wait, which no post has', 'uses total without needing it',
                     "slide kind 'carousel' is not one", 'status must be one of', "hook group 'shout' is not in",
                     'retired hook "old" has no why', 'purpose is empty'):
            with self.subTest(text=text):
                self.assertIn(text, problems)
        self.assertEqual(series.check_cards({'ok': good}), [])

    def test_every_fact_a_phrasing_may_need_is_one_the_post_makes(self):
        f = series.facts([post_of(view_of(7, 15))], 3, series='Air fryer dinners')
        self.assertEqual(set(f), set(series.FACTS))
        self.assertEqual(set(series.sample_facts()), set(series.FACTS))


class SeriesTests(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        self.ctx = app.app_context()
        self.ctx.push()
        db.drop_all()
        db.create_all()
        admin = User(email='admin@test', is_admin=True)
        admin.set_password('pw')
        db.session.add(admin)
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
            if 'Dinner' not in recipe.meal_types_list:  # what refresh() derived; the series take dinners only
                db.session.add(RecipeMealType(recipe_id=recipe.id, meal_type='Dinner'))
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

    def test_every_series_renders_in_both_sizes_with_its_cards_slides(self):
        one, three, five = str(self.ids[0]), ','.join(map(str, self.ids[:3])), ','.join(map(str, self.ids))

        def shops(ids):  # one list for several dinners takes as many slides as SHOP_PER_SLIDE allows
            views = [page(db.session.get(Recipe, i)) for i in ids]
            shop, _ = social_week.shopping(social_week.days_of(views, [None] * len(views)), views)
            return ['shop'] * -(-len(shop) // social.SHOP_PER_SLIDE)
        self.assertEqual(len(shops(self.ids)), 3)  # the five fixtures need 52 things: three slides
        expected = {
            'airfryer': (one, ['cover', 'airfryer', 'timebar', 'timers', 'shop_split', 'end']),
            'got': (three, ['got_cover', 'day', 'day', 'day', *shops(self.ids[:3]), 'end']),
            'protein': (one, ['cover', 'numbers', 'timebar', 'timers', 'shop_split', 'end']),
            'dishes': (one, ['cover', 'wash', 'ingredients', 'timebar', 'timers', 'end']),
            'guess': (one, ['collage', 'ingredients', 'dish', 'end']),
            'cuisine': (five, ['week_cover', 'day', 'day', 'day', 'day', 'day', *shops(self.ids), 'end']),
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
        r = self.get(series='airfryer', ids=self.ids[0], n=7, hook='guess', cta='save', code=9, size='tt')
        self.assertEqual((r.headers['X-Recipes'], r.headers['X-N'], r.headers['X-Hook'], r.headers['X-Cta']),
                         (str(self.ids[0]), '7', 'guess', 'save'))
        self.assertEqual(r.headers['X-Views'], 'cover airfryer timebar timers shop_split end')
        self.assertEqual(r.headers['X-Look'], SITE_LOOK)
        self.assertEqual(r.headers['X-Robots-Tag'], 'noindex')
        caption = self.get(series='airfryer', ids=self.ids[0], n=7, cta='save', code=9, size='tt', caption=1)
        text = caption.get_data(as_text=True)
        self.assertIn('thelazychef.app/tiktok/9', text)
        self.assertIn('#airfryer', text)
        self.assertIn('Save', text)

    def test_the_hook_states_the_posts_own_numbers_and_stays_the_same(self):
        texts = set()
        for _ in range(3):
            texts.add(self.get(series='airfryer', ids=self.ids[0], n=2).headers['X-Hook-Text'])
        self.assertEqual(texts, {'Air fryer #2: Spaghetti carbonara'})  # the card's default: the series and the dish
        self.assertIn('Air fryer #2: Spaghetti carbonara',
                      self.get(series='airfryer', ids=self.ids[0], n=2, slide=1).get_data(as_text=True))
        number = self.get(series='protein', ids=self.ids[0], n=2, hook='number').headers['X-Hook-Text']
        self.assertIn('40', number)  # 160 g over 4 servings
        self.assertLessEqual(len(number.split()), series.HOOK_WORDS)
        self.assertIn(self.get(series='dishes', ids=self.ids[0], n=1).headers['X-Hook-Text'],
                      ('Dishes to wash: 4', '4 dishes to wash. 16 min of work.', 'One dinner, 4 dishes to wash.'))

    def test_time_is_said_only_when_short(self):
        self.assertEqual([social.said_active(m) for m in (9, 19, 20, 38)], [9, 19, None, None])
        self.assertEqual([social.said_total(m) for m in (19, 30, 31, 90)], [19, 30, None, None])
        quick = series.facts([post_of(view_of(6, 12))], 1)  # 8 min of work, 20 in all
        self.assertEqual((quick['active'], quick['total'], quick['fastest'], quick['idle'], quick['stress_active'],
                          quick['stress_total']), (8, 20, 20, 12, True, False))
        slow = series.facts([post_of(view_of(36, 11))], 1)  # 38 min of work, 49 in all
        self.assertEqual((slow['active'], slow['total'], slow['fastest'], slow['idle'], slow['stress_active']),
                         (None, None, None, None, False))
        for seed in 'abcdef':  # no phrasing with a time is drawn for the slow one, in any group
            for group in series.HOOKS:
                text = series.hook(group, slow, seed) or ''
                self.assertNotIn('min', text, (group, text))
        # Nor the cover chip, the day label, the numbers slide, the timers' title or the caption
        v = view_of(36, 11)
        self.assertEqual(social_week.days_of([v], [None], ['Mon'])[0]['total'], None)
        self.assertEqual(social_week.days_of([view_of(6, 12)], [None], ['Mon'])[0]['total'], '20 min')
        self.assertEqual([i['label'] for i in social.numbers_slide(v)['items']], ['things to buy', 'dishes to wash'])
        self.assertEqual([i['label'] for i in social.numbers_slide(view_of(6, 12))['items']], ['start to table', 'of work'])
        self.assertEqual(social.timers_slide(v)['title'], '2 steps')
        self.assertEqual(social.timers_slide(view_of(6, 12))['title'], '2 steps, 20 min')
        call = {'group': 'follow', 'text': 'Follow'}
        self.assertNotIn('minute', series.caption('airfryer', [post_of(v)], slow, 'x', call, 'ig'))
        self.assertIn('8 minutes of work', series.caption('airfryer', [post_of(view_of(6, 12))], quick, 'x', call, 'ig'))
        long = self.get(series='airfryer', ids=self.ids[0], n=1, slide=1).get_data(as_text=True)  # 26 min: said
        self.assertIn('<span>26 min</span>', long)
        db.session.get(Recipe, self.ids[0]).title = 'x'  # a change, so the view is built again
        db.session.commit()

    def test_the_air_fryer_hooks_name_the_dish_and_the_machines_time_only_when_short(self):
        f = series.facts([post_of(view_of(36, 11))], 3, series='Air fryer dinners')
        self.assertEqual((f['machine'], f['machine_min'], f['temp'], f['dish']), (True, 11, '200 °C', 'Gyros'))
        self.assertEqual(series.hook('series', f, 'a', 'airfryer'), 'Air fryer #3: Gyros')
        self.assertIn(series.hook('lazy', f, 'a', 'airfryer'), ('200 °C. 11 minutes.', '11 minutes in the air fryer.'))
        self.assertEqual(series.hook_for(None, f, 'a', 'airfryer'), ('series', 'Air fryer #3: Gyros'))
        slow_machine = series.facts([post_of(view_of(7, 25))], 3, series='Air fryer dinners')
        self.assertEqual((slow_machine['active'], slow_machine['machine_min']), (9, None))
        self.assertIsNone(series.hook('lazy', slow_machine, 'a', 'airfryer'))  # 25 minutes in the machine: not said
        self.assertEqual(series.hook_for('lazy', slow_machine, 'a', 'airfryer'), ('series', 'Air fryer #3: Gyros'))
        # The dish in a few words, and a hook over eight words is never drawn
        self.assertEqual(series.short_title('Chicken Gyros Plate with Tzatziki and Greek Salad'), 'Chicken Gyros Plate')
        self.assertEqual(series.short_title('Air Fryer Salmon Bites with Gochujang Mayo'), 'Salmon Bites')
        self.assertEqual(series.short_title('Kjøttkaker in Brown Sauce, with potatoes'), 'Kjøttkaker')
        long = series.facts([post_of(view_of(36, 11, title='One Two Three Four Five Six Seven Eight'))], 3, series='Air fryer dinners')
        self.assertIsNone(series.hook('series', long, 'a', 'airfryer'))
        for row in series.SERIES['airfryer']['retired_hooks']:
            self.assertTrue(row['why'])
            self.assertIn('{active}', row['text'])

    def test_a_hook_over_several_dinners_names_only_the_fastest_and_only_when_short(self):
        posts = [post_of(view_of(a, b), rid=i) for i, (a, b) in enumerate(((150, 5), (50, 8), (20, 3)))]
        f = series.facts(posts, 3, count=20, ingredient='chicken')
        self.assertEqual((f['total'], f['active'], f['idle'], f['fastest'], f['machine_min']), (None, None, None, 25, None))
        for seed in 'abcdef':
            text = series.hook('search', f, seed)
            self.assertNotIn('157', text)
            self.assertNotIn('60', text)
            self.assertNotIn('minutes', text.replace('25 minutes', ''))
        slow = series.facts(posts[:2], 3, count=20, ingredient='chicken')
        self.assertIsNone(slow['fastest'])
        for seed in 'abcdef':
            self.assertNotIn('minutes', series.hook('search', slow, seed))
            self.assertIsNone(series.hook('contrast', slow, seed))
        self.assertNotIn('minutes', ' '.join(series.hook('number', slow, s) for s in 'abcdef'))

    def test_slides_say_hours_and_minutes_and_a_long_list_goes_over_more_slides(self):
        self.assertEqual([social.clock(m) for m in (45, 119, 120, 157, 180)],
                         ['45 min', '119 min', '2 h', '2 h 37 min', '3 h'])
        tiles = [{'name': f't{i}', 'amount': None, 'img': None, 'key': f'k{i}', 'times': 1} for i in range(52)]
        pages = social.shop_slides(tiles, ['salt'], 'ig')
        self.assertEqual([len(p['tiles']) for p in pages], [18, 17, 17])
        self.assertTrue(all(len(p['tiles']) <= social.SHOP_PER_SLIDE for p in pages))
        self.assertEqual([p['title'] for p in pages], ['The shopping list, 1 of 3', 'The shopping list, 2 of 3',
                                                       'The shopping list, 3 of 3'])
        self.assertEqual([p['staples'] for p in pages], [[], [], ['salt']])
        self.assertEqual([t['name'] for p in pages for t in p['tiles']], [t['name'] for t in tiles])
        self.assertEqual([len(p['tiles']) for p in social.shop_slides(tiles[:40], [], 'ig')], [20, 20])
        [one] = social.shop_slides(tiles[:24], ['salt'], 'ig', 'One list for all 3')
        self.assertEqual((one['title'], len(one['tiles']), one['staples']), ('One list for all 3', 24, ['salt']))

    def test_a_group_the_post_cannot_say_truly_falls_back(self):
        facts = {**series.sample_facts(), 'count': 25, 'total': None, 'vessels': 5, 'few': False, 'one_two': False}
        self.assertIsNone(series.hook('contrast', facts, 'x'))
        group, text = series.hook_for('contrast', facts, 'x', 'dishes')
        self.assertEqual((group, '5' in text), ('number', True))  # the series' own group, with its own numbers
        self.assertEqual(series.hook_for('contrast', facts, 'x')[0], 'number')
        self.assertEqual(series.hook_for('contrast', {**facts, 'count': 6, 'few': True}, 'x', 'dishes'),
                         ('contrast', 'Not 30 ingredients. Just 6.'))

    def test_bad_hook_cta_series_or_recipes_fall_back_or_are_not_found(self):
        r = self.get(series='airfryer', ids=self.ids[0], hook='shout', cta='buy')
        self.assertEqual((r.headers['X-Hook'], r.headers['X-Cta']), ('series', 'follow'))
        self.assertEqual(self.get(series='soup', ids=self.ids[0]).status_code, 404)
        self.assertEqual(self.get(series='got', ids=self.ids[0]).status_code, 404)  # got takes three
        self.assertEqual(self.get(series='airfryer', ids='a').status_code, 404)
        self.assertEqual(self.get(series='airfryer', ids=999).status_code, 404)
        self.assertEqual(self.get(series='airfryer', ids=self.ids[0], slide=9).status_code, 404)
        db.session.get(Recipe, self.ids[0]).status = 'draft'
        db.session.commit()
        self.assertEqual(self.get(series='airfryer', ids=self.ids[0]).status_code, 404)

    def test_an_admin_may_try_words_that_are_on_no_card_and_nobody_else_can(self):
        args = {'series': 'airfryer', 'ids': self.ids[0], 'n': 1, 'hook_text': 'Try these words', 'cta_text': 'Tap it'}
        public = self.get(**args)
        self.assertEqual((public.headers['X-Hook'], public.headers['X-Cta']), ('series', 'follow'))
        self.assertNotIn('Try these words', self.get(**args, slide=1).get_data(as_text=True))
        self.client.post('/login', data={'email': 'admin@test', 'password': 'pw'})
        admin = self.get(**args)
        self.assertEqual((admin.headers['X-Hook'], admin.headers['X-Hook-Text'], admin.headers['X-Cta']),
                         ('preview', 'Try these words', 'preview'))
        self.assertIn('Try these words', self.get(**args, slide=1).get_data(as_text=True))
        last = self.get(**args, slide=6, code=3).get_data(as_text=True)
        self.assertIn('Tap it', last)
        self.assertIn('class="address small">thelazychef.app/ig/3', last)

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

    def test_what_to_make_with_asks_for_the_shared_ingredient_and_lists_the_rest_per_dinner(self):
        ids = ','.join(map(str, self.ids[:3]))
        cover = self.get(series='got', ids=ids, n=1, slide=1).get_data(as_text=True)
        self.assertIn('What to make with beef #1', cover)
        self.assertIn('What to make with beef: 3 dinners', cover)  # the first phrasing of the card: the default
        shop = self.get(series='got', ids=ids, n=1, slide=5).get_data(as_text=True)
        self.assertIn('One list for all 3, 1 of 2', shop)

    def test_the_cuisine_week_is_five_weeknights_and_one_list(self):
        ids = ','.join(map(str, self.ids))
        cover = self.get(series='cuisine', ids=ids, n=2, slide=1).get_data(as_text=True)
        self.assertIn('5 weeknights of Italian #2', cover)
        self.assertNotIn('min each', cover)  # the slowest is over 30 minutes: no minutes on the cover
        self.assertIn('Italian', self.get(series='cuisine', ids=ids, n=2).headers['X-Hook-Text'])
        self.assertIn('Mon', self.get(series='cuisine', ids=ids, n=2, slide=2).get_data(as_text=True))

    def test_the_caption_counts_its_dishes_in_good_english(self):
        f = {**series.sample_facts(), 'vessels': 1, 'active': 8, 'total': None}
        call = {'group': 'send', 'text': 'Send it'}
        text = series.caption('dishes', [post_of(view_of(6, 12, title='Shakshuka'))], f, 'x', call, 'ig', 5)
        self.assertIn('Shakshuka, with 1 dish to wash, 8 minutes of work.', text)
        self.assertIn('thelazychef.app/ig/5', text)
        text = series.caption('dishes', [post_of(view_of(6, 12))], {**f, 'vessels': 2, 'active': None}, 'x', call, 'ig')
        self.assertIn('with 2 dishes to wash.', text)

    # The slide kinds

    def test_the_delta_goes_on_a_slide_only_when_small_else_the_time_bar(self):
        self.assertTrue(social.delta_fits({'max_depth': 2, 'leaves': 2, 'nodes': [], 'edges': []}))
        self.assertFalse(social.delta_fits({'max_depth': 3, 'leaves': 2, 'nodes': [], 'edges': []}))
        self.assertFalse(social.delta_fits({'max_depth': 1, 'leaves': 3, 'nodes': [], 'edges': []}))
        self.assertFalse(social.delta_fits(None))
        view = {'delta': {'max_depth': 1, 'leaves': 2, 'edges': [['a', 'c'], ['b', 'c']], 'nodes': [
            {'id': 'a', 'depth': 1, 'span': [0, 1]}, {'id': 'b', 'depth': 1, 'span': [1, 2]},
            {'id': 'c', 'depth': 0, 'span': [0, 2]}]}, 'total': '30 min', 'total_min': 30}
        slide = social.delta_slide(view)
        self.assertEqual((slide['cols'], slide['rows'], slide['total']), (2, 2, '30 min'))
        self.assertEqual([(c['row'], c['col'], c['flows']) for c in slide['cells']],
                         [(1, (1, 2), True), (1, (2, 3), True), (2, (1, 3), False)])
        self.assertIsNone(social.delta_slide({**view, 'total_min': 45})['total'])
        recipe = db.session.get(Recipe, self.ids[0])
        kinds = self.kinds(series='dishes', ids=recipe.id)
        self.assertEqual(kinds[3], 'delta' if social.delta_fits(page(recipe)['delta']) else 'timebar')

    def test_the_time_bar_the_numbers_the_timers_and_the_wash(self):
        view = page(db.session.get(Recipe, self.ids[0]))
        bar = social.timebar_slide(view, 'oven')  # nothing stands in an oven here: the rest is hands off
        self.assertEqual((bar['active'] + bar['idle'], bar['doer']), (view['total_min'], 'hands off'))
        self.assertEqual(bar['other'], f"{bar['idle']} min hands off")
        pot = social.timebar_slide(view, 'pot')  # the pasta water stands in the pot
        self.assertEqual((pot['idle'], pot['doer']), social.hands_off(view, 'pot'))
        self.assertEqual(pot['doer'], 'the pot' if social.machine_minutes(view, 'pot') else 'hands off')
        numbers = social.numbers_slide(view)
        self.assertEqual([(i['value'], i['unit']) for i in numbers['items']],
                         [(40, 'g'), (500, ''), (view['total_min'], 'min'), (view['active_min'], 'min')])  # 26 and 17: short
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

    def test_the_air_fryer_time_is_one_number_on_the_slide_the_bar_and_the_hook(self):
        v = view_of(36, 11)  # 38 min of work, 11 in the air fryer, 49 in all
        self.assertEqual(social.hands_off(v, 'airfryer'), (11, 'the air fryer'))
        self.assertEqual(social.airfryer_slide(v, {})['minutes'], 11)
        bar = social.timebar_slide(v, 'airfryer')
        self.assertEqual((bar['active'], bar['idle'], bar['other']), (38, 11, '11 min the air fryer'))
        f = series.facts([post_of(v)], 1)
        self.assertEqual((f['idle'], f['doer'], f['machine'], f['machine_min']), (None, 'the air fryer', True, 11))
        # Nothing stands in the air fryer: the time not working is hands off, and no machine time
        plain = view_of(10, 0)
        self.assertEqual(social.hands_off(plain, 'airfryer'), (0, 'hands off'))
        f = series.facts([post_of(plain)], 1)
        self.assertEqual((f['machine'], f['machine_min'], f['temp']), (False, None, None))

    def test_the_air_fryer_slide_reads_the_heat_steps_when_no_step_names_it(self):
        view = page(db.session.get(Recipe, self.ids[0]))
        slide = social.airfryer_slide(view, {'airfryer': 'af.webp'})
        self.assertEqual(slide['img'], 'af.webp')
        self.assertGreater(slide['minutes'], 0)

    # Picking

    def test_every_series_takes_dinners_only(self):
        breakfast = db.session.get(Recipe, self.ids[0])
        db.session.execute(db.delete(RecipeMealType).where(RecipeMealType.recipe_id == breakfast.id))
        db.session.add(RecipeMealType(recipe_id=breakfast.id, meal_type='Breakfast'))
        db.session.commit()
        for slug in series.SERIES:
            with self.subTest(series=slug):
                self.assertNotIn(breakfast.id, series.candidates(slug))
                self.assertIn(self.ids[1], series.candidates(slug))

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
