"""Pages made of blocks (services/content, routes/content_routes.py, docs/CONTENT.md): checking a package, versions
and publishing, what each person sees, the home page and its fallback to Discover, and the sandboxed embeds."""
import json
import os
import sys
import unittest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

os.environ['DB_BACKEND'] = 'local'
os.environ['DATABASE_URL'] = 'sqlite://'
os.environ['STORAGE_BACKEND'] = 'local'
os.environ.setdefault('SECRET_KEY', 'test-secret')
os.environ.setdefault('GOOGLE_API_KEY', 'test-key')
os.environ.pop('K_SERVICE', None)

from app import app  # noqa: E402
from database.models import Page, PageEmbed, Recipe, User, UserQueue, db  # noqa: E402
from services.content.blocks import KINDS  # noqa: E402
from services.content.pages import (ContentError, check_blocks, default_home, find_page, live_text,  # noqa: E402
                                    publish, render_blocks, save_version, unpublish)
from services.recipe_v2.store import save_v2  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
with open(os.path.join(ROOT, 'data', 'pilot_v2', 'fasit', 'carbonara.json'), encoding='utf-8') as f:
    CARBONARA = json.load(f)


def guide(**kw):
    data = {'slug': 'cast-iron', 'kind': 'guide', 'lang': 'en', 'title': 'Cast iron',
            'blocks': [{'kind': 'text', 'settings': {'markdown': 'Heavy and **hot**.'}}]}
    data.update(kw)
    return data


class ContentTests(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        self.ctx = app.test_request_context()  # blocks build links with url_for
        self.ctx.push()
        db.drop_all()
        db.create_all()
        self.user = User(email='cook@test')
        self.user.set_password('pw')
        self.admin = User(email='admin@test', is_admin=True)
        self.admin.set_password('pw')
        db.session.add_all([self.user, self.admin])
        db.session.commit()
        self.client = app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def login(self, email):
        self.client.post('/login', data={'email': email, 'password': 'pw'})

    def recipe(self, title, image='dish.webp', status='approved'):
        r = Recipe(title=title, status=status, cuisine='Italian', difficulty='Simplistic')
        db.session.add(r)
        save_v2(r, CARBONARA)
        r.title, r.image_filename, r.prep_time_mins = title, image, 25
        db.session.commit()
        return r

    # --- checking ---

    def test_every_kind_is_documented_and_has_a_template(self):
        docs = open(os.path.join(ROOT, 'docs', 'CONTENT.md'), encoding='utf-8').read()
        for kind in KINDS:
            self.assertTrue(os.path.exists(os.path.join(ROOT, 'templates', 'blocks', f'{kind}.html')), kind)
            self.assertIn(f'`{kind}`', docs)

    def test_a_package_that_points_at_nothing_is_refused(self):
        errors = check_blocks([
            {'kind': 'recipes', 'settings': {'ids': [999]}},
            {'kind': 'recipes', 'settings': {'filter': {'time': '7'}}},
            {'kind': 'links', 'settings': {'items': [{'to': 'page:nowhere'}, {'to': 'admin_recipes_management'}]}},
            {'kind': 'interactive', 'settings': {'embed': 'nope', 'title': 'x'}},
            {'kind': 'video', 'settings': {}},
            {'kind': 'text', 'settings': {'markdown': 'x'}, 'audience': 'everyone'},
        ])
        text = '\n'.join(errors)
        for part in ('no approved recipe with id 999', 'filter time: "7"', 'no page "nowhere"',
                     'item 2: "to" must be', 'id of an uploaded interactive', 'Block 5: kind must be', 'audience must be'):
            self.assertIn(part, text)
        with self.assertRaises(ContentError):
            save_version(guide(slug='Not A Slug'))

    def test_the_default_home_is_valid(self):
        self.assertEqual(check_blocks(default_home()['blocks']), [])

    # --- versions and publishing ---

    def test_versions_and_publishing(self):
        v1 = save_version(guide())
        db.session.commit()
        page = find_page('cast-iron')
        self.assertIsNone(live_text(page))  # a draft is not shown
        publish(v1)
        v2 = save_version(guide(title='Cast iron pans'))
        db.session.commit()
        self.assertEqual((v2.version, live_text(page).version), (2, 1))  # v2 is a draft, v1 stays live
        publish(v2)
        self.assertEqual(live_text(page).title, 'Cast iron pans')
        # Publishing an old version again makes it the newest, and keeps the history
        again = publish(v1)
        db.session.commit()
        self.assertEqual((again.version, live_text(page).title, len(page.texts)), (3, 'Cast iron', 3))
        unpublish(page, 'en')
        self.assertIsNone(live_text(page))

    def test_another_language_falls_back_to_english(self):
        publish(save_version(guide()))
        db.session.commit()
        page = find_page('cast-iron')
        self.assertEqual(live_text(page, 'no').lang, 'en')
        publish(save_version(guide(lang='no', title='Støpejern')))
        self.assertEqual(live_text(page, 'no').title, 'Støpejern')

    # --- what each person sees ---

    def test_audience_and_empty_blocks(self):
        text = save_version(guide(blocks=[
            {'kind': 'text', 'settings': {'markdown': 'Hello <script>alert(1)</script>'}},
            {'kind': 'text', 'settings': {'markdown': 'Members'}, 'audience': 'signed_in'},
            {'kind': 'text', 'settings': {'markdown': 'Visitors'}, 'audience': 'signed_out'},
            {'kind': 'cook_next', 'settings': {}},
            {'kind': 'recipes', 'settings': {'sort': 'new'}},
        ]))
        anon = render_blocks(text, None, 'en')
        self.assertEqual([b['data']['html'] for b in anon], ['<p>Hello </p>', '<p>Visitors</p>'])  # the script is gone
        self.assertEqual(len(render_blocks(text, self.user, 'en')), 2)  # members' text; the queue and recipes are empty

    def test_recipe_rows_show_approved_recipes_with_a_picture(self):
        shown = self.recipe('Shown')
        self.recipe('No picture', image=None)
        draft = self.recipe('Draft', status='draft')
        text = save_version(guide(blocks=[{'kind': 'recipes', 'settings': {'title': 'New', 'more': True}},
                                          {'kind': 'recipes', 'settings': {'ids': [shown.id]}}]))
        rows = render_blocks(text, None, 'en')
        self.assertEqual([r.title for r in rows[0]['data']['recipes']], ['Shown'])
        self.assertEqual(rows[0]['data']['more'], '/recipes')
        self.assertEqual([r.title for r in rows[1]['data']['recipes']], ['Shown'])
        self.assertIn(f'no approved recipe with id {draft.id}', ' '.join(check_blocks([{'kind': 'recipes', 'settings': {'ids': [draft.id]}}])))

    def test_cook_next_and_links(self):
        r = self.recipe('Queued')
        db.session.add(UserQueue(user_id=self.user.id, recipe_id=r.id, position=1))
        publish(save_version(guide()))
        text = save_version(guide(slug='home-test', blocks=[
            {'kind': 'cook_next', 'settings': {'limit': 2}},
            {'kind': 'links', 'settings': {'items': [{'to': 'discover'}, {'to': 'page:cast-iron', 'text': 'Why it holds heat'}]}}]))
        db.session.commit()
        blocks = render_blocks(text, self.user, 'en')
        self.assertEqual([x.title for x in blocks[0]['data']['recipes']], ['Queued'])
        tiles = blocks[1]['data']['tiles']
        self.assertEqual([(t['title'], t['url']) for t in tiles], [('Discover', '/discover'), ('Cast iron', '/guides/cast-iron')])
        self.assertEqual(tiles[1]['text'], 'Why it holds heat')

    # --- the pages ---

    def test_home_is_discover_until_a_home_page_is_published(self):
        self.assertIn('What shall we cook?', self.client.get('/').get_data(as_text=True))
        self.assertEqual(self.client.get('/discover').status_code, 200)
        text = save_version(default_home())
        db.session.commit()
        self.assertIn('What shall we cook?', self.client.get('/').get_data(as_text=True))  # a draft: still Discover
        publish(text)
        db.session.commit()
        html = self.client.get('/').get_data(as_text=True)
        self.assertIn('What shall we cook tonight?', html)
        self.assertIn('data-continue', html)
        self.assertNotIn('Cook next</h2>', html)  # signed out

    def test_guides_are_hidden_until_published(self):
        text = save_version(guide())
        db.session.commit()
        self.assertEqual(self.client.get('/guides/cast-iron').status_code, 404)
        self.login('admin@test')
        self.assertIn('Preview of version 1', self.client.get(f'/admin/pages/text/{text.id}/preview').get_data(as_text=True))
        self.client.post(f'/admin/pages/text/{text.id}/publish')
        self.assertIn('Heavy and <strong>hot</strong>', self.client.get('/guides/cast-iron').get_data(as_text=True))

    def test_admin_import_and_edit(self):
        self.login('admin@test')
        resp = self.client.post('/admin/pages/import', data={'package': json.dumps(guide())})
        page = find_page('cast-iron')
        self.assertEqual(resp.headers['Location'], f'/admin/pages/{page.id}?lang=en')
        self.client.post(f'/admin/pages/{page.id}/save', data={'package': json.dumps(guide(title='Edited'))})
        self.client.post(f'/admin/pages/{page.id}/save', data={'package': json.dumps(guide(slug='other'))})  # refused
        db.session.expire_all()
        self.assertEqual([t.title for t in find_page('cast-iron').texts], ['Cast iron', 'Edited'])
        self.assertIsNone(find_page('other'))
        self.client.post('/admin/pages/home')
        self.assertIsNotNone(find_page('home'))
        self.assertEqual(self.client.get('/admin/pages').status_code, 200)
        self.assertEqual(self.client.get(f'/admin/pages/{page.id}').status_code, 200)

    def test_an_embed_is_sandboxed(self):
        self.login('admin@test')
        self.client.post('/admin/embeds', data={'title': 'Pan picker', 'html': '<!doctype html><p>Pick a pan</p>'})
        embed = db.session.execute(db.select(PageEmbed)).scalar_one()
        resp = self.client.get(f'/content/interactive/{embed.id}')
        self.assertIn('sandbox allow-scripts', resp.headers['Content-Security-Policy'])
        self.assertNotIn('allow-same-origin', resp.headers['Content-Security-Policy'])
        self.assertIn('lazyEmbed', resp.get_data(as_text=True))
        text = save_version(guide(blocks=[{'kind': 'interactive', 'settings': {'embed': embed.id, 'title': 'Pan picker'}}]))
        publish(text)
        db.session.commit()
        html = self.client.get('/guides/cast-iron').get_data(as_text=True)
        self.assertIn('sandbox="allow-scripts allow-popups allow-popups-to-escape-sandbox"', html)
        self.assertIn(f'/content/interactive/{embed.id}', html)


if __name__ == '__main__':
    unittest.main()
