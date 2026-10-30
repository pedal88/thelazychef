"""Pages made of blocks (services/content, routes/content_routes.py, docs/CONTENT.md): checking a package, versions
and publishing, what each person sees, the home page and its fallback to Discover, and the sandboxed embeds."""
import json
import os
import shutil
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
        for slug in ('cast-iron', 'pans', 'frying-pans', 'knives'):  # images the tests uploaded (local storage)
            shutil.rmtree(os.path.join(ROOT, 'static', 'content', slug), ignore_errors=True)

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
            {'kind': 'links', 'settings': {'style': 'carousel', 'items': [{'to': 'discover'}]}},
            {'kind': 'interactive', 'settings': {'embed': 'nope', 'title': 'x'}},
            {'kind': 'video', 'settings': {}},
            {'kind': 'text', 'settings': {'markdown': 'x'}, 'audience': 'everyone'},
        ])
        text = '\n'.join(errors)
        for part in ('no approved recipe with id 999', 'filter time: "7"', 'no page "nowhere"',
                     'item 2: "to" must be', 'style must be "tiles" or "cards"', 'id of an uploaded interactive',
                     'Block 6: kind must be', 'audience must be'):
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

    # --- images, compare and the task picker ---

    def upload(self, slug, *names):
        from routes._shared import get_storage
        from services.content import assets
        for name in names:
            assets.save(slug, name, b'<svg xmlns="http://www.w3.org/2000/svg"/>', get_storage())
        db.session.commit()

    def test_images_are_named_per_page(self):
        from services.content import assets
        errors = check_blocks([{'kind': 'text', 'settings': {'markdown': '![A pan](pan.svg)'}}], 'cast-iron')
        self.assertIn('no image "pan.svg" uploaded for "cast-iron"', ' '.join(errors))
        self.upload('cast-iron', 'pan.svg')
        first = assets.find('cast-iron', 'pan.svg').url
        self.assertTrue(first.startswith('/static/content/cast-iron/pan-'))
        text = save_version(guide(hero_image='pan.svg', blocks=[{'kind': 'text', 'settings': {'markdown': '![A pan](pan.svg)'}}]))
        self.assertIn(f'src="{first}"', render_blocks(text, None, 'en')[0]['data']['html'])
        # The same name again: a new address, the name stays
        from routes._shared import get_storage
        assets.save('cast-iron', 'pan.svg', b'<svg xmlns="http://www.w3.org/2000/svg" id="2"/>', get_storage())
        self.assertNotEqual(assets.find('cast-iron', 'pan.svg').url, first)
        with self.assertRaises(ValueError):
            assets.save('cast-iron', 'Bad Name.exe', b'x', get_storage())

    def test_compare_checks_every_score(self):
        settings = {'criteria': [{'key': 'heat', 'label': 'Holds heat'}, {'key': 'care', 'label': 'Easy care'}],
                    'items': [{'name': 'Cast iron', 'scores': {'heat': 5, 'care': 2}, 'image': 'cast-iron.svg'},
                              {'name': 'Non-stick', 'scores': {'heat': 6}}]}
        text = ' '.join(check_blocks([{'kind': 'compare', 'settings': settings}], 'pans'))
        self.assertIn('Non-stick: scores must give each of heat, care a whole number from 0 to 5', text)
        self.assertIn('Cast iron: image: no image "cast-iron.svg"', text)
        self.upload('pans', 'cast-iron.svg')
        settings['items'][1]['scores'] = {'heat': 2, 'care': 4}
        self.assertEqual(check_blocks([{'kind': 'compare', 'settings': settings}], 'pans'), [])
        page = save_version(guide(slug='pans', blocks=[{'kind': 'compare', 'settings': dict(settings, layout='table')}]))
        data = render_blocks(page, None, 'en')[0]['data']
        self.assertEqual([s['pct'] for s in data['rows'][0]['scores']], [100, 40])
        self.assertTrue(data['rows'][0]['image'].startswith('/static/content/pans/cast-iron-'))

    def test_task_picker(self):
        tasks = [{'label': 'Steak', 'answer': 'Cast iron', 'why': 'It holds heat.'},
                 {'label': 'Eggs', 'answer': 'Non-stick', 'why': 'They slide off.', 'colour': 'red'}]
        self.assertIn('task 2 takes label', ' '.join(check_blocks([{'kind': 'task_picker', 'settings': {'tasks': tasks}}])))
        del tasks[1]['colour']
        publish(save_version(guide(blocks=[{'kind': 'task_picker', 'settings': {'title': 'What are you cooking?', 'tasks': tasks}}])))
        db.session.commit()
        html = self.client.get('/guides/cast-iron').get_data(as_text=True)
        self.assertIn('name="tp-1" value="1" checked', html)
        self.assertIn('They slide off.', html)

    def _guide(self, slug, images):
        """A guide package in docs/content/<slug>: its images uploaded, the English and Norwegian versions checked
        and published"""
        folder = os.path.join(ROOT, 'docs', 'content', slug)
        self.assertEqual(sorted(n for n in os.listdir(folder) if n.endswith('.svg')), images)
        packages = {}
        for lang, name in (('en', f'{slug}.json'), ('no', f'{slug}.no.json')):
            with open(os.path.join(folder, name), encoding='utf-8') as f:
                packages[lang] = json.load(f)
            self.assertEqual((packages[lang]['slug'], packages[lang]['lang']), (slug, lang))
        self.assertIn(f'no image "{images[0]}"', ' '.join(check_blocks(packages['en']['blocks'], slug)))
        self.login('admin@test')
        with self.client as c:
            from io import BytesIO
            c.post('/admin/pages/images', data={'slug': slug, 'images': [
                (BytesIO(open(os.path.join(folder, n), 'rb').read()), n) for n in images]}, content_type='multipart/form-data')
        for package in packages.values():
            self.assertEqual(check_blocks(package['blocks'], slug), [])
            publish(save_version(package))
            db.session.commit()
        return (self.client.get(f'/guides/{slug}').get_data(as_text=True),
                self.client.get(f'/guides/{slug}?lang=no').get_data(as_text=True))

    def test_the_pilot_guide_is_a_valid_package(self):
        """docs/content/frying-pans: the example every new guide can start from"""
        html, norsk = self._guide('frying-pans', ['carbon-steel.svg', 'cast-iron.svg', 'ceramic.svg', 'cover.svg',
                                                  'non-stick.svg', 'stainless-steel.svg'])
        for part in ('Five pans, the same six questions', 'The heat store', 'What are you cooking?', 'Looking after them'):
            self.assertIn(part, html)
        self.assertIn('Hva skal du lage?', norsk)

    def test_the_knife_guide_is_a_valid_package(self):
        """docs/content/knives: two comparisons (must have, optional), then sharpening as text with its drawings"""
        html, norsk = self._guide('knives', ['boning-knife.svg', 'bread-knife.svg', 'chefs-knife.svg', 'cover.svg',
                                             'fillet-knife.svg', 'honing-steel.svg', 'petty-knife.svg', 'roll-sharpener.svg', 'santoku.svg',
                                             'whetstone.svg'])
        for part in ('Must have: the three you need', 'The workhorse', 'Optional: three to add', 'Keeping them sharp',
                     'German or Japanese?'):
            self.assertIn(part, html)
        for part in ('Må ha: de tre du trenger', 'Den du aldri sliper', 'Slik holder du dem skarpe', 'Tysk eller japansk?'):
            self.assertIn(part, norsk)

    def test_the_home_page_points_at_the_guides(self):
        """docs/content/home.json: a tile per published guide"""
        self._guide('frying-pans', sorted(n for n in os.listdir(os.path.join(ROOT, 'docs', 'content', 'frying-pans'))
                                          if n.endswith('.svg')))
        self._guide('knives', sorted(n for n in os.listdir(os.path.join(ROOT, 'docs', 'content', 'knives')) if n.endswith('.svg')))
        with open(os.path.join(ROOT, 'docs', 'content', 'home.json'), encoding='utf-8') as f:
            home = json.load(f)
        self.assertEqual(check_blocks(home['blocks'], home['slug']), [])
        publish(save_version(home))
        db.session.commit()
        html = self.client.get('/').get_data(as_text=True)
        self.assertIn('href="/guides/frying-pans"', html)
        self.assertIn('href="/guides/knives"', html)
        # as cards, each with its guide's cover drawing and a label
        self.assertEqual(html.count('class="gcard"'), 2)
        self.assertIn('Guide · 6 knives', html)
        self.assertRegex(html, r'class="gcard-img" src="[^"]*knives/cover')

    # --- the content API (routes/content_api_routes.py, scripts/content.py) ---

    def api(self, method, path, key='test-content-key', **kw):
        headers = {'Authorization': f'Bearer {key}'} if key else {}
        return self.client.open(f'/api/content{path}', method=method, headers=headers, **kw)

    def with_key(self):
        os.environ['CONTENT_API_KEY'] = 'test-content-key'
        self.addCleanup(os.environ.pop, 'CONTENT_API_KEY', None)

    def test_the_api_needs_its_key(self):
        os.environ.pop('CONTENT_API_KEY', None)
        self.assertEqual(self.api('GET', '/pages').status_code, 401)  # no key set: the API is off
        self.with_key()
        self.assertEqual(self.api('GET', '/pages', key=None).status_code, 401)
        self.assertEqual(self.api('POST', '/packages', key='wrong', json=guide()).status_code, 401)
        self.login('admin@test')  # an admin's login is not the key
        self.assertEqual(self.api('GET', '/pages', key=None).status_code, 401)
        self.assertEqual(self.api('GET', '/pages').status_code, 200)

    def test_the_api_makes_drafts_and_never_publishes(self):
        from io import BytesIO
        self.with_key()
        package = guide(hero_image='cast-iron.svg')
        resp = self.api('POST', '/packages', json=package)
        self.assertEqual(resp.status_code, 400)
        self.assertIn('no image "cast-iron.svg"', ' '.join(resp.get_json()['errors']))
        resp = self.api('POST', '/pages/cast-iron/images', content_type='multipart/form-data',
                        data={'images': [(BytesIO(b'<svg xmlns="http://www.w3.org/2000/svg"/>'), 'cast-iron.svg')]})
        self.assertEqual(list(resp.get_json()['saved']), ['cast-iron.svg'])
        resp = self.api('POST', '/packages', json=package)
        self.assertEqual(resp.status_code, 201)
        body = resp.get_json()
        self.assertEqual((body['version'], body['published']), (1, False))
        self.assertIn('/admin/pages/text/', body['preview'])
        self.assertEqual(self.client.get('/guides/cast-iron').status_code, 404)  # a draft until Pål publishes it
        self.assertEqual(self.api('GET', '/pages/cast-iron?live=1').status_code, 404)
        publish(find_page('cast-iron').texts[0])
        db.session.commit()
        self.api('POST', '/packages', json=dict(package, title='Cast iron, again'))
        got = self.api('GET', '/pages/cast-iron').get_json()
        self.assertEqual((got['version'], got['package']['title']), (2, 'Cast iron, again'))
        self.assertEqual(self.api('GET', '/pages/cast-iron?live=1').get_json()['version'], 1)
        self.assertIn('cast-iron.svg', got['images'])
        langs = self.api('GET', '/pages').get_json()['pages'][0]['langs']
        self.assertEqual([(v['version'], v['published']) for v in langs['en']], [(2, False), (1, True)])
        resp = self.api('POST', '/interactives', json={'title': 'Picker', 'html': '<p>Hi</p>'})
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(db.session.get(PageEmbed, resp.get_json()['id']).html, '<p>Hi</p>')

    def test_the_script_pushes_a_package_with_its_images(self):
        """scripts/content.py push: the images named in the package or its Markdown that lie next to it go first."""
        import tempfile
        from unittest import mock
        from scripts import content as script
        self.with_key()
        folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, folder)
        for name in ('cast-iron.svg', 'lid.svg'):
            with open(os.path.join(folder, name), 'w') as f:
                f.write('<svg xmlns="http://www.w3.org/2000/svg"/>')
        with open(os.path.join(folder, 'cast-iron.json'), 'w') as f:
            json.dump(guide(hero_image='cast-iron.svg', blocks=[
                {'kind': 'text', 'settings': {'markdown': 'Heavy.\n\n![A lid](lid.svg)'}}]), f)

        def request(method, url, headers, timeout, files=None, params=None, json=None):
            data = {'images': [(f, name) for _, (name, f) in files]} if files else None
            resp = self.client.open('/' + url.split('://', 1)[1].split('/', 1)[1], method=method, headers=headers,
                                    data=data, query_string=params, json=json)
            return mock.Mock(status_code=resp.status_code, json=resp.get_json)
        with mock.patch.object(script.requests, 'request', request), mock.patch('builtins.print'):
            script.push(os.path.join(folder, 'cast-iron.json'))
        text = find_page('cast-iron').texts[0]
        self.assertEqual((text.hero_image, text.published_at), ('cast-iron.svg', None))


if __name__ == '__main__':
    unittest.main()
