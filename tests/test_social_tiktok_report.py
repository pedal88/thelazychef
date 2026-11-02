"""The TikTok posts page for the phone and the weekly report (services/social_publish.py, services/social_report.py):
what waits on the page, its slides, marking a post up, and what the report is written from. Storage and Claude are
stood in for."""
import datetime
import io
import json
import os
import sys
import unittest
from types import SimpleNamespace
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
from database.models import ReferralVisit, SocialPost, SocialPostStat, SocialReport, User, db  # noqa: E402
from services import social_publish, social_report  # noqa: E402

KEY = 'test-content-key'
JPEG = b'\xff\xd8\xff\xe0' + b'x' * 50
SUNDAY = datetime.date(2026, 11, 8)
READING = {'headline': 'Laks slo kylling.', 'won': ['tiktok-5: 2000 visninger.'], 'lost': [], 'change': 'Test en ny krok.',
           'why': 'Se besøk per 1000.', 'caution': 'For få poster.'}


class FakeStorage:
    def __init__(self):
        self.files = {}

    def save(self, data, name, folder):
        self.files[(folder, name)] = data
        return f'https://storage.example/{folder}/{name}'

    def read(self, name, folder):
        return self.files[(folder, name)]


class Base(unittest.TestCase):
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
        self.client.post('/login', data={'email': 'admin@test', 'password': 'pw'})

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def post(self, platform='tiktok', code='5', status='draft', day=SUNDAY, **fields):
        post = SocialPost(platform=platform, code=code, format='series', title=f'Post {code}', status=status,
                          posted_on=day, **fields)
        db.session.add(post)
        db.session.commit()
        return post


class TikTokPageTests(Base):
    def test_the_batch_sends_a_posts_tiktok_slides_and_text_to_the_app(self):
        post = self.post()
        ig = self.post(platform='instagram')
        storage = FakeStorage()
        with mock.patch.dict(os.environ, {'CONTENT_API_KEY': KEY}), \
                mock.patch('routes.social_api_routes.get_storage', return_value=storage):
            response = app.test_client().post(
                '/api/social/slides/5', headers={'Authorization': f'Bearer {KEY}'}, content_type='multipart/form-data',
                data={'platform': 'tiktok', 'caption': 'The text /tiktok/5',
                      'slides': [(io.BytesIO(JPEG), "01.jpg"), (io.BytesIO(JPEG), "02.jpg")]})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(social_publish.slides_of(post)), 2)
        self.assertEqual(post.caption, 'The text /tiktok/5')
        self.assertTrue(all(folder == 'social/tiktok-5' for folder, _ in storage.files))
        self.assertIsNone(ig.slide_urls)  # Instagram's post is another post

    def test_the_page_lists_tiktoks_drafts_with_slides_only(self):
        self.post(code='5', slide_urls='https://s/a.jpg\nhttps://s/b.jpg', caption='Five words', hook='The hook')
        self.post(code='6')  # no slides yet
        self.post(code='7', status='posted', slide_urls='https://s/a.jpg')
        self.post(platform='instagram', code='8', slide_urls='https://s/a.jpg')
        html = self.client.get('/admin/funnel/tiktok').get_data(as_text=True)
        self.assertIn('tiktok-5', html)
        self.assertIn('value="The hook"', html)
        self.assertIn('Five words', html)
        self.assertIn('data-slides="[1, 2]"', html)
        for other in ('tiktok-6', 'tiktok-7', 'Post 8'):
            self.assertNotIn(other, html)
        self.assertEqual([p['post'].code for p in social_publish.queue()[0]['posts']], ['8'])  # Instagram's queue

    def test_a_slide_comes_from_the_site_itself_for_the_phone_to_save(self):
        storage = FakeStorage()
        post = self.post()
        with mock.patch('routes.funnel_routes.get_storage', return_value=storage):
            social_publish.save_slides(post, [JPEG, JPEG + b'2'], 'Text', storage)
            response = self.client.get(f'/admin/funnel/posts/{post.id}/slides/2.jpg')
            self.assertEqual((response.mimetype, response.data), ('image/jpeg', JPEG + b'2'))
            self.assertEqual(self.client.get(f'/admin/funnel/posts/{post.id}/slides/3.jpg').status_code, 404)

    def test_marking_it_up_keeps_the_sound_and_link_and_returns_to_the_page(self):
        post = self.post(slide_urls='https://s/a.jpg')
        response = self.client.post(f'/admin/funnel/posts/{post.id}/posted',
                                    data={'back': 'tiktok', 'sound': 'Static Dreams', 'url': 'https://tiktok.com/x'})
        self.assertEqual(response.location, '/admin/funnel/tiktok')
        self.assertEqual((post.status, post.sound, post.url, post.posted_on),
                         ('posted', 'Static Dreams', 'https://tiktok.com/x', datetime.date.today()))
        self.assertEqual(social_publish.tiktok_days(), [])


class ReportTests(Base):
    def claude(self, reading=READING):
        calls = []

        def call(model, effort, messages, system=None, schema=None):
            calls.append(SimpleNamespace(model=model, sent=json.loads(messages[0]['content']), system=system,
                                         schema=schema))
            return SimpleNamespace(content=[SimpleNamespace(type='text', text=json.dumps(reading))]), {'cost_usd': 0.01}
        return call, calls

    def week(self):
        salmon = self.post(code='5', status='posted', day=SUNDAY - datetime.timedelta(days=3), series='airfryer')
        salmon.stats.append(SocialPostStat(day=2, views=2000, saves=9))
        self.post(code='6', status='posted', day=SUNDAY - datetime.timedelta(days=1))  # no numbers yet
        self.post(code='7', status='draft')
        earlier = self.post(code='3', status='posted', day=SUNDAY - datetime.timedelta(days=10))
        earlier.stats.append(SocialPostStat(day=7, views=444))
        db.session.add(ReferralVisit(ref='tiktok-5', day=SUNDAY, count=3))
        db.session.commit()

    def test_the_facts_are_this_weeks_posts_with_last_weeks_totals(self):
        self.week()
        facts = social_report.facts(SUNDAY)
        self.assertEqual({p['ref'] for p in facts['posts']}, {'tiktok-5', 'tiktok-6'})  # no draft, no older post
        salmon = next(p for p in facts['posts'] if p['ref'] == 'tiktok-5')
        self.assertEqual((salmon['views'], salmon['saves'], salmon['visits'], salmon['visits_1000'], salmon['days_up']),
                         (2000, 9, 3, 1.5, 3))
        self.assertEqual((facts['this_week']['posts'], facts['this_week']['without_numbers']), (2, 1))
        self.assertEqual((facts['last_week']['posts'], facts['last_week']['views']), (1, 444))
        json.dumps(facts)  # it is stored as JSON

    def test_claude_reads_the_facts_and_the_report_is_kept_once_a_week(self):
        self.week()
        call, calls = self.claude()
        row = social_report.write_week(SUNDAY, call=call)
        self.assertEqual(row.report, READING)
        self.assertEqual(calls[0].sent['this_week']['posts'], 2)
        self.assertIn('Do not declare', calls[0].system)
        self.assertEqual(set(calls[0].schema['required']), set(READING))
        social_report.write_week(SUNDAY, call=call)  # a repeated job costs nothing
        self.assertEqual(len(calls), 1)
        newer, _ = self.claude({**READING, 'headline': 'Ny lesning.'})
        social_report.write_week(SUNDAY, replace=True, call=newer)
        reports = db.session.execute(db.select(SocialReport)).scalars().all()
        self.assertEqual([r.report['headline'] for r in reports], ['Ny lesning.'])

    def test_a_week_without_posts_makes_no_call(self):
        call, calls = self.claude()
        row = social_report.write_week(SUNDAY, call=call)
        self.assertEqual(calls, [])
        self.assertIn('Ingen poster', row.report['headline'])

    def test_the_page_shows_the_reading_and_the_numbers(self):
        self.assertIn('No report yet', self.client.get('/admin/funnel/report').get_data(as_text=True))
        self.week()
        call, _ = self.claude()
        social_report.write_week(SUNDAY, call=call)
        html = self.client.get('/admin/funnel/report').get_data(as_text=True)
        for text in ('Laks slo kylling.', 'Test en ny krok.', 'For få poster.', 'tiktok-5', '2000'):
            self.assertIn(text, html)
        self.assertIn('Weekly report', self.client.get('/admin/funnel').get_data(as_text=True))

    def test_the_job_needs_the_queues_token_and_a_failure_is_tried_again(self):
        self.assertEqual(app.test_client().post('/internal/tasks/social-report').status_code, 401)
        with mock.patch('services.recipe_v2.tasks.verified', return_value=True), \
                mock.patch.object(social_report, 'write_week', side_effect=RuntimeError('no credit')):
            response = app.test_client().post('/internal/tasks/social-report')
        self.assertEqual(response.status_code, 502)
        self.assertNotIn('no credit', response.get_data(as_text=True))

    def test_writing_it_by_hand_shows_a_friendly_message_when_it_fails(self):
        with mock.patch.object(social_report, 'write_week', side_effect=RuntimeError('no credit')):
            html = self.client.post('/admin/funnel/report/write', follow_redirects=True).get_data(as_text=True)
        self.assertIn('could not be written', html)
        self.assertNotIn('no credit', html)


if __name__ == '__main__':
    unittest.main()
