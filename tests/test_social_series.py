"""The post series (services/social_series.py, the cards in data/social/series, /social/post): the cards are checked,
each series renders in both sizes with its slide sequence, the hooks state the post's own numbers and come out the
same every time, time is said only when short, bad values fall back, the address stays on the last slide, and the
picking keeps a recipe out of a series for a week."""
import datetime
import json
import os
import re
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
from services import social, social_publish, social_series as series, social_week  # noqa: E402
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
        self.assertEqual(sorted(series.SERIES), ['airfryer', 'cuisine', 'got', 'guess', 'onepot', 'only6', 'protein',
                                                 'protein4', 'three3', 'under20', 'whole'])
        self.assertEqual(series.active(), ['cuisine', 'got', 'guess', 'onepot', 'protein', 'protein4', 'under20', 'whole'])
        self.assertEqual(sorted(set(series.SERIES) - set(series.active())), ['airfryer', 'only6', 'three3'])
        for slug, card in series.SERIES.items():
            with self.subTest(series=slug):
                self.assertIn(card['status'], series.STATUSES)
                self.assertTrue(card['hook'] in series.HOOKS)
                self.assertIn(card['slides'][-1], ('end', 'answer'))

    def test_the_check_fails_a_hook_too_long_a_fact_no_post_has_and_a_slide_kind_that_is_not_one(self):
        good = series.SERIES['airfryer']
        bad = {**good, 'status': 'maybe', 'slides': ['cover', 'carousel', 'timebar', 'end'], 'filter': 'soup',
               'hooks': {'lazy': [('A hook that goes on for more than eight words. {active} min.', ('active',)),
                         ('{active} min, {wait} min standing.', ('active', 'wait')),
                         ('{active} min and {total} min.', ('active',))],
                         'shout': [('Dinner!', ())]},
               'retired_hooks': [{'text': 'old', 'why': ''}], 'purpose': ''}
        problems = '\n'.join(series.check_cards({'x': bad}))
        for text in ('is 12 words, over 8', 'needs wait, which no post has', 'uses total without needing it',
                     "slide kind 'carousel' is not one", "slide kind 'timebar' is not one", 'status must be one of',
                     "hook group 'shout' is not in", 'retired hook "old" has no why', 'purpose is empty',
                     'pick.filter must be one of'):
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
        one, three, four = str(self.ids[0]), ','.join(map(str, self.ids[:3])), ','.join(map(str, self.ids[:4]))

        def shops(ids):  # one list for several dinners takes as many slides as SHOP_PER_SLIDE allows
            views = [page(db.session.get(Recipe, i)) for i in ids]
            shop, _ = social_week.shopping(social_week.days_of(views, [None] * len(views)), views)
            return ['shop'] * -(-len(shop) // social.SHOP_PER_SLIDE)

        def steps(rid, size):  # the steps go over slides of at most COOK_STEPS each
            return ['cook'] * len(social.steps_slides(page(db.session.get(Recipe, rid)), size))
        delta = ['delta'] if social.delta_fits(page(db.session.get(Recipe, self.ids[0]))['delta']) else []
        expected = {
            'airfryer': (one, lambda size: ['cover', 'airfryer', *delta, *steps(self.ids[0], size), 'shop_split', 'end']),
            'got': (three, lambda size: ['got_cover', 'day', 'day', 'day', *shops(self.ids[:3]), 'end']),
            'three3': (three, lambda size: ['trio_cover', 'day', 'day', 'day', *shops(self.ids[:3]), 'end']),
            'protein': (one, lambda size: ['cover', 'numbers', *steps(self.ids[0], size), 'shop_split', 'end']),
            'protein4': (four, lambda size: ['week_cover', 'day', 'day', 'day', 'day', *shops(self.ids[:4]), 'end']),
            'onepot': (one, lambda size: ['cover', *delta, *steps(self.ids[0], size), 'shop_split', 'end']),  # no wash slide
            'under20': (one, lambda size: ['cover', *steps(self.ids[0], size), 'shop_split', 'end']),
            'only6': (one, lambda size: ['cover', 'shop_split', *steps(self.ids[0], size), 'end']),
            'guess': (one, lambda size: ['guess_pictures', 'guess_names', 'guess_amounts', 'guess_dish', 'answer']),
            'cuisine': (four, lambda size: ['week_cover', 'day', 'day', 'day', 'day', *shops(self.ids[:4]), 'end']),
            'whole': (one, lambda size: ['cover', 'shop_split', *['step'] * 9, 'end']),  # carbonara: 9 steps
        }
        self.assertEqual(sorted(expected), sorted(series.SERIES))
        for slug, (ids, kinds) in expected.items():
            for size in ('ig', 'tt'):
                with self.subTest(series=slug, size=size):
                    self.assertEqual(self.kinds(size, series=slug, ids=ids, n=3), kinds(size))
                    html = self.get(size=size, series=slug, ids=ids, n=3, slide=1).get_data(as_text=True)
                    self.assertIn('#3', html)  # the series' number on the first slide
                    self.assertIn(f'width:1080px; height:{social.SIZES[size][1]}px', html)
                    self.assertNotIn('kind-timebar', html)

    def test_the_css_for_a_size_and_a_kind_can_match_the_slide(self):
        # Both classes are on the slide's <main>: with a space between them the rule never applies, and the game's
        # symbols stay too large for game_columns' estimate and run into the foot
        with open(os.path.join(os.path.dirname(__file__), '..', 'static', 'css', 'social.css'), encoding='utf-8') as f:
            self.assertIsNone(re.search(r'\.size-(ig|tt) \.kind-', f.read()))

    def test_the_games_pictures_fill_their_rows_and_a_cover_strip_has_no_orphan(self):
        self.assertEqual([social.game_columns(n, 'tt') for n in (5, 8, 12, 15, 13, 14)], [5, 4, 4, 5, 5, 5])
        self.assertEqual([social.game_columns(n, 'ig') for n in (5, 8, 12, 15, 13, 14)], [5, 4, 4, 5, 5, 5])
        # The symbols as large as the rows leave room for: all of the cell on two rows, less on three
        self.assertEqual([social.game_symbol(n, 'ig') for n in (5, 10, 12, 15, 16)], [100, 100, 74, 93, 100])
        self.assertEqual([social.game_symbol(n, 'tt') for n in (5, 10, 12, 15, 16)], [100, 100, 83, 100, 100])
        self.assertEqual([social.strip_columns(n) for n in (3, 6, 7, 8, 11, 12)], [3, 6, 4, 4, 6, 6])
        # A hook that names the dish leaves no name line under it
        pot = self.get(series='onepot', ids=self.ids[0], n=1, hook_text='One pot. Spaghetti carbonara.', slide=1)
        self.client.post('/login', data={'email': 'admin@test', 'password': 'pw'})
        pot = self.get(series='onepot', ids=self.ids[0], n=1, hook_text='One pot. Spaghetti carbonara.', slide=1).get_data(as_text=True)
        self.assertNotIn('class="dish">', pot)
        # A dish over 30 minutes whose hook names it: no name line, and no chip at all (no "None", no "N ingredients")
        slow = db.session.get(Recipe, self.ids[1])  # lasagne, 105 min
        html = self.get(series='onepot', ids=slow.id, n=1, hook_text='One pot. Lasagne.', slide=1).get_data(as_text=True)
        body = html.split('<main', 1)[1]
        self.assertNotIn('class="dish">', body)
        self.assertNotIn('class="facts"', body)
        self.assertNotIn('None', body)
        self.assertNotIn('ingredients', body)
        quick = self.get(series='onepot', ids=self.ids[0], n=1, hook_text='One pot. Spaghetti carbonara.', slide=1).get_data(as_text=True)
        self.assertIn('<p class="facts"><span>26 min</span></p>', quick)  # 26 minutes: the time chip alone
        plain = self.get(series='onepot', ids=self.ids[0], n=1, hook_text='Dishes to wash: one.', slide=1).get_data(as_text=True)
        self.assertIn('class="dish">Spaghetti carbonara', plain)
        self.assertNotIn('class="strip"', plain)  # the test pantry has no symbol images: no strip at all

    def test_the_steps_go_over_slides_as_on_the_cook_view_with_each_steps_symbols(self):
        view = page(db.session.get(Recipe, self.ids[0]))  # carbonara: 9 steps
        slides = social.steps_slides(view, 'ig')
        self.assertEqual([len(sl['steps']) for sl in slides], [3, 3, 3])
        self.assertEqual([sl['eyebrow'] for sl in slides], ['Step 1 to 3 of 9', 'Step 4 to 6 of 9', 'Step 7 to 9 of 9'])
        self.assertEqual([len(sl['steps']) for sl in social.steps_slides(view, 'tt')], [3, 3, 3])
        self.assertEqual([len(sl['steps']) for sl in social.steps_slides({**view, 'steps': view['steps'][:7]}, 'tt')],
                         [3, 2, 2])
        # Steps full of symbols would run into the foot: fewer on a slide, none lost, in order
        full = {f'l{i}': {'name': 'Salt', 'img': None, 'amount': '1 g'} for i in range(8)}
        heavy = {**view, 'pictured': full,
                 'steps': [{**s, 'uses': list(full)} for s in view['steps'][:3]]}
        for size in ('ig', 'tt'):
            spread = social.steps_slides(heavy, size)
            self.assertEqual([[st['no'] for st in sl['steps']] for sl in spread], [[1, 2], [3]])
            self.assertEqual([sl['pages'] for sl in spread], [2, 2])
            self.assertEqual(spread[0]['eyebrow'], 'Step 1 to 2 of 3')
        first = slides[0]['steps'][0]
        self.assertEqual(set(first), {'no', 'short', 'phase', 'symbols'})  # no minutes, no timer
        with_symbols = [st for sl in slides for st in sl['steps'] if st['symbols']]
        self.assertTrue(with_symbols)
        self.assertEqual(set(with_symbols[0]['symbols'][0]), {'name', 'img', 'amount'})
        html = self.get(series='under20', ids=self.ids[0], n=1, slide=2).get_data(as_text=True)
        self.assertIn('class="cook"', html)
        self.assertIn('Step 1 to 3 of 9', html)
        self.assertNotIn(' min', html.split('<main', 1)[1].split('<footer', 1)[0])

    def test_the_last_slide_of_a_series_is_the_dish_with_the_cta_as_a_button(self):
        count = int(self.get(series='protein', ids=self.ids[0], n=1).headers['X-Slides'])
        html = self.get(series='protein', ids=self.ids[0], n=1, code=4, slide=count).get_data(as_text=True)
        self.assertIn('class="photo n1"', html)
        self.assertIn('/static/recipes/carbonara.png', html)
        self.assertIn('class="end over"', html)
        self.assertIn('thelazychef.app/ig/4', html)
        self.assertIn('The Lazy Chef', html)
        self.assertNotIn('class="brand-seal', html)  # the dish fills the slide: only the small wordmark
        ids = ','.join(map(str, self.ids[:4]))
        count = int(self.get(series='protein4', ids=ids, n=1).headers['X-Slides'])
        html = self.get(series='protein4', ids=ids, n=1, slide=count).get_data(as_text=True)
        self.assertIn('class="photo n4"', html)
        self.assertEqual(html.count('<img src="/static/recipes/'), 4)
        # The formats keep their last slide as it was
        last = self.client.get(f'/social/recipe/{self.ids[0]}/grid', query_string={'slide': 4}).get_data(as_text=True)
        self.assertIn('class="brand-seal', last)

    def test_the_answer_says_what_the_post_was_made_of(self):
        r = self.get(series='airfryer', ids=self.ids[0], n=7, hook='guess', cta='save', code=9, size='tt')
        self.assertEqual((r.headers['X-Recipes'], r.headers['X-N'], r.headers['X-Hook'], r.headers['X-Cta']),
                         (str(self.ids[0]), '7', 'guess', 'save'))
        self.assertTrue(r.headers['X-Views'].startswith('cover airfryer '))
        self.assertTrue(r.headers['X-Views'].endswith(' shop_split end'))
        self.assertIn('cook', r.headers['X-Views'].split())
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
        # One Pot Meals names its vessel; carbonara cooks in a pot and a pan, so its card has nothing true to say and
        # the shared number group speaks instead
        pot = series.facts([post_of(view_of(6, 12, heat='frying_pan'))], 1, series='One Pot Meals')
        self.assertEqual(pot['vessel'], None)  # view_of names no equipment list; the fact needs the view's equipment
        pot = {**series.sample_facts(), 'vessel': 'frying pan', 'one_dish': False, 'dish': 'Shakshuka', 'active': 8}
        self.assertIn(series.hook_for(None, pot, 'a', 'onepot')[1],
                      ('One frying pan. Shakshuka.', 'Shakshuka, in one frying pan.', 'One frying pan, 8 min of work.'))
        self.assertNotIn('Dishes to wash: 1', [series.hook('number', pot, s, 'onepot') for s in 'abcdefgh'])
        self.assertIn('Dishes to wash: 1', [series.hook('number', {**pot, 'one_dish': True}, s, 'onepot') for s in 'abcdefghijkl'])
        self.assertEqual(self.get(series='onepot', ids=self.ids[0], n=1).headers['X-Hook'], 'number')

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
        # Nor the cover chip, the numbers slide or the caption; a day's label never has minutes
        v = view_of(36, 11)
        self.assertNotIn('total', social_week.days_of([view_of(6, 12)], [None], ['Mon'])[0])
        self.assertNotIn(' min', self.get(series='protein4', ids=','.join(map(str, self.ids[:4])), n=1, slide=2)
                         .get_data(as_text=True).split('<main', 1)[1].split('class="grid"', 1)[0])
        for quick_or_slow in (v, view_of(6, 12)):  # the big numbers never show minutes now
            self.assertEqual([i['label'] for i in social.numbers_slide(quick_or_slow)['items']], ['things to buy', 'dishes to wash'])
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
        self.assertEqual(series.short_title('Beef and Broccoli Stir Fry with Steamed Rice'), 'Beef and Broccoli Stir Fry')
        self.assertEqual(series.short_title('Sweet and Sour Chicken with Jasmine Rice'), 'Sweet and Sour Chicken')
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
        group, text = series.hook_for('contrast', facts, 'x', 'onepot')
        self.assertEqual((group, 'frying pan' in text), ('number', True))  # the series' own group, its own facts
        self.assertEqual(series.hook_for('contrast', facts, 'x')[0], 'number')
        self.assertEqual(series.hook_for('contrast', {**facts, 'count': 6, 'few': True}, 'x', 'onepot'),
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
        count = int(admin.headers['X-Slides'])
        last = self.get(**args, slide=count, code=3).get_data(as_text=True)
        self.assertIn('Tap it', last)
        self.assertIn('<b>thelazychef.app/ig/3</b>', last)

    def test_the_address_stays_on_the_last_slide_whatever_the_cta(self):
        count = int(self.get(series='airfryer', ids=self.ids[0]).headers['X-Slides'])
        for cta in ('follow', 'send', 'site'):
            with self.subTest(cta=cta):
                html = self.get(series='airfryer', ids=self.ids[0], cta=cta, code=4, size='tt', slide=count).get_data(as_text=True)
                self.assertIn('thelazychef.app/tiktok/4', html)  # in the button with site, under it otherwise
                self.assertEqual('<b>thelazychef.app/tiktok/4</b>' in html, cta != 'site')
                self.assertEqual('Type it in your browser' in html, cta != 'site')
        bio = self.get(series='airfryer', ids=self.ids[0], cta='bio', code=4, size='ig', slide=count)
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

    def test_the_cuisine_week_is_four_weeknights_and_one_list(self):
        ids = ','.join(map(str, self.ids[:4]))
        cover = self.get(series='cuisine', ids=ids, n=2, slide=1).get_data(as_text=True)
        self.assertIn('4 weeknights of Italian #2', cover)
        self.assertIn('class="dishes n4"', cover)
        self.assertNotIn('min each', cover)  # the slowest is over 30 minutes: no minutes on the cover
        self.assertIn('Italian', self.get(series='cuisine', ids=ids, n=2).headers['X-Hook-Text'])
        self.assertIn('Mon', self.get(series='cuisine', ids=ids, n=2, slide=2).get_data(as_text=True))
        self.assertIn('Thu', self.get(series='cuisine', ids=ids, n=2, slide=5).get_data(as_text=True))
        self.assertEqual(self.get(series='cuisine', ids=','.join(map(str, self.ids))).status_code, 404)  # five is not four
        four = self.get(series='protein4', ids=ids, n=1, slide=2).get_data(as_text=True)
        self.assertIn('Dinner 1 · 40 g protein', four)
        cover = self.get(series='protein4', ids=ids, n=1, slide=1).get_data(as_text=True)
        self.assertIn('40 g protein per serving', cover)
        self.assertNotIn('min each', cover)

    def test_the_caption_counts_its_dishes_in_good_english(self):
        f = {**series.sample_facts(), 'vessels': 1, 'active': 8, 'total': None}
        call = {'group': 'send', 'text': 'Send it'}
        text = series.caption('onepot', [post_of(view_of(6, 12, title='Shakshuka'))], f, 'x', call, 'ig', 5)
        self.assertIn('Shakshuka, cooked in one frying pan, with 1 dish to wash, 8 minutes of work.', text)
        self.assertIn('thelazychef.app/ig/5', text)
        text = series.caption('onepot', [post_of(view_of(6, 12))], {**f, 'vessels': 2, 'active': None, 'vessel': None}, 'x', call, 'ig')
        self.assertIn('Gyros, cooked, with 2 dishes to wash.', text)
        self.assertIn('one thing to buy', series.caption('only6', [post_of(view_of(6, 12))], {**f, 'count': 1}, 'x', call, 'ig').replace('1 thing', 'one thing'))

    # The slide kinds

    def test_the_delta_goes_on_a_slide_only_when_small_else_no_slide(self):
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
        for rid in self.ids:
            recipe = db.session.get(Recipe, rid)
            kinds = self.kinds(series='onepot', ids=recipe.id)
            self.assertEqual('delta' in kinds, social.delta_fits(page(recipe)['delta']))
            self.assertNotIn('timebar', kinds)

    def test_the_hands_off_time_the_numbers_and_the_wash(self):
        view = page(db.session.get(Recipe, self.ids[0]))
        self.assertEqual(social.hands_off(view, 'oven')[1], 'hands off')  # nothing stands in an oven here
        self.assertEqual(social.hands_off(view, 'pot')[1], 'the pot' if social.machine_minutes(view, 'pot') else 'hands off')
        numbers = social.numbers_slide(view)
        self.assertEqual([(i['value'], i['unit']) for i in numbers['items']], [(40, 'g'), (500, '')])  # no minutes
        wash = social.wash_slide(view, {'frying_pan': 'pan.webp'})
        self.assertEqual([e['name'] for e in wash['items']], ['Large pot', 'Bowl', 'Frying pan', 'Colander'])
        self.assertEqual(wash['title'], 'Dishes to wash: 4')
        self.assertEqual(wash['items'][2]['img'], 'pan.webp')
        self.assertEqual([e['id'] for e in social.cooking_vessels(view)], ['large_pot', 'frying_pan'])
        split = social.shop_split_slide(view, 'ig')
        self.assertTrue(split['tiles'] and split['have'])
        self.assertNotIn('Salt', [t['name'] for t in split['tiles']])

    def test_the_air_fryer_time_is_one_number_on_the_slide_and_in_the_hook(self):
        v = view_of(36, 11)  # 38 min of work, 11 in the air fryer, 49 in all
        self.assertEqual(social.hands_off(v, 'airfryer'), (11, 'the air fryer'))
        self.assertEqual(social.airfryer_slide(v, {})['minutes'], 11)
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

    # The whole recipe

    def test_the_whole_recipe_is_the_dish_the_list_and_every_step_in_its_own_words(self):
        rid = self.ids[0]  # carbonara: 9 steps
        view = page(db.session.get(Recipe, rid))
        for size in ('ig', 'tt'):
            with self.subTest(size=size):
                first = self.get(series='whole', ids=rid, n=1, size=size, code=8)
                self.assertEqual(first.headers['X-Hook-Text'], 'The whole recipe. 9 steps. Save it.')
                html = first.get_data(as_text=True)
                self.assertIn('class="hero"', html)
                self.assertNotIn('class="strip"', html)  # the dish and the hook: the symbols are on the next slide
                shop = self.get(series='whole', ids=rid, n=1, size=size, code=8, slide=2).get_data(as_text=True)
                self.assertIn(f"Serves {view['servings']}", shop)
                for s in view['steps']:
                    slide = self.get(series='whole', ids=rid, n=1, size=size, code=8, slide=s['n'] + 2).get_data(as_text=True)
                    self.assertIn(f"Step {s['n']} of 9", slide)
                    self.assertIn(str(s['html']), slide)  # the step list's own words, with the amounts, not cut
                    self.assertIn(s['short'].replace("'", '&#39;'), slide)
                    if s['done_when']:
                        self.assertIn(s['done_when'].replace("'", '&#39;'), slide)
                last = self.get(series='whole', ids=rid, n=1, size=size, code=8, slide=12).get_data(as_text=True)
                self.assertIn('Save this', last)
                self.assertIn(f'{social.ADDRESS[size]}/8', last)
        # A slide says what the step list says about the step, with the symbols of what goes in
        slides = social.full_step_slides(view, 'ig')
        self.assertEqual([sl['eyebrow'] for sl in slides][:2], ['Step 1 of 9', 'Step 2 of 9'])
        with_symbols = next(sl for sl in slides if sl['symbols'])
        self.assertEqual(set(with_symbols['symbols'][0]), {'name', 'img'})
        # The symbols take the room the words leave: large alone under a line of text, the smallest under a wall of it
        one = {**with_symbols, 'symbols': with_symbols['symbols'][:1], 'html': 'Cut the bacon.', 'done_when': None}
        self.assertEqual(social.full_step_tile(one, 'ig'), social.FULL_TILE_MAX)
        wall = {**with_symbols, 'symbols': with_symbols['symbols'] * 6, 'html': 'word ' * 90}
        self.assertEqual(social.full_step_tile(wall, 'ig'), social.FULL_TILE_MIN)
        timed = {**view, 'steps': [{**view['steps'][0], 'duration': '5 min + 20 min standing', 'equipment': 'Oven, 200 °C',
                                    'while': 'While: the pasta boils'}]}
        self.assertEqual(social.full_step_slides(timed, 'tt')[0]['facts'], ['5 min + 20 min standing', 'Oven, 200 °C'])
        self.assertEqual(social.full_step_slides(timed, 'tt')[0]['during'], 'While: the pasta boils')
        caption = self.get(series='whole', ids=rid, n=1, code=8, caption=1).get_data(as_text=True)
        self.assertIn('all 9 steps', caption)
        self.assertIn('thelazychef.app/ig/8', caption)

    def test_a_step_that_does_not_fit_leaves_the_recipe_out_and_is_never_cut(self):
        rid = self.ids[0]
        view = page(db.session.get(Recipe, rid))
        self.assertTrue(series.whole_ok(view))
        long = {**view, 'steps': [{**s, 'html': 'word ' * 400} for s in view['steps']]}
        self.assertFalse(social.full_steps_fit(long))
        self.assertFalse(series.whole_ok(long))
        # Too few or too many steps
        self.assertFalse(series.whole_ok({**view, 'steps': view['steps'][:7]}))
        self.assertFalse(series.whole_ok({**view, 'steps': view['steps'] * 2}))
        for rid_out in self.ids[1:3]:  # lasagne and tikka: 15 steps
            self.assertEqual(self.get(series='whole', ids=rid_out, n=1).status_code, 404)
        self.assertEqual(set(series.candidates('whole')), {self.ids[0], self.ids[3]})  # carbonara and brownies
        # The pick goes past one that does not fit
        real = series.whole_ok
        series.whole_ok = lambda v: v['title'] != db.session.get(Recipe, self.ids[0]).title and real(v)
        try:
            self.assertEqual(series.pick('whole'), [self.ids[3]])
            self.assertEqual(self.get(series='whole', ids=rid, n=1).status_code, 404)
        finally:
            series.whole_ok = real

    def test_the_whole_recipes_posts_stay_within_what_a_carousel_takes(self):
        kinds = series.SERIES['whole']['slides']
        self.assertEqual(kinds, ['cover', 'shop_split', 'full_steps', 'end'])
        self.assertLessEqual(series.WHOLE_STEPS[1] + len(kinds) - 1, social_publish.MAX_SLIDES)

    # Picking

    def test_every_series_but_guess_takes_dinners_only(self):
        breakfast = db.session.get(Recipe, self.ids[0])
        db.session.execute(db.delete(RecipeMealType).where(RecipeMealType.recipe_id == breakfast.id))
        db.session.add(RecipeMealType(recipe_id=breakfast.id, meal_type='Breakfast'))
        db.session.commit()
        for slug in series.SERIES:
            with self.subTest(series=slug):
                if slug == 'guess':
                    self.assertFalse(series.candidates(slug)[breakfast.id]['dinner'])
                else:
                    self.assertNotIn(breakfast.id, series.candidates(slug))
                    self.assertIn(self.ids[1], series.candidates(slug) if slug not in ('onepot', 'under20', 'only6', 'whole')
                                  else self.ids)
        # Guess the dish, not the dinner, on the one that is not one: in the caption (the hook is the score line)
        caption = self.get(series='guess', ids=breakfast.id, n=1, caption=1).get_data(as_text=True)
        self.assertIn('One dish,', caption)
        self.assertIn('One dinner,', self.get(series='guess', ids=self.ids[1], n=1, caption=1).get_data(as_text=True))

    def test_guess_the_dinner_is_a_points_game_over_five_slides(self):
        rid = self.ids[0]
        r = self.get(series='guess', ids=rid, n=12, code=3)
        self.assertEqual(r.headers['X-Views'], 'guess_pictures guess_names guess_amounts guess_dish answer')
        self.assertIn(r.headers['X-Hook-Text'], ('5 points if you guess from the pictures', '5 points: get it from the pictures'))
        self.assertEqual(r.headers['X-Cta'], 'ask')
        title = db.session.get(Recipe, rid).title
        pages = [self.get(series='guess', ids=rid, n=12, code=3, slide=n).get_data(as_text=True) for n in range(1, 6)]
        bodies = [p.split('<main', 1)[1] for p in pages]
        for body in bodies[:3]:  # the symbols the same size on the three slides with pictures
            self.assertIn('--symbol:', body)
        for body in bodies[:4]:  # the dish is not named before the answer
            self.assertNotIn(title, body)
            self.assertIn('class="bar"', body)
        self.assertIn('<b>5</b><span>' + r.headers['X-Hook-Text'][2:] + '</span>', bodies[0])
        self.assertIn('Not sure? Swipe for the names.', bodies[0])
        self.assertNotIn('<figcaption>', bodies[0])  # pictures only
        self.assertIn('<b>4</b><span>points with the names</span>', bodies[1])
        self.assertIn('<span>egg</span>', bodies[1])
        self.assertNotIn('<b>2</b><span>egg', bodies[1])  # no amounts yet
        self.assertIn('<b>3</b><span>points with the amounts</span>', bodies[2])
        self.assertIn('<b>2</b><span>egg</span>', bodies[2])
        self.assertIn('<b>2</b><span>points if you know it now</span>', bodies[3])
        self.assertIn('/static/recipes/carbonara.png', bodies[3])
        self.assertIn('Swipe for the answer.', bodies[3])
        self.assertEqual(bodies[0].count('class="on"'), 5)
        self.assertEqual(bodies[3].count('class="on"'), 2)
        self.assertIn('The answer', bodies[4])
        self.assertIn('class="title">Spaghetti carbonara</h1>', bodies[4])
        self.assertIn('How many points did you get?', bodies[4])
        self.assertIn('thelazychef.app/ig/3', bodies[4])
        self.assertEqual(bodies[4].count('The Lazy Chef'), 1)  # one wordmark
        caption = self.get(series='guess', ids=rid, n=12, code=3, caption=1).get_data(as_text=True)
        self.assertNotIn(title, caption)
        self.assertIn('5 points if you know it from the pictures alone, 4 with the names', caption)
        self.assertIn('How many points did you get?', caption)
        # At most GUESS_MAX things to buy: carbonara (5) is in, lasagne (21) and tikka (17) are left out
        c = series.candidates('guess')
        self.assertIn(self.ids[0], c)
        self.assertNotIn(self.ids[1], c)
        self.assertNotIn(self.ids[2], c)
        self.assertLessEqual(max(len(x['buy']) for x in c.values()), series.GUESS_MAX)

    def test_one_pot_under_20_and_only_6_pick_by_the_steps_and_the_list(self):
        c = series.candidates('onepot')  # exactly one vessel the food is cooked in, not the air fryer
        for rid in self.ids:
            db.session.get(Recipe, rid).heat_source = 'pan'
        db.session.commit()
        self.assertEqual(series.candidates('onepot'), {})  # the fixtures all cook in two or more, or in the air fryer
        self.assertEqual(c, {})
        self.assertEqual(list(series.candidates('under20')), [self.ids[0]])  # carbonara: 16 minutes of work
        self.assertEqual(list(series.candidates('only6')), [self.ids[0]])  # carbonara: five things to buy
        self.assertEqual(self.get(series='only6').headers['X-Recipes'], str(self.ids[0]))
        # A dinner made short enough, in the steps' active minutes
        from database.models import RecipeStep
        for step in db.session.execute(db.select(RecipeStep).where(RecipeStep.recipe_id == self.ids[1])).scalars():
            step.active_minutes = 1
        db.session.commit()
        self.assertEqual(sorted(series.candidates('under20')), self.ids[:2])
        self.assertEqual(series.pick('under20', datetime.date(2026, 11, 2)), [self.ids[0]])
        only = series.facts([post_of(view_of(6, 12))], 1, count=5, series='Only 6 things to buy')
        self.assertTrue(only['only_six'])
        self.assertEqual(series.hook_for(None, only, 'a', 'only6')[0], 'number')
        self.assertIn('5', series.hook_for(None, only, 'a', 'only6')[1])
        self.assertIsNone(series.hook('number', {**only, 'count': 9, 'only_six': False}, 'a', 'only6'))

    def test_three_ingredients_three_dinners_share_three_things_one_a_protein(self):
        views = [page(db.session.get(Recipe, i)) for i in self.ids[:3]]
        posts = [{'id': i, 'view': v, 'image': None, 'eq': {}, 'heat_source': None, 'protein': 'Beef',
                  'cuisine': 'Italian', 'dinner': True} for i, v in zip(self.ids, views)]
        shared = series.shared_trio(posts)
        self.assertEqual(len(shared['symbols']), min(3, len(shared['keys'])))
        self.assertEqual(series.merge_key('a', 'Chicken'), series.merge_key('b', 'Chicken'))
        # Three dinners sharing chicken (thigh, breast, thigh), onion and garlic: one set, named "chicken"; two near
        # copies (more than WEEK_SAME of the list in common) are not three different dishes
        c = {1: {'buy': frozenset({1, 10, 11, 20, 21, 22, 23, 24}), 'protein': 'Chicken'},
             2: {'buy': frozenset({2, 10, 11, 30, 31, 32, 33, 34}), 'protein': 'Chicken'},
             3: {'buy': frozenset({1, 10, 11, 40, 41, 42, 43, 44}), 'protein': 'Chicken'},
             4: {'buy': frozenset({1, 10, 11, 20, 21, 22, 23, 25}), 'protein': 'Chicken'}}
        from database.models import Ingredient
        for i, name, sub in ((1, 'chicken thigh', 'chicken'), (2, 'chicken breast', 'chicken'), (10, 'onion', 'onion'),
                             (11, 'garlic', 'garlic')):
            db.session.add(Ingredient(id=i, food_id=f'f{i}', name=name, main_category='meat' if i < 3 else 'produce',
                                      sub_category=sub, tier='core', status='active'))
        db.session.commit()
        sets = series.trios(c)
        self.assertEqual([ids for ids, _ in sets], [[1, 2, 3], [2, 3, 4]])  # 1 and 4 share 7 of 9: near copies
        # The same dish by name is one dish, however different its list; a dinner buying too much is left out
        named = {i: {**c[i], 'title': t} for i, t in zip(c, ('Butter Chicken with Basmati Rice and Naan', 'Chicken Pad Thai',
                                                           'Butter Chicken with Basmati Rice and Homemade Naan', 'Chicken Curry'))}
        self.assertEqual([ids for ids, _ in series.trios(named)], [[2, 3, 4]])
        big = {**c, 2: {**c[2], 'buy': frozenset(range(100, 100 + series.TRIO_BUY_MAX + 1)) | {2, 10, 11}}}
        self.assertEqual(series.trios(big), [])
        self.assertEqual(series.trio(c, [1, 2, 3, 4], {}), [1, 2, 3])
        self.assertNotEqual(series.merge_key('a', 'Beef'), series.merge_key('b', 'Beef'))
        # The fixtures share salt and oil only (staples), so no set: the series has run out
        self.assertEqual(series.pick('three3', datetime.date(2026, 11, 2)), [])
        self.assertEqual(self.get(series='three3').status_code, 404)
        ids = ','.join(map(str, self.ids[:3]))
        cover = self.get(series='three3', ids=ids, n=1, slide=1).get_data(as_text=True)
        self.assertIn('3 ingredients, 3 dinners #1', cover)

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
        self.assertEqual(len(series.pick('cuisine', today)), 4)
        self.assertEqual(len(series.pick('protein4', today)), 4)
        for rid in self.ids[:2]:
            db.session.get(Recipe, rid).cuisine = 'Thai'
        db.session.commit()
        self.assertEqual(series.pick('cuisine', today), [])
        self.assertEqual(self.get(series='cuisine').status_code, 404)  # the series has run out: it pauses

    def test_a_post_without_recipes_picks_them_and_says_which(self):
        r = self.get(series='protein')
        self.assertEqual(r.status_code, 200)
        self.assertEqual((r.headers['X-Recipes'], r.headers['X-N']), (str(self.ids[0]), '1'))


if __name__ == '__main__':
    unittest.main()
