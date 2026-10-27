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
        for part in ('Write it as The Minimalist', 'Vegetarian:', 'Low carb:', 'at most 8 ingredients'):
            self.assertIn(part, prompt)
        notes = [e['message'] for e in recipe.validation_errors if e['rule'] == 'persona']
        self.assertTrue(any('outside the foundation pantry' in n and 'allows 1' in n for n in notes), notes)
        self.assertIn('Vegetarian · Low carb', self.client.get(f'/recipe/{recipe.id}').get_data(as_text=True))
        with mock.patch.object(claude, 'call', fake_claude()):
            self.client.post('/new-recipe/v2', data={'source': 'Fish pie', 'chef_id': 'family_cook'})
        self.assertIsNone(db.session.execute(db.select(Recipe).order_by(Recipe.id.desc())).scalars().first().chef_id)

    def test_baby_keeps_its_age_tags_the_recipe_and_flags_what_a_baby_should_not_get(self):
        self.login()
        page = self.client.get('/new-recipe/v2').get_data(as_text=True)
        self.assertIn('value="baby"', page)
        self.assertIn('8 months+: coarser mash', page)
        asked = []
        call = fake_claude()
        with mock.patch.object(claude, 'call', lambda *a, **kw: asked.append(a[2]) or call(*a, **kw)):
            self.client.post('/new-recipe/v2', data={'source': 'Spaghetti carbonara for four', 'settings': ['baby'],
                                                     'age_from_months': '8'})
        recipe = db.session.execute(db.select(Recipe)).scalar_one()
        self.assertEqual((recipe.settings, recipe.age_from_months), (['baby'], 8))
        self.assertIn('From 8 months: a coarser mash', asked[0][0]['content'])
        self.assertIn('Baby Food', recipe.meal_types_list)
        notes = [e['message'] for e in recipe.validation_errors if e['rule'] == 'persona']
        self.assertTrue(any(n.startswith('For a baby 8 months+') and 'salt' in n for n in notes), notes)  # carbonara has salt
        self.assertIn('Baby, 8 months+', self.client.get(f'/recipe/{recipe.id}').get_data(as_text=True))
        # An age that is not a stage becomes the youngest; without Baby there is no age
        with mock.patch.object(claude, 'call', fake_claude()):
            self.client.post('/new-recipe/v2', data={'source': 'Fish pie', 'settings': ['baby'], 'age_from_months': '7'})
        with mock.patch.object(claude, 'call', fake_claude()):
            self.client.post('/new-recipe/v2', data={'source': 'Fish pie', 'age_from_months': '8'})
        ages = [r.age_from_months for r in db.session.execute(db.select(Recipe).order_by(Recipe.id)).scalars()]
        self.assertEqual(ages, [8, 6, None])

    def _chefs(self):
        with open(os.path.join(ROOT, 'data', 'agents', 'chefs.json'), encoding='utf-8') as f:
            seeds = {c['id']: c for c in json.load(f)['chefs']}
        for cid in ('the_classicist', 'the_smart_cook', 'the_minimalist'):
            c = seeds[cid]
            db.session.add(Chef(id=cid, name=c['name'], archetype=c['archetype'], description=c['description'],
                                image_filename='', active=True, **{k: json.dumps(c[k]) for k in ('constraints', 'diet_preferences',
                                'cooking_style', 'ingredient_logic', 'instruction_style')}))
        db.session.commit()

    def test_batch_reads_each_line_into_what_new_recipe_would_get(self):
        from services.chef_service import get_chefs
        from services.recipe_v2 import batch
        self._chefs()
        text = """# a note
Butter chicken, for 4 | smart | kid, low carb
Kjøttkaker i brun saus | Klassikeren
Søtpotetmos med linser | minimalist | baby 8

Pasta med tomatsaus | | vegetar
https://example.com/lasagne | classicist | kid
Pizza | nobody
Taco | smart | spicy
""" + 'x' * 201
        rows, over = batch.parse(text, get_chefs(), default_settings=['vegetarian'])
        got = [(r['no'], r['chef']['id'] if r['chef'] else None, r['settings'], r['age'], bool(r['error'])) for r in rows]
        self.assertEqual(got, [
            (2, 'the_smart_cook', ['kid_friendly', 'low_carb'], None, False),
            (3, 'the_classicist', ['vegetarian'], None, False),  # no settings on the line: the default
            (4, 'the_minimalist', ['baby'], 8, False),
            (6, None, ['vegetarian'], None, False),
            (7, 'the_classicist', [], None, False),  # a recipe page is kept as it is
            (8, None, ['vegetarian'], None, True),   # no such chef
            (9, 'the_smart_cook', [], None, True),   # no such setting
            (10, None, ['vegetarian'], None, True),  # too long for an idea
        ])
        self.assertEqual(rows[4]['kind'], 'web')
        self.assertEqual(over, 0)

    def test_batch_checks_first_then_makes_the_recipes_and_shows_how_they_get_on(self):
        self._chefs()
        self.login()
        page = self.client.get('/new-recipe/v2/batch').get_data(as_text=True)
        self.assertIn('Many recipes at once', page)
        lines = 'Spaghetti carbonara for four | smart\nPasta for two | nobody\nCarbonara for two | minimalist | baby 8'
        checked = self.client.post('/new-recipe/v2/batch', data={'lines': lines, 'action': 'check'}).get_data(as_text=True)
        self.assertIn('Make 2 recipes', checked)
        self.assertIn('No single chef called', checked)
        self.assertEqual(db.session.execute(db.select(db.func.count(Recipe.id))).scalar(), 0)  # checking makes nothing
        fakes = []  # a recorded answer pair (round 1, round 2) per recipe

        def call(*a, **kw):
            if not fakes or fakes[-1][1] == 2:
                fakes.append([fake_claude(), 0])
            fakes[-1][1] += 1
            return fakes[-1][0](*a, **kw)
        with mock.patch.object(claude, 'call', call):
            res = self.client.post('/new-recipe/v2/batch', data={'lines': lines, 'action': 'make'})
        self.assertIn('/new-recipe/v2/batch/status?ids=', res.headers['Location'])
        made = db.session.execute(db.select(Recipe).order_by(Recipe.id)).scalars().all()
        self.assertEqual([(r.chef_id, r.settings, r.age_from_months) for r in made],
                         [('the_smart_cook', None, None), ('the_minimalist', ['baby'], 8)])
        status = self.client.get(res.headers['Location']).get_data(as_text=True)
        self.assertIn('2 recipes made', status)
        self.assertNotIn('http-equiv="refresh"', status)
        # The same lines again: made before, so skipped unless asked
        again = self.client.post('/new-recipe/v2/batch', data={'lines': lines, 'action': 'check'}).get_data(as_text=True)
        self.assertIn('Made before', again)
        self.assertNotIn('Make 2 recipes', again)

    def test_images_for_many_recipes_are_queued_and_followed(self):
        from services.recipe_v2 import images
        self.login()
        with mock.patch.object(claude, 'call', fake_claude()):
            self.client.post('/new-recipe/v2', data={'source': 'Spaghetti carbonara for four'})
        recipe = db.session.execute(db.select(Recipe)).scalar_one()
        page = self.client.get('/new-recipe/v2/images').get_data(as_text=True)
        self.assertIn('1 recipe without an image', page)
        self.assertIn(f'name="ids" value="{recipe.id}" checked', page)

        def draw(recipe, storage, style=None):  # stands in for the image model
            recipe.image_filename = 'dish_test.webp'
            return {'dish': 'dish_test.webp', 'parts': 0, 'notes': [], 'style': 'cutout', 'trial': False, 'cost_usd': 0.1}
        with mock.patch.object(images, 'make_images', draw):
            res = self.client.post('/new-recipe/v2/images', data={'ids': [str(recipe.id)]})
        self.assertTrue(res.headers['Location'].endswith(f'/new-recipe/v2/images?started={recipe.id}'))
        db.session.refresh(recipe)
        self.assertEqual(recipe.image_filename, 'dish_test.webp')
        done = self.client.get(res.headers['Location']).get_data(as_text=True)
        self.assertIn('Images made for 1', done)
        self.assertIn('0 recipes without an image', done)
        self.assertNotIn('http-equiv="refresh"', done)

    def test_a_failed_image_job_is_noted_on_its_last_attempt(self):
        from services.recipe_v2 import images
        self.login()
        with mock.patch.object(claude, 'call', fake_claude()):
            self.client.post('/new-recipe/v2', data={'source': 'Spaghetti carbonara for four'})
        recipe = db.session.execute(db.select(Recipe)).scalar_one()

        def broken(*a, **kw):
            raise RuntimeError('quota')
        with mock.patch.object(images, 'make_images', broken):
            with self.assertRaises(RuntimeError):
                tasks.run_images(recipe.id, attempt=0)  # Cloud Tasks tries again
            self.assertTrue(tasks.run_images(recipe.id, attempt=tasks.MAX_ATTEMPTS - 1))
        db.session.refresh(recipe)
        self.assertEqual([e['rule'] for e in recipe.validation_errors if e['rule'] == 'image'], ['image'])
        self.assertIsNone(recipe.image_filename)
        # Only Cloud Tasks may call the job
        self.client.get('/logout')
        self.assertEqual(self.client.post(f'/internal/tasks/recipe-v2-images/{recipe.id}').status_code, 401)

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
        self.assertEqual(page.count('action="/new-recipe/v2"'), 4)  # the idea, a video, a web page and pasted text
        self.assertNotIn('/generate/video', page)
        self.assertIn('id="chef-none"', page)
        self.assertIn('<option value="en" selected>English</option>', page)
        self.assertEqual(page.count('class="language-copy" value="en"'), 3)
        # A prompt to copy for an AI that writes the one-line idea
        self.assertIn('Copy a prompt for your AI', page)
        self.assertIn('one line of at most 200 characters', page)

    def test_the_front_page_offers_only_the_chefs_of_now(self):
        with open(os.path.join(ROOT, 'data', 'agents', 'chefs.json'), encoding='utf-8') as f:
            seeds = {c['id']: c for c in json.load(f)['chefs']}
        for cid, active in (('the_minimalist', True), ('speezy_gonzales', False)):
            c = seeds[cid]
            db.session.add(Chef(id=cid, name=c['name'], archetype=c['archetype'], description=c['description'],
                                image_filename='', active=active, **{k: json.dumps(c[k]) for k in ('constraints', 'diet_preferences',
                                'cooking_style', 'ingredient_logic', 'instruction_style')}))
        db.session.commit()
        self.login()
        page = self.client.get('/new-recipe').get_data(as_text=True)
        self.assertIn('The Minimalist', page)
        self.assertNotIn('Speezy Gonzales', page)

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
                         {'kind': 'idea', 'source': 'Lasagne', 'language': 'nb', 'images': True})
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
            with mock.patch.object(tasks, 'verified', return_value=True), mock.patch.object(claude, 'call', fake_claude()), \
                    mock.patch.object(tasks, 'enqueue_images') as queued, mock.patch.object(tasks, 'enqueue_pantry') as pantry, \
                    mock.patch('services.recipe_v2.pantry_fill.needs_filling', return_value=False):
                res = self.client.post(url, json=body, headers={'Authorization': 'Bearer ok'})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(db.session.get(Recipe, recipe.id).status, 'draft')
        queued.assert_called_once_with(recipe.id)  # a task from before the option gets its images too
        pantry.assert_not_called()  # every line linked: no pantry job

    def test_a_made_recipe_queues_its_images_unless_asked_not_to(self):
        def placeholder():
            recipe = Recipe(title='x', cuisine='', difficulty='', status='generating', schema_version=2)
            db.session.add(recipe)
            db.session.commit()
            return recipe.id

        with mock.patch.dict(os.environ, QUEUE_ENV), mock.patch.object(tasks, 'enqueue_images') as queued, \
                mock.patch.object(tasks, 'enqueue_pantry') as pantry, \
                mock.patch('services.recipe_v2.pantry_fill.needs_filling', return_value=False):
            with mock.patch.object(claude, 'call', fake_claude()):
                first = placeholder()
                self.assertTrue(tasks.run(first, 'idea', 'Spaghetti carbonara'))
            with mock.patch.object(claude, 'call', fake_claude()):
                self.assertTrue(tasks.run(placeholder(), 'idea', 'Spaghetti carbonara', images=False))
            # A queue that will not take the image job leaves the recipe made
            queued.side_effect = RuntimeError('queue down')
            with mock.patch.object(claude, 'call', fake_claude()):
                third = placeholder()
                self.assertTrue(tasks.run(third, 'idea', 'Spaghetti carbonara'))
        self.assertEqual([c.args for c in queued.call_args_list], [(first,), (third,)])
        pantry.assert_not_called()
        self.assertEqual(db.session.get(Recipe, third).status, 'draft')
        self.assertTrue(db.session.get(Recipe, third).steps)
        # Without a queue (locally) no images are made on their own
        with mock.patch.object(tasks, 'enqueue_images') as local, mock.patch.object(claude, 'call', fake_claude()):
            tasks.run(placeholder(), 'idea', 'Spaghetti carbonara')
        local.assert_not_called()

    def test_the_forms_make_images_unless_skipped(self):
        self.login()
        new = self.client.get('/new-recipe/v2').get_data(as_text=True)
        self.assertIn('name="no_images" value="1">', new)  # not ticked
        ran = []
        with mock.patch.object(tasks, 'enqueue', lambda *a, **kw: ran.append(kw['images'])):
            self.client.post('/new-recipe/v2', data={'source': 'Lasagne'})
            self.client.post('/new-recipe/v2', data={'source': 'Lasagne', 'no_images': '1'})
            self.client.post('/new-recipe/v2/batch', data={'lines': 'Pasta for two', 'action': 'make'})
            self.client.post('/new-recipe/v2/batch', data={'lines': 'Pizza for two', 'action': 'make', 'no_images': '1'})
        self.assertEqual(ran, [True, False, True, False])
        checked = self.client.post('/new-recipe/v2/batch', data={'lines': 'Soup for two', 'action': 'check'}).get_data(as_text=True)
        self.assertIn('with the images', checked)

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
