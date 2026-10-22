"""New recipe in model v2: the input page, the status page, the task endpoint and the queue.

Claude is replaced by recorded answers from the pilot, and Google Cloud by
stand-ins, so nothing outside the test is called.
"""
import base64
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
for key in ('TASKS_QUEUE', 'TASKS_SERVICE_ACCOUNT', 'APP_BASE_URL'):
    os.environ.pop(key, None)

from app import app  # noqa: E402
from database.models import Chef, Recipe, User, db  # noqa: E402
from routes.recipe_v2_routes import kind_of  # noqa: E402
from services.recipe_v2 import claude, language, tasks  # noqa: E402

QUEUE_ENV = {'TASKS_QUEUE': 'recipe-generation', 'TASKS_LOCATION': 'europe-west1',
             'TASKS_SERVICE_ACCOUNT': 'recipe-tasks@p.iam.gserviceaccount.com', 'APP_BASE_URL': 'https://app.example'}


def recorded():
    with open(os.path.join(ROOT, 'data', 'pilot_v2', 'results_0b', 'opus-low', 'fasit', 'carbonara.json'), encoding='utf-8') as f:
        return json.load(f)


def fake_claude():
    run = recorded()
    answers = [run['source_text'], json.dumps(run['recipe'], ensure_ascii=False)]

    def call(model, effort, messages, system=None, schema=None):
        text = answers.pop(0)
        msg = SimpleNamespace(content=[SimpleNamespace(type='text', text=text)], stop_reason='end_turn', model=model)
        return msg, {'cost_usd': 0.01, 'seconds': 1.0}
    return call


class RecipeV2RouteTests(unittest.TestCase):
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

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def login(self):
        self.client.post('/login', data={'email': 'admin@test', 'password': 'pw'})

    def test_short_input_is_an_idea_and_long_or_multiline_is_a_recipe(self):
        self.assertEqual(kind_of('Chicken tikka masala for four'), 'idea')
        self.assertEqual(kind_of('Pancakes\n2 eggs\n3 dl milk'), 'text')
        self.assertEqual(kind_of('x' * 300), 'text')

    def test_locally_the_recipe_is_made_straight_away(self):
        self.login()
        self.assertEqual(self.client.get('/new-recipe/v2').status_code, 200)
        with mock.patch.object(claude, 'call', fake_claude()):
            res = self.client.post('/new-recipe/v2', data={'source': 'Spaghetti carbonara for four'})
        recipe = db.session.execute(db.select(Recipe)).scalar_one()
        self.assertEqual(res.headers['Location'], f'/new-recipe/v2/{recipe.id}')
        self.assertEqual((recipe.status, recipe.schema_version, recipe.source_type), ('draft', 2, 'description'))
        self.assertTrue(recipe.steps)
        # Done, so the status page moves on to the recipe
        self.assertEqual(self.client.get(f'/new-recipe/v2/{recipe.id}').headers['Location'], f'/recipe/{recipe.id}')
        self.assertEqual(self.client.get(f'/recipe/{recipe.id}').status_code, 200)

    def test_a_chef_writes_the_idea_and_broken_rules_flag_the_draft(self):
        with open(os.path.join(ROOT, 'data', 'agents', 'chefs.json'), encoding='utf-8') as f:
            c = next(c for c in json.load(f)['chefs'] if c['id'] == 'speezy_gonzales')
        db.session.add(Chef(id=c['id'], name=c['name'], archetype=c['archetype'], description=c['description'],
                            image_filename='', **{k: json.dumps(c[k]) for k in ('constraints', 'diet_preferences',
                            'cooking_style', 'ingredient_logic', 'instruction_style')}))
        db.session.commit()
        self.login()
        self.assertIn(b'Speezy Gonzales', self.client.get('/new-recipe/v2').data)
        asked = []
        call = fake_claude()
        with mock.patch.object(claude, 'call', lambda *a, **kw: asked.append(a[2]) or call(*a, **kw)):
            self.client.post('/new-recipe/v2', data={'source': 'Spaghetti carbonara for four', 'chef_id': 'speezy_gonzales'})
        recipe = db.session.execute(db.select(Recipe)).scalar_one()
        self.assertEqual(recipe.chef_id, 'speezy_gonzales')
        self.assertIn('THE COOK\nWrite it as Speezy Gonzales', asked[0][0]['content'])
        # The recorded carbonara takes longer and needs more washing up than Speezy allows
        notes = [e['message'] for e in recipe.validation_errors if e['rule'] == 'persona']
        self.assertTrue(any(n.startswith('Takes ') for n in notes), notes)
        self.assertTrue(recipe.is_flagged_for_review)
        self.assertIn(b'It breaks a rule of its chef', self.client.get(f'/recipe/{recipe.id}').data)

    def test_settings_go_on_top_of_the_chef_and_retired_chefs_are_not_offered(self):
        with open(os.path.join(ROOT, 'data', 'agents', 'chefs.json'), encoding='utf-8') as f:
            seeds = {c['id']: c for c in json.load(f)['chefs']}
        for cid, active in (('the_minimalist', True), ('family_cook', False)):
            c = seeds[cid]
            db.session.add(Chef(id=cid, name=c['name'], archetype=c['archetype'], description=c['description'],
                                image_filename='', active=active, **{k: json.dumps(c[k]) for k in ('constraints', 'diet_preferences',
                                'cooking_style', 'ingredient_logic', 'instruction_style')}))
        db.session.commit()
        self.login()
        page = self.client.get('/new-recipe/v2').data
        self.assertIn(b'The Minimalist', page)
        self.assertNotIn(b'The Family Cook', page)
        self.assertIn(b'value="kid_friendly"', page)
        asked = []
        call = fake_claude()
        with mock.patch.object(claude, 'call', lambda *a, **kw: asked.append(a[2]) or call(*a, **kw)):
            self.client.post('/new-recipe/v2', data={'source': 'Spaghetti carbonara for four', 'chef_id': 'the_minimalist',
                                                     'settings': ['vegetarian', 'low_carb', 'nonsense']})
        recipe = db.session.execute(db.select(Recipe)).scalar_one()
        self.assertEqual((recipe.chef_id, recipe.settings), ('the_minimalist', ['vegetarian', 'low_carb']))
        prompt = asked[0][0]['content']
        for part in ('Write it as The Minimalist', 'Vegetarian:', 'Low carb:', 'at most 6 ingredients'):
            self.assertIn(part, prompt)
        notes = [e['message'] for e in recipe.validation_errors if e['rule'] == 'persona']
        self.assertTrue(any('outside the foundation pantry' in n and 'allows 1' in n for n in notes), notes)
        self.assertIn('Vegetarian · Low carb', self.client.get(f'/recipe/{recipe.id}').get_data(as_text=True))
        with mock.patch.object(claude, 'call', fake_claude()):
            self.client.post('/new-recipe/v2', data={'source': 'Fish pie', 'chef_id': 'family_cook'})
        self.assertIsNone(db.session.execute(db.select(Recipe).order_by(Recipe.id.desc())).scalars().first().chef_id)

    def test_an_unknown_chef_is_ignored(self):
        self.login()
        with mock.patch.object(claude, 'call', fake_claude()):
            self.client.post('/new-recipe/v2', data={'source': 'Spaghetti carbonara for four', 'chef_id': 'nobody'})
        self.assertIsNone(db.session.execute(db.select(Recipe)).scalar_one().chef_id)

    def test_recipes_are_in_english_unless_another_language_is_chosen(self):
        self.login()
        for language, expected, code in (('', 'Write a recipe in English for: Kyllinggryte', 'en'),
                                         ('nb', 'Write a recipe in Norwegian (bokmål) for: Kyllinggryte', 'nb'),
                                         ('xx', 'Write a recipe in English for: Kyllinggryte', 'en')):
            asked = []
            call = fake_claude()
            with mock.patch.object(claude, 'call', lambda *a, **kw: asked.append(a[2]) or call(*a, **kw)):
                self.client.post('/new-recipe/v2', data={'source': 'Kyllinggryte med ris, for fire', 'language': language})
            self.assertIn(expected, asked[0][0]['content'], language)
            recipe = db.session.execute(db.select(Recipe).order_by(Recipe.id.desc())).scalars().first()
            self.assertEqual(recipe.language, code, language)

    def test_language_codes(self):
        self.assertEqual(language.code_of('nb'), 'nb')
        self.assertEqual(language.code_of('Norwegian (bokmål)'), 'nb')  # tasks queued before the codes
        self.assertIsNone(language.code_of('xx'))
        self.assertIsNone(language.prompt_name(None))

    def test_the_front_page_sends_ideas_links_and_text_to_v2(self):
        self.login()
        page = self.client.get('/new-recipe').get_data(as_text=True)
        self.assertEqual(page.count('action="/new-recipe/v2"'), 3)
        self.assertIn('action="/generate/video"', page)  # video stays on the old importer
        self.assertIn('id="chef-none"', page)
        self.assertIn('<option value="en" selected>English</option>', page)
        self.assertEqual(page.count('class="language-copy" value="en"'), 2)

    def test_empty_input_is_refused(self):
        self.login()
        self.assertEqual(self.client.post('/new-recipe/v2', data={'source': '  '}).status_code, 400)

    def test_with_a_queue_the_recipe_waits_and_the_task_is_queued(self):
        self.login()
        posted = {}

        class Session:
            def __init__(self, credentials):
                pass

            def post(self, url, json=None, timeout=None):
                posted.update(url=url, task=json)
                return SimpleNamespace(raise_for_status=lambda: None)

        with mock.patch.dict(os.environ, QUEUE_ENV), mock.patch('google.auth.default', return_value=(None, 'p')), \
                mock.patch('google.auth.transport.requests.AuthorizedSession', Session):
            self.client.post('/new-recipe/v2', data={'source': 'Lasagne', 'language': 'nb'})
        recipe = db.session.execute(db.select(Recipe)).scalar_one()
        self.assertEqual(recipe.status, 'generating')
        self.assertTrue(posted['url'].endswith('/locations/europe-west1/queues/recipe-generation/tasks'))
        request = posted['task']['task']['httpRequest']
        self.assertEqual(request['url'], f'https://app.example/internal/tasks/recipe-v2/{recipe.id}')
        self.assertEqual(request['oidcToken'], {'serviceAccountEmail': QUEUE_ENV['TASKS_SERVICE_ACCOUNT'], 'audience': 'https://app.example'})
        self.assertEqual(json.loads(base64.b64decode(request['body'])),
                         {'kind': 'idea', 'source': 'Lasagne', 'language': 'nb'})
        self.assertEqual(recipe.language, 'nb')
        self.assertEqual(self.client.get(f'/new-recipe/v2/{recipe.id}/status').get_json()['status'], 'generating')

    def test_the_task_endpoint_needs_the_queue_token(self):
        recipe = Recipe(title='x', cuisine='', difficulty='', status='generating', schema_version=2)
        db.session.add(recipe)
        db.session.commit()
        url = f'/internal/tasks/recipe-v2/{recipe.id}'
        body = {'kind': 'idea', 'source': 'Spaghetti carbonara'}
        self.assertEqual(self.client.post(url, json=body).status_code, 401)
        with mock.patch.dict(os.environ, QUEUE_ENV):
            self.assertEqual(self.client.post(url, json=body, headers={'Authorization': 'Bearer forged'}).status_code, 401)
            with mock.patch.object(tasks, 'verified', return_value=True), mock.patch.object(claude, 'call', fake_claude()):
                res = self.client.post(url, json=body, headers={'Authorization': 'Bearer ok'})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(db.session.get(Recipe, recipe.id).status, 'draft')

    def test_the_task_endpoint_makes_versions(self):
        recipe = Recipe(title='x', cuisine='', difficulty='', status='generating', schema_version=2)
        db.session.add(recipe)
        db.session.commit()
        ran = []
        with mock.patch.dict(os.environ, QUEUE_ENV), mock.patch.object(tasks, 'verified', return_value=True), \
                mock.patch.object(tasks, 'run', lambda *a, **kw: ran.append((a, kw))):
            res = self.client.post(f'/internal/tasks/recipe-v2/{recipe.id}', headers={'Authorization': 'Bearer ok'},
                                   json={'kind': 'version', 'source': 'The recipe as text', 'language': 'Norwegian (bokmål)'})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(ran[0][0][:3], (recipe.id, 'version', 'The recipe as text'))
        self.assertEqual(ran[0][1]['language'], 'nb')

    def test_the_token_must_come_from_the_queue_account(self):
        with mock.patch.dict(os.environ, QUEUE_ENV):
            claims = {'email': QUEUE_ENV['TASKS_SERVICE_ACCOUNT'], 'email_verified': True}
            with mock.patch('google.oauth2.id_token.verify_oauth2_token', return_value=claims) as verify:
                self.assertTrue(tasks.verified('Bearer t'))
                self.assertEqual(verify.call_args.kwargs['audience'], 'https://app.example')
            with mock.patch('google.oauth2.id_token.verify_oauth2_token', return_value=dict(claims, email='someone@else')):
                self.assertFalse(tasks.verified('Bearer t'))

    def test_errors_are_retried_and_the_last_one_flags_the_draft(self):
        recipe = Recipe(title='x', cuisine='', difficulty='', status='generating', schema_version=2)
        db.session.add(recipe)
        db.session.commit()

        def broken(*args, **kwargs):
            raise RuntimeError('overloaded')

        with mock.patch.object(claude, 'call', broken):
            with self.assertRaises(RuntimeError):
                tasks.run(recipe.id, 'idea', 'x', attempt=0)
            self.assertEqual(db.session.get(Recipe, recipe.id).status, 'generating')
            self.assertTrue(tasks.run(recipe.id, 'idea', 'x', attempt=tasks.MAX_ATTEMPTS - 1))
        recipe = db.session.get(Recipe, recipe.id)
        self.assertEqual((recipe.status, recipe.is_flagged_for_review), ('draft', True))
        self.assertNotIn('overloaded', recipe.validation_errors[0]['message'])  # no raw errors in the UI

    def test_a_finished_recipe_is_not_made_twice(self):
        recipe = Recipe(title='x', cuisine='', difficulty='', status='draft', schema_version=2)
        db.session.add(recipe)
        db.session.commit()
        with mock.patch.object(claude, 'call', side_effect=AssertionError('called')):
            self.assertTrue(tasks.run(recipe.id, 'idea', 'x'))


if __name__ == '__main__':
    unittest.main()
