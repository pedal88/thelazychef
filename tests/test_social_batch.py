"""A day of posts from scripts/social_batch.py: the posts the site suggests, the drafts it logs with their codes
through the social API, marking a draft posted, and reading a plan (services/funnel.py, routes/social_api_routes.py)."""
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
from database.models import Recipe, RecipeComponent, SocialPost, User, db  # noqa: E402
from scripts.social_batch import folder_name, parse_plan  # noqa: E402
from services import funnel  # noqa: E402

DAY = datetime.date(2026, 11, 3)
KEY = 'test-content-key'


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
        # Recipes with 1, 3, 4, 2, 3 and 5 parts; the candidates are mocked, so only the parts matter here
        self.ids = []
        for n, parts in enumerate((1, 3, 4, 2, 3, 5), 1):
            recipe = Recipe(title=f'Dish {n}', cuisine='', difficulty='', status='approved', schema_version=2)
            db.session.add(recipe)
            db.session.flush()
            for p in range(parts):
                db.session.add(RecipeComponent(recipe_id=recipe.id, local_id=f'c{p}', name=f'Part {p}', sort_order=p))
            self.ids.append(recipe.id)
        db.session.commit()
        self.client = app.test_client()
        self.candidates = mock.patch('services.funnel.social_week.candidates', lambda: dict.fromkeys(self.ids, {}))
        self.candidates.start()
        self.key = mock.patch.dict(os.environ, {'CONTENT_API_KEY': KEY})
        self.key.start()

    def tearDown(self):
        self.key.stop()
        self.candidates.stop()
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def api(self, method, path, **kw):
        return self.client.open(f'/api/social{path}', method=method, headers={'Authorization': f'Bearer {KEY}'}, **kw)

    def posts(self):
        return db.session.execute(db.select(SocialPost).order_by(SocialPost.id)).scalars().all()

    # What the site suggests

    def test_the_formats_take_turns_and_a_map_has_three_or_four_parts(self):
        picked = funnel.suggest(DAY, 5)
        self.assertEqual([(p['format'], p['recipe_id']) for p in picked],
                         [('map', self.ids[1]), ('grid', self.ids[0]), ('map', self.ids[2]), ('grid', self.ids[3]),
                          ('map', self.ids[4])])
        self.assertEqual(picked[0]['title'], 'Dish 2')

    def test_a_recipe_rests_after_a_post_and_a_map_falls_back_to_a_grid(self):
        db.session.add(SocialPost(platform='tiktok', code='1', format='map', recipe_id=self.ids[1], title='Dish 2',
                                  posted_on=DAY - datetime.timedelta(days=funnel.RECIPE_REST_DAYS - 1)))
        db.session.add(SocialPost(platform='tiktok', code='2', format='map', recipe_id=self.ids[2], title='Dish 3',
                                  posted_on=DAY - datetime.timedelta(days=funnel.RECIPE_REST_DAYS)))
        db.session.commit()
        picked = funnel.suggest(DAY, 6)
        self.assertNotIn(self.ids[1], [p['recipe_id'] for p in picked])
        self.assertEqual([p['format'] for p in picked], ['map', 'grid', 'map', 'grid', 'grid'])

    # The drafts

    def test_the_api_needs_the_key(self):
        for method, path in (('GET', f'/suggest?day={DAY}'), ('POST', '/drafts')):
            with self.subTest(path=path):
                self.assertEqual(self.client.open(f'/api/social{path}', method=method).status_code, 401)
                self.assertEqual(self.client.open(f'/api/social{path}', method=method,
                                                  headers={'Authorization': 'Bearer wrong'}).status_code, 401)
        self.assertEqual(self.api('GET', '/suggest?day=tomorrow').status_code, 400)
        self.assertEqual(self.api('GET', f'/suggest?day={DAY}&n=2').get_json()['posts'][0]['format'], 'map')

    def test_a_day_is_logged_as_drafts_on_both_platforms_under_one_code_each(self):
        db.session.add(SocialPost(platform='tiktok', code='4', format='grid', title='Earlier', posted_on=DAY))
        db.session.commit()
        plan = [{'format': 'map', 'recipe_id': self.ids[1], 'hook': '4 lines, 1 plate'},
                {'format': 'week', 'ids': self.ids[:5]}, {'format': 'pantry'}]
        body = self.api('POST', '/drafts', json={'day': DAY.isoformat(), 'posts': plan}).get_json()
        self.assertEqual([(p['code'], p['format'], p['title'], p['new']) for p in body['posts']],
                         [('5', 'map', 'Dish 2', True), ('6', 'week', 'One shop, five dinners', True),
                          ('7', 'pantry', 'The foundation pantry', True)])
        drafts = [p for p in self.posts() if p.status == 'draft']
        self.assertEqual(sorted((p.platform, p.code) for p in drafts),
                         sorted((platform, code) for code in '567' for platform in ('instagram', 'tiktok')))
        self.assertTrue(all(p.posted_on == DAY for p in drafts))
        self.assertEqual({p.hook for p in drafts if p.code == '5'}, {'4 lines, 1 plate'})
        week = next(p for p in drafts if p.code == '6')
        self.assertEqual(week.notes, 'Recipes ' + ','.join(str(i) for i in self.ids[:5]))
        self.assertEqual(funnel.next_code(), '8')

    def test_the_same_day_sent_again_keeps_its_codes(self):
        plan = [{'format': 'map', 'recipe_id': self.ids[1]}, {'format': 'grid', 'recipe_id': self.ids[0]}]
        self.api('POST', '/drafts', json={'day': DAY.isoformat(), 'posts': plan})
        plan[1]['hook'] = 'Guess the dinner'
        again = self.api('POST', '/drafts', json={'day': DAY.isoformat(), 'posts': plan + [{'format': 'pantry'}]})
        self.assertEqual([(p['code'], p['new']) for p in again.get_json()['posts']],
                         [('1', False), ('2', False), ('3', True)])
        self.assertEqual(len(self.posts()), 6)
        self.assertEqual({p.hook for p in self.posts() if p.code == '2'}, {'Guess the dinner'})

    def test_a_wrong_plan_saves_nothing(self):
        db.session.get(Recipe, self.ids[3]).status = 'draft'
        db.session.commit()
        for posts, message in (([{'format': 'other'}], 'format must be one of'),
                               ([{'format': 'map'}], 'map needs an approved recipe'),
                               ([{'format': 'grid', 'recipe_id': self.ids[3]}], 'grid needs an approved recipe'),
                               ([{'format': 'week', 'ids': [1, 2]}], 'ids are the five recipe ids'),
                               ([{'format': 'pantry'}, {'format': 'map', 'recipe_id': 999}], 'post 2: map needs')):
            with self.subTest(posts=posts):
                response = self.api('POST', '/drafts', json={'day': DAY.isoformat(), 'posts': posts})
                self.assertEqual(response.status_code, 400)
                self.assertIn(message, ' '.join(response.get_json()['errors']))
        self.assertEqual(self.api('POST', '/drafts', json={'posts': []}).status_code, 400)
        self.assertEqual(self.posts(), [])

    def test_a_draft_is_marked_posted_on_the_funnel_page(self):
        self.api('POST', '/drafts', json={'day': DAY.isoformat(), 'posts': [{'format': 'pantry'}]})
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
    def test_a_plan_is_a_post_per_line_with_its_hook(self):
        text = ('# Tuesday\nmap 345 | 4 lines, 1 plate, 42 minutes\ngrid 297\n\n'
                'week 1,2,3,4,5 | One shop\nweek\npantry\n')
        self.assertEqual(parse_plan(text), [
            {'format': 'map', 'hook': '4 lines, 1 plate, 42 minutes', 'recipe_id': 345},
            {'format': 'grid', 'hook': None, 'recipe_id': 297},
            {'format': 'week', 'hook': 'One shop', 'ids': [1, 2, 3, 4, 5]},
            {'format': 'week', 'hook': None},
            {'format': 'pantry', 'hook': None}])

    def test_a_line_it_cannot_read_says_which(self):
        for line in ('map', 'map soup', 'grid 1 2', 'pantry 4', 'week a,b'):
            with self.subTest(line=line), self.assertRaisesRegex(ValueError, 'line 2'):
                parse_plan(f'pantry\n{line}')

    def test_a_post_has_a_folder_by_its_place_code_and_recipe(self):
        self.assertEqual(folder_name(1, {'code': '5', 'format': 'map', 'recipe_id': 345, 'ids': None}),
                         '1-code5-map-345')
        self.assertEqual(folder_name(2, {'code': '6', 'format': 'week', 'recipe_id': None, 'ids': [1, 2, 3, 4, 5]}),
                         '2-code6-week-1-2-3-4-5')
        self.assertEqual(folder_name(3, {'code': '7', 'format': 'pantry', 'recipe_id': None, 'ids': None}),
                         '3-code7-pantry')


if __name__ == '__main__':
    unittest.main()
