"""Reading a recipe from a link: schema.org JSON-LD first, then the page text, and the refusals.

No network: pages are stand-ins.
"""
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
os.environ.pop('TASKS_QUEUE', None)

from app import app  # noqa: E402
from database.models import Recipe, User, db  # noqa: E402
from routes.recipe_v2_routes import kind_of  # noqa: E402
from services.recipe_v2 import sources, tasks  # noqa: E402
from services.recipe_v2.sources import SourceError, fetch_recipe_text, jsonld_text  # noqa: E402

RECIPE = {
    '@context': 'https://schema.org',
    '@graph': [
        {'@type': 'WebPage', 'name': 'Blog'},
        {'@type': 'Recipe', 'name': 'Thai Red Curry', 'recipeYield': ['4', '4 servings'],
         'recipeIngredient': ['600 g chicken thighs', '3 tbsp red curry paste', '400 ml coconut milk'],
         'recipeInstructions': [
             {'@type': 'HowToSection', 'name': 'Curry', 'itemListElement': [
                 {'@type': 'HowToStep', 'text': 'Fry the paste in the coconut cream.'},
                 {'@type': 'HowToStep', 'text': 'Add the chicken &amp; simmer.'}]},
             'Serve with rice.']},
    ],
}
PAGE = ('<html><head><script type="application/ld+json">' + json.dumps(RECIPE) +
        '</script></head><body><p>A long story about my grandmother.</p></body></html>')


def response(status=200, body='', location=None):
    return SimpleNamespace(status_code=status, content=body.encode(), headers={'Location': location} if location else {})


def public(url):
    return 'internal' not in url


class SourceTests(unittest.TestCase):
    def test_json_ld_becomes_recipe_text(self):
        text = jsonld_text(RECIPE['@graph'][1])
        self.assertTrue(text.startswith('Thai Red Curry\nServings: 4, 4 servings'))
        self.assertIn('- 3 tbsp red curry paste', text)
        self.assertIn('Curry:\n1. Fry the paste in the coconut cream.\n2. Add the chicken & simmer.\n3. Serve with rice.', text)

    def test_a_page_with_json_ld_gives_the_recipe_without_the_story(self):
        text, how = fetch_recipe_text('https://blog.example/curry', get=lambda *a, **k: response(body=PAGE), public=public)
        self.assertEqual(how, 'jsonld')
        self.assertNotIn('grandmother', text)

    def test_without_json_ld_the_page_text_is_used(self):
        body = '<html><body><nav>menu</nav><article>' + 'Mix and bake. ' * 30 + '</article></body></html>'
        text, how = fetch_recipe_text('https://blog.example/x', get=lambda *a, **k: response(body=body), public=public)
        self.assertEqual(how, 'page')
        self.assertNotIn('menu', text)

    def test_blocked_missing_and_video_links_give_a_clear_message(self):
        cases = [
            ('https://blocked.example/x', response(403), 'blocks automatic reading'),
            ('https://gone.example/x', response(404), '(404)'),
            ('https://empty.example/x', response(body='<html><body>Hi</body></html>'), 'no recipe'),
        ]
        for url, res, words in cases:
            with self.subTest(url), self.assertRaises(SourceError) as ctx:
                fetch_recipe_text(url, get=lambda *a, **k: res, public=public)
            self.assertIn(words, str(ctx.exception))
        with self.assertRaises(SourceError):
            fetch_recipe_text('https://www.tiktok.com/@chef/video/1', get=lambda *a, **k: response(body=PAGE), public=public)

    def test_internal_addresses_are_refused_also_after_a_redirect(self):
        calls = []

        def get(url, **kwargs):
            calls.append(url)
            return response(302, location='http://internal.example/computeMetadata')

        with self.assertRaises(SourceError):
            fetch_recipe_text('https://blog.example/curry', get=get, public=public)
        self.assertEqual(calls, ['https://blog.example/curry'])  # the internal target is never fetched
        for url in ('http://169.254.169.254/computeMetadata/v1/', 'http://localhost:8000/', 'ftp://blog.example/x'):
            self.assertFalse(sources._public(url), url)

    def test_links_are_their_own_kind(self):
        self.assertEqual(kind_of('https://www.recipetineats.com/thai-red-curry-with-chicken/'), 'web')
        self.assertEqual(kind_of('Thai red curry, see https://x.example'), 'idea')


class WebRecipeTests(unittest.TestCase):
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

    def test_a_video_link_starts_a_video_recipe(self):
        self.assertEqual(kind_of('https://www.tiktok.com/@cook/video/123'), 'video')
        with mock.patch.object(tasks, 'enqueue') as enqueue:
            res = self.client.post('/new-recipe/v2', data={'source': 'https://www.instagram.com/reel/abc/'})
        self.assertEqual(res.status_code, 302)
        recipe = db.session.execute(db.select(Recipe)).scalar_one()
        self.assertEqual((recipe.source_type, recipe.status), ('video', 'generating'))
        self.assertEqual(enqueue.call_args[0][1:3], ('video', 'https://www.instagram.com/reel/abc/'))

    def test_the_video_is_watched_and_its_text_goes_into_round_1(self):
        from services.recipe_v2 import claude, generate

        seen, cleaned = [], []

        def call(model, effort, messages, system=None, schema=None):
            seen.append(messages[0]['content'])
            raise RuntimeError('stop after round 1')

        download = lambda url: {'video_path': '/tmp/v.mp4', 'caption': 'Smash burgers #dinner'}  # noqa: E731
        watch = lambda path, caption: f'Smash burgers\n- 500 g ground beef\n(caption: {caption})'  # noqa: E731
        real = sources.fetch_video_text
        with mock.patch('services.recipe_v2.sources.fetch_video_text', lambda url: real(url, download=download, watch=watch)), \
                mock.patch('services.social_media_service.SocialMediaExtractor.cleanup', lambda *a: cleaned.append(a)), \
                mock.patch.object(claude, 'call', call), self.assertRaises(RuntimeError):
            generate.create_recipe('video', 'https://www.tiktok.com/@cook/video/123')
        self.assertIn('a cooking video', seen[0])
        self.assertIn('500 g ground beef', seen[0])
        self.assertIn('Smash burgers #dinner', seen[0])
        self.assertEqual(cleaned, [('/tmp/v.mp4', None)])  # the download is removed

    def test_a_video_that_cannot_be_had_is_a_source_error(self):
        def gone(url):
            raise ValueError('Failed to download video: private')
        with mock.patch('services.social_media_service.SocialMediaExtractor.cleanup'):
            with self.assertRaises(SourceError):
                sources.fetch_video_text('https://www.tiktok.com/@cook/video/1', download=gone)
            with self.assertRaises(SourceError):  # nothing could be read
                sources.fetch_video_text('https://www.tiktok.com/@cook/video/1', download=lambda u: {'video_path': 'x'}, watch=lambda p, c: ' ')

    def test_an_unreadable_page_gives_a_flagged_draft_without_retries(self):
        recipe = Recipe(title='x', cuisine='', difficulty='', status='generating', schema_version=2, source_type='web')
        db.session.add(recipe)
        db.session.commit()
        with mock.patch('services.recipe_v2.sources.fetch_recipe_text', side_effect=SourceError('This site blocks automatic reading.')):
            self.assertTrue(tasks.run(recipe.id, 'web', 'https://blocked.example/x', attempt=0))  # no retry on the first attempt
        recipe = db.session.get(Recipe, recipe.id)
        self.assertEqual((recipe.status, recipe.is_flagged_for_review), ('draft', True))
        self.assertEqual(recipe.validation_errors, [{'rule': 'source', 'message': 'This site blocks automatic reading.'}])

    def test_the_page_text_goes_into_round_1(self):
        from services.recipe_v2 import claude, generate

        seen = []

        def call(model, effort, messages, system=None, schema=None):
            seen.append(messages[0]['content'])
            raise RuntimeError('stop after round 1')

        with mock.patch('services.recipe_v2.sources.fetch_recipe_text', return_value=('Thai Red Curry\n- 3 tbsp red curry paste', 'jsonld')), \
                mock.patch.object(claude, 'call', call), self.assertRaises(RuntimeError):
            generate.create_recipe('web', 'https://blog.example/curry')
        self.assertIn('a web page', seen[0])
        self.assertIn('3 tbsp red curry paste', seen[0])


if __name__ == '__main__':
    unittest.main()
