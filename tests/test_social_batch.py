"""A day of posts from scripts/social_batch.py: the drafts it logs with their codes through the social API, series
and formats, marking a draft posted, the day's series, and reading a plan (services/funnel.py,
routes/social_api_routes.py)."""
import datetime
import os
import sys
import unittest
from unittest import mock

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(ROOT)

os.environ['DB_BACKEND'] = 'local'
os.environ['DATABASE_URL'] = 'sqlite://'
os.environ['STORAGE_BACKEND'] = 'local'
os.environ.setdefault('SECRET_KEY', 'test-secret')
os.environ.setdefault('GOOGLE_API_KEY', 'test-key')
os.environ.pop('K_SERVICE', None)

from app import app  # noqa: E402
from database.models import Recipe, SocialPost, User, db  # noqa: E402
from scripts.social_batch import day_plan, folder_name, parse_plan, plan_post  # noqa: E402
from services import funnel, social_series  # noqa: E402

DAY = datetime.date(2026, 11, 3)  # a Tuesday
KEY = 'test-content-key'


def airfryer(n, ids, hook='12 min of work.', cta=None):
    return {'format': 'series', 'series': 'airfryer', 'series_n': n, 'ids': ids, 'hook': hook, 'hook_group': 'lazy',
            'cta_group': cta or {'tiktok': 'site', 'instagram': 'bio'}, 'views': 'cover airfryer end', 'look': 'd',
            'slides': 6}


class DayOfPostsTests(unittest.TestCase):
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
        for n in range(1, 7):
            recipe = Recipe(title=f'Dish {n}', cuisine='', difficulty='', status='approved', schema_version=2)
            db.session.add(recipe)
            db.session.flush()
            self.ids.append(recipe.id)
        db.session.commit()
        self.client = app.test_client()
        self.key = mock.patch.dict(os.environ, {'CONTENT_API_KEY': KEY})
        self.key.start()

    def tearDown(self):
        self.key.stop()
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def drafts(self, *posts, day=DAY):
        return self.client.post('/api/social/drafts', json={'day': day.isoformat(), 'posts': list(posts)},
                                headers={'Authorization': f'Bearer {KEY}'})

    def posts(self):
        return db.session.execute(db.select(SocialPost).order_by(SocialPost.id)).scalars().all()

    def test_the_api_needs_the_key(self):
        self.assertEqual(self.client.post('/api/social/drafts').status_code, 401)
        self.assertEqual(self.client.post('/api/social/drafts', headers={'Authorization': 'Bearer wrong'},
                                          json={}).status_code, 401)
        self.assertEqual(self.drafts().status_code, 400)

    def test_a_series_post_is_a_draft_on_both_platforms_with_what_the_site_chose(self):
        db.session.add(SocialPost(platform='tiktok', code='4', format='grid', title='Earlier', posted_on=DAY))
        db.session.commit()
        body = self.drafts(airfryer(7, [self.ids[2]])).get_json()
        self.assertEqual([(p['code'], p['series'], p['series_n'], p['title'], p['new']) for p in body['posts']],
                         [('5', 'airfryer', 7, 'airfryer #7: 12 min of work.', True)])
        tiktok, instagram = sorted((p for p in self.posts() if p.code == '5'), key=lambda p: p.platform != 'tiktok')
        for post in (tiktok, instagram):
            self.assertEqual((post.status, post.posted_on, post.format, post.series, post.series_n, post.recipe_id,
                              post.recipe_ids, post.hook, post.hook_group, post.views, post.look, post.slides),
                             ('draft', DAY, 'series', 'airfryer', 7, self.ids[2], str(self.ids[2]),
                              '12 min of work.', 'lazy', 'cover airfryer end', 'd', 6))
        self.assertEqual((tiktok.cta_group, instagram.cta_group), ('site', 'bio'))

    def test_the_next_post_of_a_series_sees_the_draft(self):
        self.drafts(airfryer(7, [self.ids[2]]))
        self.assertEqual(social_series.next_n('airfryer'), 8)
        self.assertEqual(social_series.used_in('airfryer'), {self.ids[2]: DAY})

    def test_formats_are_logged_too(self):
        body = self.drafts({'format': 'map', 'recipe_id': self.ids[1], 'hook': '4 lines, 1 plate',
                            'hook_group': 'number', 'cta_group': 'save'},
                           {'format': 'week', 'ids': self.ids[:5]}, {'format': 'pantry'}).get_json()
        self.assertEqual([(p['code'], p['format'], p['title'], p['recipe_ids']) for p in body['posts']],
                         [('1', 'map', 'Dish 2', str(self.ids[1])),
                          ('2', 'week', 'One shop, five dinners', ','.join(str(i) for i in self.ids[:5])),
                          ('3', 'pantry', 'The foundation pantry', None)])
        self.assertEqual({(p.hook, p.hook_group, p.cta_group) for p in self.posts() if p.code == '1'},
                         {('4 lines, 1 plate', 'number', 'save')})
        self.assertEqual(len(self.posts()), 6)
        self.assertEqual(funnel.next_code(), '4')

    def test_the_same_post_sent_again_keeps_its_code(self):
        self.drafts(airfryer(7, [self.ids[2]]), {'format': 'grid', 'recipe_id': self.ids[0]})
        again = self.drafts(airfryer(7, [self.ids[2]], hook='Air fryer, 12 minutes.'),
                            {'format': 'grid', 'recipe_id': self.ids[0]}, {'format': 'pantry'}).get_json()
        self.assertEqual([(p['code'], p['new']) for p in again['posts']], [('1', False), ('2', False), ('3', True)])
        self.assertEqual(len(self.posts()), 6)
        self.assertEqual({p.hook for p in self.posts() if p.code == '1'}, {'Air fryer, 12 minutes.'})

    def test_a_wrong_plan_saves_nothing(self):
        db.session.get(Recipe, self.ids[3]).status = 'draft'
        db.session.commit()
        for posts, message in (([{'format': 'other'}], 'format must be series or one of'),
                               ([{'format': 'map'}], 'map needs an approved recipe'),
                               ([{'format': 'grid', 'recipe_id': self.ids[3]}], 'grid needs an approved recipe'),
                               ([{'format': 'week', 'ids': [1, 2]}], 'ids are the five recipe ids'),
                               ([{'format': 'series', 'series': 'soup', 'series_n': 1, 'ids': [1]}], 'series must'),
                               ([{**airfryer(1, [1]), 'series_n': None}], 'needs its number'),
                               ([{**airfryer(1, [1]), 'ids': None}], 'needs its recipes'),
                               ([{**airfryer(1, [1]), 'hook_group': 'loud'}], 'hook_group must be one of'),
                               ([{**airfryer(1, [1]), 'cta_group': {'tiktok': 'shout'}}], 'cta_group must be'),
                               ([{'format': 'pantry'}, {'format': 'map', 'recipe_id': 999}], 'post 2: map needs')):
            with self.subTest(posts=posts):
                response = self.drafts(*posts)
                self.assertEqual(response.status_code, 400)
                self.assertIn(message, ' '.join(response.get_json()['errors']))
        self.assertEqual(self.posts(), [])

    def test_a_draft_is_marked_posted_on_the_funnel_page(self):
        self.drafts({'format': 'pantry'})
        self.client.post('/login', data={'email': 'admin@test', 'password': 'pw'})
        html = self.client.get('/admin/funnel').get_data(as_text=True)
        self.assertEqual(html.count('>Draft</span>'), 2)
        tiktok = next(p for p in self.posts() if p.platform == 'tiktok')
        self.client.post(f'/admin/funnel/posts/{tiktok.id}/posted')
        self.assertEqual((tiktok.status, tiktok.posted_on), ('posted', datetime.date.today()))
        self.assertEqual(self.client.get('/admin/funnel').get_data(as_text=True).count('>Draft</span>'), 1)
        self.assertIn('<option value="posted" selected>',
                      self.client.get(f'/admin/funnel/posts/{tiktok.id}').get_data(as_text=True))

    # The numbers sheet

    def day_of_posts(self, on, first=1):
        """Three codes from first on both platforms, up on the date on, a draft for that day that is not up yet, and a
        post from the day before."""
        for code in range(first, first + 3):
            for platform in ('tiktok', 'instagram'):
                db.session.add(SocialPost(platform=platform, code=str(code), format='map', title=f'Post {code}',
                                          posted_on=on))
        db.session.add(SocialPost(platform='tiktok', code=str(first + 4), format='map', title='Draft', posted_on=on,
                                  status='draft'))
        db.session.add(SocialPost(platform='tiktok', code=str(first + 3), format='map', title='Other day',
                                  posted_on=on - datetime.timedelta(days=1)))
        db.session.commit()

    def test_the_sheet_holds_one_dates_posts_tiktok_first_and_no_drafts(self):
        self.day_of_posts(DAY)
        rows = funnel.sheet(7, DAY)
        self.assertEqual([funnel.post_ref(r['post']) for r in rows],
                         ['tiktok-1', 'tiktok-2', 'tiktok-3', 'instagram-1', 'instagram-2', 'instagram-3'])
        self.assertEqual(len(funnel.sheet(7, DAY, 'instagram')), 3)
        self.client.post('/login', data={'email': 'admin@test', 'password': 'pw'})
        on = datetime.date.today() - datetime.timedelta(days=2)
        self.day_of_posts(on, first=11)
        html = self.client.get('/admin/funnel/numbers?day=2').get_data(as_text=True)
        self.assertIn(f'went up on {on.strftime("%d.%m.%Y")}', html)
        self.assertNotIn('Other day', html)
        self.assertNotIn('>Draft<', html)

    def test_the_sheet_saves_every_post_that_got_numbers_and_nothing_when_one_is_wrong(self):
        self.day_of_posts(DAY)
        self.client.post('/login', data={'email': 'admin@test', 'password': 'pw'})
        rows = funnel.sheet(7, DAY)
        first, second = rows[0]['post'], rows[1]['post']
        url = f'/admin/funnel/numbers?day=7&on={DAY}'
        response = self.client.post(url, data={f'{first.id}-views': '1 200', f'{second.id}-saves': 'many'})
        self.assertEqual(response.status_code, 400)
        self.assertIn('tiktok-2: Saves must be a whole number.', response.get_data(as_text=True))
        self.assertIn('value="1 200"', response.get_data(as_text=True))
        self.assertEqual(first.stats, [])
        response = self.client.post(url, data={f'{first.id}-views': '1 200', f'{first.id}-profile_visits': '4',
                                               f'{second.id}-saves': '3'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual([(s.day, s.views, s.profile_visits) for s in first.stats], [(7, 1200, 4)])
        self.assertEqual([(s.day, s.saves) for s in second.stats], [(7, 3)])
        self.assertEqual(rows[2]['post'].stats, [])
        html = self.client.get(url).get_data(as_text=True)
        self.assertIn(f'name="{first.id}-views" value="1200"', html)
        self.client.post(url, data={f'{first.id}-views': '1500'})
        self.assertEqual([(s.views, s.profile_visits) for s in first.stats], [(1500, None)])

    # Per format and hook

    def test_formats_and_hooks_are_summed_per_platform_over_the_window(self):
        today = datetime.date(2026, 11, 10)
        posts = (  # (platform, code, format, hook, days ago, views, saves, visits, status)
            ('tiktok', '1', 'map', 'Guess it', 1, 1000, 10, 2, 'posted'),
            ('tiktok', '2', 'map', 'Guess it', 3, 3000, 20, 1, 'posted'),
            ('tiktok', '3', 'map', 'Once', 2, None, None, 0, 'posted'),
            ('tiktok', '4', 'grid', None, 6, 500, 0, 0, 'posted'),
            ('tiktok', '5', 'grid', None, 20, 900, 9, 9, 'posted'),
            ('instagram', '1', 'map', 'Guess it', 1, 200, 2, 4, 'posted'),
            ('tiktok', '6', 'map', None, 0, None, None, 0, 'draft'))
        rows = []
        for platform, code, fmt, hook, ago, views, saves, visits, status in posts:
            post = SocialPost(platform=platform, code=code, format=fmt, hook=hook, title='x', status=status,
                              posted_on=today - datetime.timedelta(days=ago))
            latest = mock.Mock(views=views, saves=saves) if views is not None else None
            rows.append({'post': post, 'latest': latest, 'visits': visits})
        week = funnel.summary(rows, today, 7)
        self.assertEqual([(g['platform'], g['label'], g['posts'], g['median_views'], g['saves_1000'],
                           g['visits_1000']) for g in week['formats']],
                         [('tiktok', 'map', 3, 2000, 7.5, 0.8), ('tiktok', 'grid', 1, 500, 0.0, 0.0),
                          ('instagram', 'map', 1, 200, 10.0, 20.0)])
        self.assertEqual([(g['platform'], g['label'], g['posts']) for g in week['hooks']],
                         [('tiktok', 'Guess it', 2)])
        month = funnel.summary(rows, today, 28)
        self.assertEqual([(g['label'], g['posts']) for g in month['formats'] if g['platform'] == 'tiktok'],
                         [('grid', 2), ('map', 3)])

    def test_the_funnel_page_shows_formats_and_hooks(self):
        self.api('POST', '/drafts', json={'day': datetime.date.today().isoformat(),
                                          'posts': [{'format': 'pantry', 'hook': 'Save this'}]})
        self.client.post('/login', data={'email': 'admin@test', 'password': 'pw'})
        html = self.client.get('/admin/funnel').get_data(as_text=True)
        self.assertIn('Per format and hook', html)
        self.assertIn('No posts went up in the last 7 days.', html)
        for post in self.posts():
            self.client.post(f'/admin/funnel/posts/{post.id}/posted')
        html = self.client.get('/admin/funnel').get_data(as_text=True)
        self.assertIn('<span class="font-mono">pantry</span>', html)
        self.assertNotIn('No posts went up in the last 7 days.', html)


class PlanTests(unittest.TestCase):
    def test_a_day_is_the_four_series_and_a_fifth_by_weekday(self):
        monday = datetime.date(2026, 11, 2)
        self.assertEqual([p['kind'] for p in day_plan(monday)], ['airfryer', 'got', 'protein', 'dishes', 'guess'])
        self.assertEqual(day_plan(monday + datetime.timedelta(days=2))[-1]['kind'], 'cuisine')
        self.assertEqual(day_plan(monday + datetime.timedelta(days=4))[-1]['kind'], 'guess')
        fifths = {day_plan(monday + datetime.timedelta(days=d))[-1]['kind'] for d in (1, 3, 5, 6, 8)}
        self.assertTrue(fifths <= {'airfryer', 'got', 'protein', 'dishes'})

    def test_a_plan_is_a_post_per_line(self):
        text = ('# Tuesday\nairfryer hook=number cta=follow\ngot 323,326,329 hook=search n=4\nguess\n\n'
                'map 345 cta=save | 4 lines, 1 plate\nweek 1,2,3,4,5\npantry\n')
        self.assertEqual(parse_plan(text), [
            {'kind': 'airfryer', 'hook': 'number', 'cta': 'follow'},
            {'kind': 'got', 'ids': [323, 326, 329], 'hook': 'search', 'n': 4},
            {'kind': 'guess'},
            {'kind': 'map', 'ids': [345], 'cta': 'save', 'words': '4 lines, 1 plate'},
            {'kind': 'week', 'ids': [1, 2, 3, 4, 5]},
            {'kind': 'pantry'}])

    def test_a_line_it_cannot_read_says_which_and_why(self):
        for line, why in (('soup', 'not a series'), ('map', 'takes one recipe'), ('grid 1,2', 'takes one recipe'),
                          ('pantry 4', 'takes no recipes'), ('week 1,2', 'five recipes'),
                          ('airfryer hook=loud', 'is not recipes'), ('map 3 n=2', 'is not recipes'),
                          ('airfryer | Look at this', 'writes its own hook')):
            with self.subTest(line=line), self.assertRaisesRegex(ValueError, f'line 2: .*{why}'):
                parse_plan(f'pantry\n{line}')

    def test_a_series_is_asked_in_both_sizes_and_fixed_for_the_render(self):
        answers = {'tt': {'X-N': '7', 'X-Recipes': '325', 'X-Hook': 'lazy', 'X-Hook-Text': '12 min of work.',
                          'X-Cta': 'site', 'X-Views': 'cover end', 'X-Look': 'd', 'X-Slides': '6'}}
        answers['ig'] = {**answers['tt'], 'X-Cta': 'bio'}
        asked = []

        def fetch(url, context):
            asked.append(url)
            return answers['tt' if 'size=tt' in url else 'ig'], ''
        with mock.patch('scripts.social_batch.fetch', fetch):
            draft, query, page, recipe = plan_post({'kind': 'airfryer', 'cta': 'bio'}, 'http://x', None, None)
        self.assertEqual(len(asked), 2)
        self.assertEqual((draft['series_n'], draft['ids'], draft['hook'], draft['hook_group'], draft['cta_group']),
                         (7, [325], '12 min of work.', 'lazy', {'tiktok': 'site', 'instagram': 'bio'}))
        self.assertEqual((query['ids'], query['n'], query['hook'], query['cta'], page, recipe),
                         ('325', '7', 'lazy', 'bio', 'series', None))

    def test_a_post_has_a_folder_by_its_place_code_and_recipes(self):
        self.assertEqual(folder_name(1, {'code': '5', 'format': 'series', 'series': 'got', 'series_n': 4,
                                         'recipe_ids': '323,326,329'}), '1-code5-got4-323-326-329')
        self.assertEqual(folder_name(2, {'code': '6', 'format': 'map', 'series': None, 'series_n': None,
                                         'recipe_ids': '345'}), '2-code6-map-345')
        self.assertEqual(folder_name(3, {'code': '7', 'format': 'pantry', 'series': None, 'series_n': None,
                                         'recipe_ids': None}), '3-code7-pantry')


if __name__ == '__main__':
    unittest.main()
