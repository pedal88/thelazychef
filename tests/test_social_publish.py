"""The Instagram queue (services/social_publish.py): slides and text from the batch, approving with a time, a task that
publishes a carousel, cancelling, never twice, and a failure shown in the queue. Meta and the queue are stood in for."""
import datetime
import io
import os
import sys
import unittest
from unittest import mock

from PIL import Image

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(ROOT)

os.environ['DB_BACKEND'] = 'local'
os.environ['DATABASE_URL'] = 'sqlite://'
os.environ['STORAGE_BACKEND'] = 'local'
os.environ.setdefault('SECRET_KEY', 'test-secret')
os.environ.setdefault('GOOGLE_API_KEY', 'test-key')
os.environ.pop('K_SERVICE', None)

from app import app  # noqa: E402
from database.models import SocialPost, User, db  # noqa: E402
from scripts.social_batch import jpegs  # noqa: E402
from services import social_publish  # noqa: E402
from services.social_stats import StatsError  # noqa: E402

KEY = 'test-content-key'
NOW = datetime.datetime(2026, 11, 3, 9, 0)  # 10:00 in Oslo
IG = {'INSTAGRAM_ACCESS_TOKEN': 'test-token', 'INSTAGRAM_USER_ID': '178414', 'CONTENT_API_KEY': KEY}
JPEG = b'\xff\xd8\xff\xe0' + b'x' * 50
URLS = 'https://storage.example/1.jpg\nhttps://storage.example/2.jpg'


class FakeMeta:
    """What a publish asks Meta, with its answers; fail names a path to answer with an error."""

    def __init__(self, media=(), status='FINISHED', fail=None, used=0):
        self.media, self.status, self.fail, self.used = list(media), status, fail, used
        self.sent, self.made = [], 0

    def get(self, path, params):
        if path.endswith('/media'):
            return {'data': self.media}
        if path.endswith('/content_publishing_limit'):
            return {'data': [{'config': {'quota_total': 50}, 'quota_usage': self.used}]}
        if 'status_code' in params.get('fields', ''):
            return {'status_code': self.status}
        return {'permalink': f'https://www.instagram.com/p/{path}/'}

    def send(self, path, params):
        self.sent.append((path, params))
        if self.fail and path.endswith(self.fail):
            raise StatsError('(#36003) The image is not on a public address')
        self.made += 1
        return {'id': f'c{self.made}'}


class QueueTests(unittest.TestCase):
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
        self.client = app.test_client()
        self.env = mock.patch.dict(os.environ, IG)
        self.env.start()
        # Slides to memory, not to static/
        self.storage = mock.patch('routes.social_api_routes.get_storage', return_value=mock.Mock(
            save=lambda data, name, folder: f'https://storage.example/{folder}/{name}'))
        self.storage.start()

    def tearDown(self):
        self.storage.stop()
        self.env.stop()
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def post(self, code='5', status='draft', urls=URLS, caption='Dinner. thelazychef.app/ig/5', **fields):
        post = SocialPost(platform='instagram', code=code, format='series', title=f'Post {code}', caption=caption,
                          posted_on=datetime.date(2026, 11, 3), status=status, slide_urls=urls, **fields)
        db.session.add(post)
        db.session.commit()
        return post

    def login(self):
        self.client.post('/login', data={'email': 'admin@test', 'password': 'pw'})

    # Slides from the batch

    def upload(self, code, *slides, caption='Text'):
        return self.client.post(f'/api/social/slides/{code}', headers={'Authorization': f'Bearer {KEY}'},
                                data={'caption': caption, 'slides': [(io.BytesIO(s), f'{i}.jpg')
                                                                     for i, s in enumerate(slides)]},
                                content_type='multipart/form-data')

    def test_the_slides_and_text_come_to_a_draft(self):
        self.assertEqual(self.client.post('/api/social/slides/5').status_code, 401)
        self.assertEqual(self.upload('5', JPEG, JPEG).status_code, 404)
        post = self.post(urls=None, caption=None)
        answer = self.upload('5', JPEG + b'1', JPEG + b'2', caption='Dinner in one line')
        self.assertEqual(answer.get_json(), {'code': '5', 'slides': 2})
        self.assertEqual(post.caption, 'Dinner in one line')
        first, second = social_publish.slides_of(post)
        self.assertIn('social/instagram-5/01-', first)
        self.assertIn('social/instagram-5/02-', second)
        self.assertTrue(first.endswith('.jpg'))

    def test_wrong_slides_are_refused_and_a_scheduled_post_is_left_alone(self):
        self.post(urls=None)
        for slides, message in (((JPEG,), '2 to 20 slides'), ((JPEG, b'not a jpeg'), 'slide 2 is not a JPEG'),
                                ((JPEG,) * 21, 'not 21')):
            with self.subTest(message=message):
                answer = self.upload('5', *slides)
                self.assertEqual(answer.status_code, 400)
                self.assertIn(message, answer.get_json()['error'])
        self.post(code='6', status='scheduled')
        self.assertEqual(self.upload('6', JPEG, JPEG).status_code, 400)

    def test_the_batch_makes_jpegs_in_order(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as folder:
            for name, colour in (('02.png', 'red'), ('01.png', 'blue')):
                Image.new('RGBA', (108, 135), colour).save(Path(folder) / name)
            first, second = jpegs(Path(folder))
        self.assertEqual(first[:3], b'\xff\xd8\xff')
        pixel = Image.open(io.BytesIO(first)).getpixel((5, 5))
        self.assertGreater(pixel[2], pixel[0])  # 01 is the blue one
        self.assertEqual(Image.open(io.BytesIO(second)).size, (108, 135))

    # The page and approving

    def test_the_queue_offers_the_days_posts_at_good_times(self):
        self.post('5')
        self.post('6')
        self.post('7', urls=None)  # no slides yet
        self.post('8', status='posted')
        [day] = social_publish.queue()
        self.assertEqual([(r['post'].code, r['when']) for r in day['posts']],
                         [('5', '2026-11-03T11:00'), ('6', '2026-11-03T18:00')])
        self.assertEqual(self.client.get('/admin/funnel/queue').status_code, 302)
        self.login()
        html = self.client.get('/admin/funnel/queue').get_data(as_text=True)
        self.assertIn('https://storage.example/2.jpg', html)
        self.assertIn('name="caption-1"', html)
        self.assertIn('Publishing is not set up here', html)

    def test_a_series_that_goes_up_by_hand_is_shown_but_cannot_be_approved(self):
        hand = self.post('5', series='whole')
        other = self.post('6', series='got')
        self.assertEqual([r['by_hand'] for r in social_publish.queue()[0]['posts']], [True, False])
        self.login()
        html = self.client.get('/admin/funnel/queue').get_data(as_text=True)
        self.assertIn('Post by hand', html)
        self.assertNotIn(f'name="approve-{hand.id}"', html)
        self.assertIn(f'name="approve-{other.id}"', html)
        self.assertIn(f'name="caption-{hand.id}"', html)  # its words to copy
        when = datetime.datetime(2030, 1, 1, 12)
        self.assertEqual(social_publish.schedule(hand, when, None), 'instagram-5 goes up by hand')
        self.assertEqual(hand.status, 'draft')
        self.client.post('/admin/funnel/queue/approve', data={f'approve-{hand.id}': '1', f'when-{hand.id}': '2030-01-01T12:00'})
        self.assertEqual(hand.status, 'draft')

    def test_approving_schedules_the_ticked_posts_in_oslo_time(self):
        a, b = self.post('5'), self.post('6')
        self.login()
        with mock.patch('services.social_publish.tasks._queue') as queued, \
                mock.patch('services.social_publish.utcnow', return_value=NOW):
            page = self.client.post('/admin/funnel/queue/approve', follow_redirects=True, data={
                f'approve-{a.id}': '1', f'when-{a.id}': '2026-11-03T18:30', f'caption-{a.id}': ' New text ',
                f'when-{b.id}': '2026-11-03T11:00', f'caption-{b.id}': 'Not this one'}).get_data(as_text=True)
        self.assertIn('1 post scheduled.', page)
        self.assertEqual((a.status, a.scheduled_at, a.caption),
                         ('scheduled', datetime.datetime(2026, 11, 3, 17, 30), 'New text'))
        self.assertEqual((b.status, b.scheduled_at), ('draft', None))
        queued.assert_called_once_with(f'/internal/tasks/social-publish/{a.id}', {},
                                       at=datetime.datetime(2026, 11, 3, 17, 30))

    def test_a_time_that_has_passed_or_a_queue_that_fails_schedules_nothing(self):
        post = self.post()
        when = NOW + datetime.timedelta(hours=1)
        self.assertIn('the time has passed', social_publish.schedule(post, NOW, 'x', now=NOW))
        self.assertIn('give a time', social_publish.schedule(post, None, 'x', now=NOW))
        self.assertIsNone(social_publish.parse_when('tomorrow'))
        self.assertEqual(post.status, 'draft')
        with mock.patch('services.social_publish.tasks._queue', side_effect=RuntimeError('no')):
            self.assertIn('did not take it', social_publish.schedule(post, when, 'x', now=NOW))
        self.assertEqual((post.status, post.scheduled_at), ('draft', None))

    def test_cancel_goes_back_to_draft_and_the_task_does_nothing(self):
        post = self.post(status='scheduled', scheduled_at=NOW)
        self.login()
        self.client.post(f'/admin/funnel/queue/{post.id}/cancel')
        self.assertEqual((post.status, post.scheduled_at), ('draft', None))
        meta = FakeMeta()
        self.assertEqual(social_publish.publish(post, meta.get, meta.send, now=NOW), 'not scheduled')
        self.assertEqual(meta.sent, [])

    # Publishing

    def test_a_carousel_is_published_with_the_ai_label(self):
        post = self.post(status='scheduled', scheduled_at=NOW)
        meta = FakeMeta()
        self.assertEqual(social_publish.publish(post, meta.get, meta.send, wait=lambda s: None, now=NOW), 'posted')
        self.assertEqual(meta.sent, [
            ('178414/media', {'image_url': 'https://storage.example/1.jpg', 'is_carousel_item': 'true'}),
            ('178414/media', {'image_url': 'https://storage.example/2.jpg', 'is_carousel_item': 'true'}),
            ('178414/media', {'media_type': 'CAROUSEL', 'children': 'c1,c2', 'caption': 'Dinner. thelazychef.app/ig/5',
                              'is_ai_generated': 'true'}),
            ('178414/media_publish', {'creation_id': 'c3'})])
        self.assertEqual((post.status, post.media_id, post.url, post.posted_on, post.publish_error),
                         ('posted', 'c4', 'https://www.instagram.com/p/c4/', NOW.date(), None))

    def test_a_post_never_goes_up_twice(self):
        post = self.post(status='scheduled', scheduled_at=NOW)
        meta = FakeMeta(media=[{'id': 'm9', 'caption': 'Dinner. thelazychef.app/ig/5', 'permalink': 'https://i/p/m9'}])
        self.assertEqual(social_publish.publish(post, meta.get, meta.send, now=NOW), 'already up')
        self.assertEqual(meta.sent, [])
        self.assertEqual((post.status, post.media_id, post.url), ('posted', 'm9', 'https://i/p/m9'))

    def test_a_task_for_an_older_time_does_nothing(self):
        post = self.post(status='scheduled', scheduled_at=NOW + datetime.timedelta(hours=2))
        meta = FakeMeta()
        self.assertEqual(social_publish.publish(post, meta.get, meta.send, now=NOW), 'not yet')
        self.assertEqual((post.status, meta.sent), ('scheduled', []))

    def test_a_failure_goes_back_to_draft_with_the_reason(self):
        post = self.post(status='scheduled', scheduled_at=NOW)
        meta = FakeMeta(fail='media_publish')
        self.assertEqual(social_publish.publish(post, meta.get, meta.send, wait=lambda s: None, now=NOW), 'failed')
        self.assertEqual((post.status, post.scheduled_at), ('draft', None))
        self.assertIn('not on a public address', post.publish_error)
        self.login()
        self.assertIn('The last try failed', self.client.get('/admin/funnel/queue').get_data(as_text=True))

    def test_instagrams_limit_and_a_container_that_fails_stop_it(self):
        post = self.post(status='scheduled', scheduled_at=NOW)
        meta = FakeMeta(used=50)
        self.assertEqual(social_publish.publish(post, meta.get, meta.send, now=NOW), 'failed')
        self.assertIn('limit of 50', post.publish_error)
        self.assertEqual(meta.sent, [])
        post.status = 'scheduled'
        meta = FakeMeta(status='ERROR')
        self.assertEqual(social_publish.publish(post, meta.get, meta.send, now=NOW), 'failed')
        self.assertIn('could not read the post', post.publish_error)

    def test_the_task_needs_the_queue_token_and_says_what_it_did(self):
        post = self.post(status='scheduled', scheduled_at=NOW)
        url = f'/internal/tasks/social-publish/{post.id}'
        self.assertEqual(self.client.post(url).status_code, 401)
        with mock.patch('routes.funnel_routes.tasks.verified', return_value=True), \
                mock.patch('routes.funnel_routes.social_publish.publish', return_value='posted') as published:
            self.assertEqual(self.client.post(url).get_json(), {'result': 'posted'})
            self.assertEqual(self.client.post('/internal/tasks/social-publish/999').get_json(),
                             {'result': 'no such post'})
            with mock.patch.dict(os.environ, {'INSTAGRAM_ACCESS_TOKEN': ''}):
                self.assertEqual(self.client.post(url).get_json(), {'result': 'Instagram is not set up'})
        published.assert_called_once()

    def test_the_daily_fetch_marks_a_scheduled_post_that_is_up(self):
        from services import social_stats
        post = self.post(status='scheduled', scheduled_at=NOW)
        item = {'id': 'm5', 'caption': 'thelazychef.app/ig/5', 'permalink': 'https://i/p/m5',
                'timestamp': '2026-11-03T09:17:36+0000'}
        get = mock.Mock(side_effect=lambda path, params: {'data': [item], 'paging': {}} if path.endswith('/media')
                        else {'data': []})
        social_stats.fetch_instagram(datetime.date(2026, 11, 3), get)
        self.assertEqual(post.status, 'posted')


if __name__ == '__main__':
    unittest.main()
