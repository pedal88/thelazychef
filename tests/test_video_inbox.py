"""The video inbox: links saved from the phone, one row per video, nothing made and nothing written on a GET."""
import io
import json
import os
import sys
import unittest
import zipfile
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
from services.recipe_v2 import inbox, sources, tasks  # noqa: E402

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


class ManyLinksTests(unittest.TestCase):
    def test_links_are_read_out_of_anything(self):
        for text, link in (('{"Link":"https:\\/\\/www.tiktokv.com\\/share\\/video\\/7\\/"}', 'https://www.tiktokv.com/share/video/7/'),
                           ('Date: 2026\nLink: https://www.tiktok.com/@a/video/1.', 'https://www.tiktok.com/@a/video/1'),
                           ('a,https://vm.tiktok.com/ZN1/,b', 'https://vm.tiktok.com/ZN1/'),
                           ('<a href="https://youtu.be/x">', 'https://youtu.be/x')):
            with self.subTest(text=text):
                self.assertEqual(inbox.links_in(text), [link])

    def test_a_share_link_is_the_same_video(self):
        self.assertEqual(inbox.video_key('https://www.tiktokv.com/share/video/123/'), inbox.video_key(TIKTOK))

    def test_a_zip_file_gives_the_text_in_it(self):
        data = io.BytesIO()
        with zipfile.ZipFile(data, 'w') as z:
            z.writestr('Activity/Favorite Videos.txt', TIKTOK)
            z.writestr('picture.png', 'https://www.tiktok.com/@a/video/9')
        self.assertEqual(inbox.text_of_upload(data.getvalue(), 'export.zip').strip(), TIKTOK)
        self.assertEqual(inbox.text_of_upload(b'plain \xff text', 'a.txt'), 'plain \ufffd text')


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

    def test_the_paste_button_sends_only_the_link_and_only_on_a_tap(self):
        html = self.client.get('/admin/inbox/add').get_data(as_text=True)
        self.assertIn('Paste and save', html)
        script = html[html.index('Reads the clipboard'):html.index('</script>', html.index('Reads the clipboard'))]
        self.assertLess(script.index("addEventListener('click'"), script.index('readText())'))
        self.assertIn('field.value = found[0]', script)
        # With a link the page sends itself, so it has no use for the clipboard
        self.assertNotIn('Paste and save', self.client.get('/admin/inbox/add', query_string={'url': TIKTOK}).get_data(as_text=True))

    def _many(self, n):
        return '\n'.join(f'https://www.tiktok.com/@a/video/{i}' for i in range(1, n + 1))

    def test_checking_says_what_is_there_and_saves_nothing(self):
        self._save()  # video 123
        recipe = Recipe(title='x', cuisine='', difficulty='', status='draft', schema_version=2, source_type='video',
                        source_input='https://www.tiktok.com/@c/video/456')
        db.session.add(recipe)
        db.session.commit()
        text = (f'{TIKTOK} https://www.tiktok.com/@a/video/456 https://www.tiktok.com/@a/video/7?_t=1 https://www.tiktok.com/@a/video/7 '
                'https://www.tiktok.com/@a https://example.com/x https://vm.tiktok.com/ZNa/ https://[bad')
        html = self.client.post('/admin/inbox/check', data={'text': text}).get_data(as_text=True)
        self.assertEqual(self._count(), 1)
        found = inbox.sort(text)
        self.assertEqual(found['new'], ['https://www.tiktok.com/@a/video/7', 'https://vm.tiktok.com/ZNa/'])
        self.assertEqual((found['known'], found['other']), (3, 3))  # in the inbox, made, there twice; a profile, a site, no address
        self.assertIn('2 new', html)
        self.assertIn('Save 2 videos', html)

    def test_a_file_can_be_checked(self):
        html = self.client.post('/admin/inbox/check', data={'file': (io.BytesIO(self._many(3).encode()), 'favorites.txt')},
                                content_type='multipart/form-data').get_data(as_text=True)
        self.assertIn('3 new', html)
        bad = self.client.post('/admin/inbox/check', data={'file': (io.BytesIO(b'nope'), 'a.zip')}, content_type='multipart/form-data')
        self.assertEqual(bad.status_code, 302)

    def test_a_long_paste_gets_past_the_form_limit(self):
        text = self._many(2) + ' ' + 'x' * 600_000
        self.assertIn('2 new', self.client.post('/admin/inbox/check', data={'text': text}).get_data(as_text=True))

    def test_saving_many_saves_all_once_and_queues_one_task(self):
        links = '\n'.join(inbox.sort(self._many(3))['new'])
        with mock.patch.object(tasks, 'enqueue_inbox_many', return_value=True) as queue:
            self.client.post('/admin/inbox/add-many', data={'links': links})
            queue.assert_called_once()
            self.assertEqual(len(queue.call_args.args[0]), 3)
            self.client.post('/admin/inbox/add-many', data={'links': links})  # the page sent twice
        self.assertEqual(self._count(), 3)
        self.assertEqual(queue.call_count, 1)

    def test_a_list_over_the_limit_says_so_and_saves_the_limit(self):
        with mock.patch.object(inbox, 'MAX_LINKS', 2):
            html = self.client.post('/admin/inbox/check', data={'text': self._many(3)}).get_data(as_text=True)
            self.assertIn('at most 2', html)
            with mock.patch.object(tasks, 'enqueue_inbox_many'):
                self.client.post('/admin/inbox/add-many', data={'links': self._many(3)})
        self.assertEqual(self._count(), 2)

    def test_a_discarded_video_stays_discarded_in_a_long_list(self):
        self._save()
        db.session.execute(db.update(VideoInbox).values(status='discarded'))
        db.session.commit()
        self.client.post('/admin/inbox/add-many', data={'links': TIKTOK})
        self.assertEqual(db.session.execute(db.select(VideoInbox.status)).scalar_one(), 'discarded')

    def test_saved_videos_survive_when_the_queue_fails(self):
        with mock.patch.object(tasks, 'enqueue_inbox_many', side_effect=RuntimeError('down')):
            self.assertEqual(self.client.post('/admin/inbox/add-many', data={'links': TIKTOK}).status_code, 302)
        self.assertEqual(self._count(), 1)
        self.assertEqual(len(inbox.waiting()), 1)
        html = self.client.get('/admin/inbox').get_data(as_text=True)
        self.assertIn('Queue them again', html)
        with mock.patch.object(tasks, 'enqueue_inbox_many', return_value=True) as queue:
            self.client.post('/admin/inbox/look-up-waiting')
        queue.assert_called_once()

    def test_one_look_up_that_cannot_be_queued_does_not_stop_the_rest(self):
        sent = []

        def queue(path, payload, at=None, session=None):
            if '/2' in path:
                raise RuntimeError('down')
            sent.append((path, at))
        with mock.patch.object(tasks, '_queue', queue), mock.patch.object(tasks, '_session'):
            self.assertEqual(tasks.run_inbox_many([1, 2, 3]), 2)
        self.assertEqual([p for p, _ in sent], ['/internal/tasks/video-inbox/1', '/internal/tasks/video-inbox/3'])
        self.assertEqual((sent[1][1] - sent[0][1]).total_seconds(), 2 * tasks.INBOX_SPACING)

    def test_the_task_that_queues_needs_the_queue_token(self):
        self.assertEqual(self.client.post('/internal/tasks/video-inbox-many', json={'ids': [1]}).status_code, 401)
        with mock.patch.object(tasks, 'verified', return_value=True), mock.patch.object(tasks, 'run_inbox_many', return_value=1) as run:
            self.assertEqual(self.client.post('/internal/tasks/video-inbox-many', json={'ids': [1]}, headers={'Authorization': 'Bearer x'}).status_code, 200)
        run.assert_called_once_with([1])

    def test_a_look_up_queued_twice_costs_once(self):
        row = VideoInbox(url=TIKTOK, video_key='tiktok:123', webpage_url=TIKTOK, dish_name='Soup', video_text='Soup')
        db.session.add(row)
        db.session.commit()
        with mock.patch.object(inbox, 'look_up') as look_up:
            tasks.run_inbox(row.id)
        look_up.assert_not_called()

    def test_a_row_looked_up_before_videos_were_read_can_be_read(self):
        row = VideoInbox(url=TIKTOK, video_key='tiktok:123', webpage_url=TIKTOK, dish_name='Soup', meta_error=inbox.NOT_READ)
        db.session.add(row)
        db.session.commit()
        self.assertIn('Look up', self.client.get('/admin/inbox').get_data(as_text=True))
        with mock.patch.object(tasks, 'enqueue_inbox', return_value=True):
            self.client.post(f'/admin/inbox/{row.id}/look-up')
        db.session.refresh(row)
        self.assertIsNone(row.meta_error)  # else the task would think it was done
        with mock.patch.object(inbox, 'look_up') as look_up:
            tasks.run_inbox(row.id)
        look_up.assert_called_once()

    def test_every_saved_video_is_in_the_list(self):  # Pål chooses the links, so nothing is sorted away by its caption
        db.session.add_all([VideoInbox(url=TIKTOK, video_key='a', dish_name='Soup', webpage_url=TIKTOK),
                            VideoInbox(url=TIKTOK, video_key='b', dish_name='Bowls', webpage_url=TIKTOK, suggestions={'is_recipe': False})])
        db.session.commit()
        html = self.client.get('/admin/inbox').get_data(as_text=True)
        self.assertIn('Soup', html)
        self.assertIn('Bowls', html)
        self.assertNotIn('look like a recipe', html)

    def test_a_link_can_be_pasted_when_the_page_gets_none(self):
        html = self.client.get('/admin/inbox/add').get_data(as_text=True)
        self.assertIn('name="url"', html)
        self.assertNotIn('save-video', html)  # nothing to send by itself yet
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

    ANSWER = {'dish_name': 'Lemon orzo', 'cuisine': 'Italian', 'main_protein': 'Chicken',
              'meal_types': ['Dinner'], 'similar': []}

    READ = staticmethod(lambda url: 'Lemon orzo\n- 200 g orzo')

    def test_a_video_is_looked_up_and_read(self):
        recipe = self._approved()
        draft = Recipe(title='A draft', cuisine='', difficulty='', status='draft', schema_version=2)
        db.session.add(draft)
        row = self._row('https://vm.tiktok.com/ZNabc/')
        seen = []
        extract = lambda url: {'caption': 'Lemon orzo #dinner', 'title': 't', 'uploader': 'cook', 'duration': 61.5,  # noqa: E731
                               'webpage_url': TIKTOK + '?_t=1'}
        answer = dict(self.ANSWER, similar=[recipe.id, recipe.id, 99999, draft.id])
        inbox.look_up(row, extract=extract, call=self._claude(answer, seen), read=self.READ)
        db.session.commit()

        self.assertEqual((row.dish_name, row.uploader, row.duration_s), ('Lemon orzo', 'cook', 61))
        self.assertEqual((row.video_key, row.webpage_url), ('tiktok:123', TIKTOK))  # the short link now has its video's key
        self.assertEqual(row.similar, [recipe.id])  # only recipes that exist and are approved, each once
        self.assertEqual(row.suggestions['cuisine'], 'Italian')
        self.assertIn('Chicken Pad Thai', seen[0]['system'])
        self.assertNotIn('A draft', seen[0]['system'])
        self.assertIn('Lemon orzo #dinner', seen[0]['user'])
        self.assertIn('200 g orzo', seen[0]['user'])
        self.assertEqual(row.video_text, 'Lemon orzo\n- 200 g orzo')
        html = self.client.get('/admin/inbox').get_data(as_text=True)
        for text in ('Lemon orzo', 'Looks like:', 'Chicken Pad Thai', 'Italian · Chicken · Dinner', 'cook', 'What the video shows'):
            self.assertIn(text, html)

    def test_the_recipe_is_made_from_what_the_inbox_read(self):
        self._row().video_text = 'Read once'
        db.session.commit()
        self.assertEqual(inbox.written_down(TIKTOK + '?_t=1'), 'Read once')
        self.assertIsNone(inbox.written_down('https://www.tiktok.com/@other/video/999'))

    def test_a_video_that_was_not_read_still_gets_its_details(self):
        extract = lambda url: {'caption': 'Bowls', 'webpage_url': TIKTOK}  # noqa: E731

        def fails(url):
            raise RuntimeError('gemini 503 raw')

        def no_recipe(url):
            raise sources.NoRecipeInVideo('none')

        def not_called(url):
            raise AssertionError('a long video is not read')
        for read, duration, message in ((fails, 40, inbox.NOT_READ), (no_recipe, 40, inbox.NO_RECIPE_SHOWN),
                                        (not_called, inbox.READ_MAX_SECONDS + 1, inbox.TOO_LONG)):
            with self.subTest(message=message):
                row = VideoInbox(url=TIKTOK, video_key=f'k{duration}{message[:5]}')
                db.session.add(row)
                db.session.flush()
                inbox.look_up(row, extract=lambda url: dict(extract(url), duration=duration), call=self._claude(self.ANSWER), read=read)
                self.assertEqual(row.meta_error, message)
                self.assertEqual(row.dish_name, 'Lemon orzo')
                self.assertIsNone(row.video_text)
                db.session.delete(row)
                db.session.flush()

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

    def test_chosen_videos_go_to_the_batch_page_which_shows_the_cost_first(self):
        chosen, other = self._row(), self._row('https://www.instagram.com/reel/AbC/')
        chosen.webpage_url = TIKTOK + '/clean'
        db.session.commit()
        self.assertIn(f'name="inbox" value="{chosen.id}"', self.client.get('/admin/inbox').get_data(as_text=True))
        with mock.patch.object(tasks, 'enqueue') as enqueue:
            res = self.client.post('/new-recipe/v2/batch', data={'inbox': [str(chosen.id)]})
            html = res.get_data(as_text=True)
            self.assertEqual(res.status_code, 200)
            self.assertIn('Make 1 recipe', html)
            self.assertIn('USD', html)
            self.assertIn(TIKTOK + '/clean', html)
            self.assertNotIn(other.url, html)
            enqueue.assert_not_called()  # nothing is made before the second step
            self.assertEqual(self.client.post('/new-recipe/v2/batch', data={'lines': TIKTOK + '/clean', 'action': 'make'}).status_code, 302)
        recipe = db.session.execute(db.select(Recipe)).scalar_one()
        self.assertEqual((recipe.source_type, recipe.status, recipe.source_input), ('video', 'generating', TIKTOK + '/clean'))
        self.assertEqual(enqueue.call_args[0][1:3], ('video', TIKTOK + '/clean'))

    def test_a_video_already_made_cannot_be_ticked(self):
        row = self._row()
        db.session.add(Recipe(title='x', cuisine='', difficulty='', status='draft', schema_version=2, source_type='video', source_input=TIKTOK))
        db.session.commit()
        self.assertNotIn(f'name="inbox" value="{row.id}"', self.client.get('/admin/inbox').get_data(as_text=True))

    def test_a_video_made_into_a_recipe_is_marked(self):
        self._save()
        recipe = Recipe(title='x', cuisine='', difficulty='', status='draft', schema_version=2, source_type='video', source_input=TIKTOK + '?_t=1')
        db.session.add(recipe)
        db.session.commit()
        self.assertIn(f'Already made: recipe {recipe.id}', self.client.get('/admin/inbox').get_data(as_text=True))


if __name__ == '__main__':
    unittest.main()
