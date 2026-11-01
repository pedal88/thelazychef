"""Instagram's numbers fetched into the post log (services/social_stats.py): matching posts by their code or link, a
draft marked posted, which days are fetched, rows typed in by hand left alone, the daily job's token and the Funnel
page's button. Meta is stood in for: no test calls the Graph API."""
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
from database.models import SocialPost, SocialPostStat, User, db  # noqa: E402
from services import funnel, social_stats  # noqa: E402

TODAY = datetime.date(2026, 11, 10)
IG = {'INSTAGRAM_ACCESS_TOKEN': 'test-token', 'INSTAGRAM_USER_ID': '178414'}


def insight(name, value):
    return {'name': name, 'period': 'lifetime', 'values': [{'value': value}]}


class FakeMeta:
    """The Graph API's answers, as the spike of 01.11.2026 got them: the posts in pages, and per post its metrics."""

    def __init__(self, posts, numbers, page=25):
        self.posts, self.numbers, self.page, self.asked = posts, numbers, page, []

    def __call__(self, path, params):
        self.asked.append((path, params))
        if path.endswith('/media'):
            start = int(params.get('after', 0))
            data = self.posts[start:start + self.page]
            more = start + self.page < len(self.posts)
            paging = {'cursors': {'after': str(start + self.page)}, **({'next': 'x'} if more else {})}
            return {'data': data, 'paging': paging}
        media_id = path.split('/')[0]
        if media_id not in self.numbers:
            raise social_stats.StatsError('(#10) Not enough viewers for the media to show insights')
        return {'data': [insight(k, v) for k, v in self.numbers[media_id].items()]}


def item(media_id, caption, day, link=None):
    return {'id': media_id, 'caption': caption, 'permalink': link or f'https://www.instagram.com/p/{media_id}/',
            'timestamp': f'{day.isoformat()}T09:17:36+0000', 'media_type': 'CAROUSEL_ALBUM'}


NUMBERS = {'views': 7, 'reach': 2, 'likes': 1, 'comments': 0, 'saved': 3, 'shares': 1, 'profile_visits': 2,
           'follows': 0, 'total_interactions': 5}


class InstagramFetchTests(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        self.ctx = app.app_context()
        self.ctx.push()
        db.drop_all()
        db.create_all()
        admin = User(email='admin@test', is_admin=True)
        admin.set_password('pw')
        db.session.add(admin)
        db.session.commit()
        self.env = mock.patch.dict(os.environ, IG)
        self.env.start()

    def tearDown(self):
        self.env.stop()
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def log(self, code, posted_on, status='posted', platform='instagram', url=None):
        post = SocialPost(platform=platform, code=code, format='series', title=f'Post {code}', posted_on=posted_on,
                          status=status, url=url)
        db.session.add(post)
        db.session.commit()
        return post

    def test_a_post_is_found_by_its_code_and_gets_the_days_numbers(self):
        post = self.log('5', TODAY - datetime.timedelta(days=2))
        meta = FakeMeta([item('m5', 'Air fryer #7\n\nEvery step: thelazychef.app/ig/5 #recipe', post.posted_on)],
                        {'m5': NUMBERS})
        summary = social_stats.fetch_instagram(TODAY, meta, now=datetime.datetime(2026, 11, 10, 5))
        self.assertEqual((summary['read'], summary['matched'], summary['saved']), (1, 1, 1))
        [stat] = post.stats
        self.assertEqual((stat.day, stat.views, stat.reach, stat.likes, stat.comments, stat.saves, stat.shares,
                          stat.profile_visits, stat.source, stat.fetched_at),
                         (2, 7, 2, 1, 0, 3, 1, 2, 'instagram', datetime.datetime(2026, 11, 10, 5)))
        self.assertEqual(post.url, 'https://www.instagram.com/p/m5/')
        self.assertIn(('m5/insights', {'metric': 'views,reach,likes,comments,saved,shares,profile_visits'}),
                      meta.asked)

    def test_a_post_without_a_code_is_found_by_its_link_and_others_are_reported(self):
        post = self.log('2', TODAY, url='https://www.instagram.com/p/old/')
        self.log('2', TODAY, platform='tiktok')
        meta = FakeMeta([item('m1', 'Guess the dinner', TODAY, link='https://www.instagram.com/p/old'),
                         item('m2', 'thelazychef.app/ig/99', TODAY), item('m3', 'Our first post', TODAY)],
                        {'m1': NUMBERS})
        summary = social_stats.fetch_instagram(TODAY, meta)
        self.assertEqual((summary['matched'], summary['saved']), (1, 1))
        self.assertEqual(summary['unlogged'], ['https://www.instagram.com/p/m2/', 'https://www.instagram.com/p/m3/'])
        self.assertEqual(post.stats[0].day, 0)

    def test_a_draft_becomes_posted_on_the_day_instagram_says(self):
        post = self.log('7', TODAY - datetime.timedelta(days=1), status='draft')
        went_up = TODAY - datetime.timedelta(days=3)
        summary = social_stats.fetch_instagram(TODAY, FakeMeta([item('m7', 'thelazychef.app/ig/7', went_up)],
                                                               {'m7': NUMBERS}))
        self.assertEqual((post.status, post.posted_on, summary['posted']), ('posted', went_up, 1))
        self.assertEqual(post.stats[0].day, 3)

    def test_only_due_days_are_fetched_and_typed_rows_are_left_alone(self):
        posts = {day: self.log(str(day), TODAY - datetime.timedelta(days=day)) for day in (14, 15, 30, 31)}
        typed = self.log('1', TODAY - datetime.timedelta(days=7))
        funnel.save_stat(typed, {'day': '7', 'views': '400'})
        meta = FakeMeta([item(f'm{p.code}', f'thelazychef.app/ig/{p.code}', p.posted_on)
                         for p in [*posts.values(), typed]], {f'm{c}': NUMBERS for c in ('14', '15', '30', '31', '1')})
        summary = social_stats.fetch_instagram(TODAY, meta)
        self.assertEqual(summary['saved'], 2)
        self.assertEqual({day: [s.day for s in p.stats] for day, p in posts.items()},
                         {14: [14], 15: [], 30: [30], 31: []})
        self.assertEqual([(s.views, s.source) for s in typed.stats], [(400, 'manual')])

    def test_a_fetched_row_is_refreshed_and_one_post_failing_does_not_stop_the_rest(self):
        a, b = self.log('1', TODAY), self.log('2', TODAY)
        meta = FakeMeta([item('m1', 'thelazychef.app/ig/1', TODAY), item('m2', 'thelazychef.app/ig/2', TODAY)],
                        {'m1': NUMBERS})
        summary = social_stats.fetch_instagram(TODAY, meta)
        self.assertEqual(summary['errors'], ['instagram-2: (#10) Not enough viewers for the media to show insights'])
        self.assertEqual((len(a.stats), len(b.stats)), (1, 0))
        meta.numbers['m1'] = {**NUMBERS, 'views': 50}
        social_stats.fetch_instagram(TODAY, meta)
        self.assertEqual([s.views for s in a.stats], [50])

    def test_the_posts_are_read_page_by_page_up_to_a_hundred(self):
        meta = FakeMeta([item(f'm{i}', 'x', TODAY) for i in range(130)], {}, page=25)
        self.assertEqual(len(social_stats.media(meta)), 100)
        self.assertEqual(len(social_stats.media(FakeMeta([item('m', 'x', TODAY)], {}))), 1)

    def test_codes_are_read_from_the_caption(self):
        for caption, code in (('Every step: thelazychef.app/ig/12', '12'), ('THELAZYCHEF.APP/IG/Ab', 'ab'),
                              ('thelazychef.app/tiktok/3', None), ('', None), (None, None)):
            with self.subTest(caption=caption):
                self.assertEqual(social_stats.code_of(caption), code)

    def test_graph_errors_never_show_the_token(self):
        with mock.patch('services.social_stats.requests.get', side_effect=social_stats.requests.ConnectionError(
                'https://graph.facebook.com/v26.0/x?access_token=test-token')):
            with self.assertRaises(social_stats.StatsError) as raised:
                social_stats.graph_get('x', {})
        self.assertNotIn('test-token', str(raised.exception))

    # The daily job and the button

    def test_the_daily_job_needs_the_queue_token(self):
        client = app.test_client()
        self.assertEqual(client.post('/internal/tasks/social-stats').status_code, 401)
        self.log('5', TODAY)
        meta = FakeMeta([item('m5', 'thelazychef.app/ig/5', TODAY)], {'m5': NUMBERS})
        fetch = social_stats.fetch_instagram
        with mock.patch('routes.funnel_routes.tasks.verified', return_value=True), \
                mock.patch('routes.funnel_routes.social_stats.fetch_instagram', lambda: fetch(TODAY, meta)):
            answer = client.post('/internal/tasks/social-stats', headers={'Authorization': 'Bearer x'})
        self.assertEqual((answer.status_code, answer.get_json()['saved']), (200, 1))

    def test_the_daily_job_skips_without_a_token_and_says_when_instagram_fails(self):
        client = app.test_client()
        with mock.patch('routes.funnel_routes.tasks.verified', return_value=True):
            with mock.patch.dict(os.environ, {'INSTAGRAM_ACCESS_TOKEN': ''}):
                self.assertIn('skipped', client.post('/internal/tasks/social-stats').get_json())
            with mock.patch('routes.funnel_routes.social_stats.fetch_instagram',
                            side_effect=social_stats.StatsError('Invalid OAuth access token')):
                answer = client.post('/internal/tasks/social-stats')
        self.assertEqual((answer.status_code, answer.get_json()), (502, {'error': 'Invalid OAuth access token'}))

    def test_fetch_from_instagram_on_the_funnel_page(self):
        client = app.test_client()
        client.post('/login', data={'email': 'admin@test', 'password': 'pw'})
        with mock.patch('routes.funnel_routes.social_stats.fetch_instagram', return_value={
                'read': 2, 'matched': 1, 'posted': 0, 'saved': 1, 'unlogged': ['x'], 'errors': []}):
            page = client.post('/admin/funnel/fetch', follow_redirects=True).get_data(as_text=True)
        self.assertIn('Instagram: 2 posts read, 1 in the log, 1 numbers saved, 0 drafts marked posted. '
                      'Not in the log: 1.', page)
        self.assertIn('Fetch from Instagram', page)
        with mock.patch.dict(os.environ, {'INSTAGRAM_USER_ID': ''}):
            page = client.post('/admin/funnel/fetch', follow_redirects=True).get_data(as_text=True)
        self.assertIn('Instagram is not set up', page)

    def test_a_fetched_row_is_marked_in_the_post_log(self):
        post = self.log('5', TODAY)
        post.stats.append(SocialPostStat(day=0, views=7, source='instagram'))
        db.session.commit()
        client = app.test_client()
        client.post('/login', data={'email': 'admin@test', 'password': 'pw'})
        self.assertIn('instagram-5 · series · day 0 · fetched', client.get('/admin/funnel').get_data(as_text=True))


if __name__ == '__main__':
    unittest.main()
