"""The video inbox: links saved from the phone, one row per video, nothing made and nothing written on a GET."""
import json
import os
import sys
import unittest
from types import SimpleNamespace
from unittest import mock

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

os.environ['DB_BACKEND'] = 'local'
os.environ['DATABASE_URL'] = 'sqlite://'
os.environ['STORAGE_BACKEND'] = 'local'
os.environ.setdefault('SECRET_KEY', 'test-secret')
os.environ.setdefault('GOOGLE_API_KEY', 'test-key')
os.environ.pop('K_SERVICE', None)

from app import app  # noqa: E402
from database.models import Recipe, User, VideoInbox, db  # noqa: E402
from services.recipe_v2 import inbox, tasks  # noqa: E402

TIKTOK = 'https://www.tiktok.com/@cook/video/123'


class KeyTests(unittest.TestCase):
    def test_every_link_to_one_video_has_one_key(self):
        for key, links in (
                ('tiktok:123', [TIKTOK, 'https://m.tiktok.com/v/x/video/123?_t=abc']),
                ('instagram:AbC-1', ['https://www.instagram.com/reel/AbC-1/?igsh=xyz', 'https://instagram.com/reels/AbC-1', 'https://www.instagram.com/p/AbC-1/']),
                ('youtube:dQw', ['https://www.youtube.com/watch?v=dQw&t=3', 'https://youtu.be/dQw?si=1', 'https://www.youtube.com/shorts/dQw']),
                ('vm.tiktok.com/ZNabc', ['https://vm.tiktok.com/ZNabc/'])):
            for link in links:
                with self.subTest(link=link):
                    self.assertEqual(inbox.video_key(link), key)

    def test_the_link_loses_its_tracking(self):
        self.assertEqual(inbox.clean_url('https://www.instagram.com/reel/AbC/?igsh=xyz#x'), 'https://www.instagram.com/reel/AbC/')
        self.assertEqual(inbox.clean_url('https://www.youtube.com/watch?v=dQw&si=1'), 'https://www.youtube.com/watch?v=dQw')

    def test_the_link_is_found_among_words(self):
        self.assertEqual(inbox.first_link('Look at this! https://vm.tiktok.com/ZNabc/. Great'), 'https://vm.tiktok.com/ZNabc/')
        self.assertIsNone(inbox.first_link('no link'))


class RouteTests(unittest.TestCase):
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
        with self.client.session_transaction() as s:
            s['_user_id'], s['_fresh'] = str(admin.id), True

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def _save(self, url=TIKTOK):
        self.client.get('/admin/inbox/add', query_string={'url': url})
        return self.client.post('/admin/inbox/add', data={'url': url}, headers={'Sec-Fetch-Site': 'same-origin'})

    def _count(self):
        return db.session.scalar(db.select(db.func.count()).select_from(VideoInbox))

    def test_the_get_writes_nothing_and_the_page_sends_itself(self):
        res = self.client.get('/admin/inbox/add', query_string={'url': f'Look {TIKTOK}?_t=1'})
        html = res.get_data(as_text=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn('.submit()', html)
        self.assertEqual(self._count(), 0)

    def test_a_link_can_be_pasted_when_the_page_gets_none(self):
        html = self.client.get('/admin/inbox/add').get_data(as_text=True)
        self.assertIn('name="url"', html)
        self.assertNotIn('.submit()', html)  # nothing to send yet
        self.assertIn('/admin/inbox/add', self.client.get('/admin/inbox').get_data(as_text=True))
        res = self.client.post('/admin/inbox/add', data={'url': f'Look at this! {TIKTOK}?_t=1'})
        self.assertEqual(res.status_code, 302)
        self.assertEqual(db.session.execute(db.select(VideoInbox)).scalar_one().url, TIKTOK)

    def test_a_post_from_another_site_saves_nothing(self):
        response = self.client.post('/admin/inbox/add', data={'url': TIKTOK}, headers={'Sec-Fetch-Site': 'cross-site'})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self._count(), 0)

    def test_only_video_links_are_saved(self):
        self.assertEqual(self.client.get('/admin/inbox/add', query_string={'url': 'https://example.com/a'}).status_code, 400)
        self._save('https://example.com/a')
        self.assertEqual(self._count(), 0)

    def test_saving_keeps_the_clean_link_and_makes_nothing(self):
        self.assertEqual(self._save('https://www.instagram.com/reel/AbC/?igsh=xyz').status_code, 302)
        row = db.session.execute(db.select(VideoInbox)).scalar_one()
        self.assertEqual((row.url, row.video_key, row.status), ('https://www.instagram.com/reel/AbC/', 'instagram:AbC', 'new'))
        self.assertEqual(db.session.scalar(db.select(db.func.count()).select_from(Recipe)), 0)
        self.assertIn('instagram.com/reel/AbC', self.client.get('/admin/inbox').get_data(as_text=True))

    def test_one_video_is_one_row_and_sharing_it_again_takes_it_back(self):
        self._save()
        self._save(TIKTOK + '?_t=other')
        row = db.session.execute(db.select(VideoInbox)).scalar_one()
        self.client.post(f'/admin/inbox/{row.id}/status', data={'status': 'discarded'})
        self.assertNotIn(TIKTOK, self.client.get('/admin/inbox').get_data(as_text=True))
        self.assertIn(TIKTOK, self.client.get('/admin/inbox?show=discarded').get_data(as_text=True))
        self._save()
        db.session.refresh(row)
        self.assertEqual(row.status, 'new')

    def _approved(self, title='Chicken Pad Thai'):
        recipe = Recipe(title=title, cuisine='', difficulty='', status='approved', schema_version=2)
        db.session.add(recipe)
        db.session.commit()
        return recipe

    def _row(self, url=TIKTOK):
        row = VideoInbox(url=url, video_key=inbox.video_key(url))
        db.session.add(row)
        db.session.commit()
        return row

    @staticmethod
    def _claude(answer, seen=None):
        def call(model, effort, messages, system=None, schema=None):
            if seen is not None:
                seen.append({'model': model, 'system': system, 'user': messages[0]['content'], 'schema': schema})
            return SimpleNamespace(content=[SimpleNamespace(type='text', text=json.dumps(answer))]), {'cost_usd': 0.001}
        return call

    ANSWER = {'is_recipe': True, 'dish_name': 'Lemon orzo', 'cuisine': 'Italian', 'main_protein': 'Chicken',
              'meal_types': ['Dinner'], 'similar': []}

    def test_a_video_is_looked_up_without_being_downloaded(self):
        recipe = self._approved()
        draft = Recipe(title='A draft', cuisine='', difficulty='', status='draft', schema_version=2)
        db.session.add(draft)
        row = self._row('https://vm.tiktok.com/ZNabc/')
        seen = []
        extract = lambda url: {'caption': 'Lemon orzo #dinner', 'title': 't', 'uploader': 'cook', 'duration': 61.5,  # noqa: E731
                               'webpage_url': TIKTOK + '?_t=1'}
        answer = dict(self.ANSWER, similar=[recipe.id, recipe.id, 99999, draft.id])
        inbox.look_up(row, extract=extract, call=self._claude(answer, seen))
        db.session.commit()

        self.assertEqual((row.dish_name, row.uploader, row.duration_s), ('Lemon orzo', 'cook', 61))
        self.assertEqual((row.video_key, row.webpage_url), ('tiktok:123', TIKTOK))  # the short link now has its video's key
        self.assertEqual(row.similar, [recipe.id])  # only recipes that exist and are approved, each once
        self.assertEqual(row.suggestions['cuisine'], 'Italian')
        self.assertIn('Chicken Pad Thai', seen[0]['system'])
        self.assertNotIn('A draft', seen[0]['system'])
        self.assertIn('Lemon orzo #dinner', seen[0]['user'])
        html = self.client.get('/admin/inbox').get_data(as_text=True)
        for text in ('Lemon orzo', 'Looks like:', 'Chicken Pad Thai', 'Italian · Chicken · Dinner', 'cook'):
            self.assertIn(text, html)

    def test_only_what_the_app_knows_goes_in_the_schema(self):
        from schemas.recipe_v2 import CUISINES

        props = inbox.schema()['properties']
        self.assertEqual(props['cuisine']['enum'], list(CUISINES))
        self.assertIn('Chicken', props['main_protein']['enum'])

    def test_a_short_link_to_a_video_already_in_the_inbox_goes_away(self):
        long_row = self._row()
        short = self._row('https://vm.tiktok.com/ZNabc/')
        kept = inbox.look_up(short, extract=lambda url: {'webpage_url': TIKTOK}, call=self._claude(self.ANSWER))
        db.session.commit()
        self.assertEqual(kept.id, long_row.id)
        self.assertEqual(self._count(), 1)

    def test_a_video_that_cannot_be_read_stays_and_calls_no_model(self):
        row = self._row()

        def blocked(url):
            raise ValueError('Failed to extract metadata: blocked')

        def no_call(*a, **k):
            raise AssertionError('no model call')
        inbox.look_up(row, extract=blocked, call=no_call)
        db.session.commit()
        self.assertEqual(row.meta_error, inbox.NO_DETAILS)
        html = self.client.get('/admin/inbox').get_data(as_text=True)
        self.assertIn('Look up', html)
        self.assertNotIn('Failed to extract', html)  # never the raw error

    def test_the_last_failure_is_noted_and_earlier_ones_try_again(self):
        row = self._row()
        with mock.patch.object(inbox, 'look_up', side_effect=RuntimeError('anthropic 529 raw')):
            with self.assertRaises(RuntimeError):
                tasks.run_inbox(row.id, attempt=0)
            self.assertTrue(tasks.run_inbox(row.id, attempt=tasks.MAX_ATTEMPTS - 1))
        db.session.refresh(row)
        self.assertTrue(row.meta_error)
        self.assertNotIn('529', row.meta_error)

    def test_saving_queues_the_look_up_and_a_failure_to_queue_keeps_the_video(self):
        with mock.patch.object(tasks, 'enqueue_inbox') as enqueue:
            self._save()
        enqueue.assert_called_once()
        with mock.patch.object(tasks, 'enqueue_inbox', side_effect=RuntimeError('queue')):
            self.assertEqual(self._save('https://www.instagram.com/reel/AbC/').status_code, 302)
        self.assertEqual(self._count(), 2)

    def test_the_task_needs_the_queue_token(self):
        row = self._row()
        self.assertEqual(self.client.post(f'/internal/tasks/video-inbox/{row.id}').status_code, 401)

    def test_a_video_made_into_a_recipe_is_marked(self):
        self._save()
        recipe = Recipe(title='x', cuisine='', difficulty='', status='draft', schema_version=2, source_type='video', source_input=TIKTOK + '?_t=1')
        db.session.add(recipe)
        db.session.commit()
        self.assertIn(f'Already made: recipe {recipe.id}', self.client.get('/admin/inbox').get_data(as_text=True))


if __name__ == '__main__':
    unittest.main()
