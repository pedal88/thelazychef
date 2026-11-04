"""The review API (routes/review_api_routes.py): it needs its own key, it only reads, and nothing about people is in it."""
import json
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

from app import app  # noqa: E402
from database.models import (  # noqa: E402
    Ingredient, IngredientAlias, Recipe, RecipeNote, User, UserQueue, UserRecipeInteraction, db,
)
from services.recipe_v2.store import save_v2  # noqa: E402

with open(os.path.join(ROOT, 'data', 'pilot_v2', 'fasit', 'carbonara.json'), encoding='utf-8') as f:
    CARBONARA = json.load(f)

KEY = 'test-review-key'
EMAIL = 'someone.private@example.test'
NOTE_TEXT = 'an admin note that must stay in the app'
URLS = ('/recipes/{id}', '/pantry?q=butter', '/questions', '/pantry-report')


def rules():
    return [r for r in app.url_map.iter_rules() if r.endpoint.startswith('review_api.')]


class ReviewApiTests(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        self.ctx = app.app_context()
        self.ctx.push()
        db.drop_all()
        db.create_all()
        self.client = app.test_client()
        env = mock.patch.dict(os.environ, {'REVIEW_API_KEY': KEY})
        env.start()
        self.addCleanup(env.stop)

        self.person = User(email=EMAIL, is_admin=True)
        self.person.set_password('a-password')
        self.butter = Ingredient(food_id='b1', name='butter', status='active')
        self.waiting = Ingredient(food_id='y1', name='yogurt spread', status='pending')
        self.draft = Recipe(title='Draft', cuisine='Italian', difficulty='Simplistic', status='draft', source_type='text',
                            source_input='my idea', source_text='The source said this.', prep_time_mins=25)
        db.session.add_all([self.person, self.butter, self.waiting, self.draft,
                            IngredientAlias(ingredient=self.butter, name='100% smør')])
        save_v2(self.draft, CARBONARA)
        db.session.flush()
        next(line for line in self.draft.lines if line.name == 'vann').ingredient = self.butter
        next(line for line in self.draft.lines if line.name == 'salt').ingredient = self.waiting
        self.draft.validation_errors = [
            {'rule': 'ask', 'message': 'worth adding?', 'line': 'salt', 'item': 'y1', 'reason': 'it matters',
             'swap': {'food_id': 'b1', 'name': 'butter', 'amount_factor': 1, 'replacements': []}},
            {'rule': 'asked', 'message': 'x: added', 'line': 'x', 'answer': 'added x to the pantry', 'reason': 'r',
             'at': '2026-11-04T10:00:00+00:00'},
            {'rule': 'pantry', 'message': '"100% smør" is now an alias of butter (close enough)'}]
        db.session.flush()
        db.session.add_all([RecipeNote(recipe=self.draft, user_id=self.person.id, text=NOTE_TEXT),
                            UserRecipeInteraction(user_id=self.person.id, recipe_id=self.draft.id, status='favorite', comment=NOTE_TEXT),
                            UserQueue(user_id=self.person.id, recipe_id=self.draft.id)])
        db.session.commit()
        self.id = self.draft.id

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def get(self, path, key=KEY):
        headers = {'Authorization': f'Bearer {key}'} if key else {}
        return self.client.get(f'/api/review{path}', headers=headers)

    def urls(self):
        return [u.format(id=self.id) for u in URLS]

    # --- the key ---

    def test_every_route_is_covered_by_the_tests(self):
        self.assertEqual(len(rules()), len(URLS))

    def test_every_route_needs_the_key(self):
        for url in self.urls():
            with self.subTest(url=url):
                self.assertEqual(self.get(url, key=None).status_code, 401)
                self.assertEqual(self.get(url, key='wrong').status_code, 401)
                self.assertEqual(self.get(url).status_code, 200)

    def test_without_the_variable_the_api_is_off(self):
        with mock.patch.dict(os.environ):
            os.environ.pop('REVIEW_API_KEY')
            for url in self.urls():
                self.assertEqual(self.get(url).status_code, 401)
                self.assertEqual(self.get(url, key='').status_code, 401)

    def test_an_unknown_recipe_says_nothing_without_the_key(self):
        self.assertEqual(self.get('/recipes/999999', key=None).status_code, 401)
        self.assertEqual(self.get('/recipes/999999').status_code, 404)

    def test_the_keys_of_the_two_apis_do_not_open_each_other(self):
        with mock.patch.dict(os.environ, {'CONTENT_API_KEY': 'the-content-key'}):
            self.assertEqual(self.get('/questions', key='the-content-key').status_code, 401)
            review_key = {'Authorization': f'Bearer {KEY}'}
            self.assertEqual(self.client.get('/api/content/pages', headers=review_key).status_code, 401)
            self.assertEqual(self.client.post('/api/content/packages', headers=review_key, json={}).status_code, 401)
            self.assertEqual(self.client.post('/api/social/drafts', headers=review_key, json={}).status_code, 401)

    def test_an_admins_login_is_not_the_key(self):
        with self.client.session_transaction() as session:
            session['_user_id'] = str(self.person.id)
            session['_fresh'] = True
        self.assertEqual(self.get('/questions', key=None).status_code, 401)

    # --- only reading ---

    def test_every_route_is_get_only(self):
        for rule in rules():
            self.assertEqual(rule.methods, {'GET', 'HEAD', 'OPTIONS'}, rule.rule)

    def test_writes_are_refused_with_the_key_and_without(self):
        for url in self.urls():
            for method in ('POST', 'PUT', 'PATCH', 'DELETE'):
                for headers in ({'Authorization': f'Bearer {KEY}'}, {}):
                    with self.subTest(url=url, method=method, key=bool(headers)):
                        self.assertEqual(self.client.open(f'/api/review{url}', method=method, headers=headers).status_code, 405)
        self.assertIsNotNone(db.session.get(Recipe, self.id))

    def test_reading_changes_nothing(self):
        def state():
            db.session.expire_all()
            return (json.dumps(db.session.get(Recipe, self.id).validation_errors), db.session.get(Recipe, self.id).status,
                    sorted(i.name for i in db.session.execute(db.select(Ingredient)).scalars()),
                    sorted(a.name for a in db.session.execute(db.select(IngredientAlias)).scalars()))
        before = state()
        for url in self.urls():
            self.assertEqual(self.get(url).status_code, 200)
        self.assertEqual(state(), before)

    def test_on_postgres_the_transaction_is_read_only(self):
        conn = mock.MagicMock()
        conn.dialect.name = 'postgresql'
        with mock.patch.object(db.session, 'connection', return_value=conn):
            self.assertEqual(self.get('/questions').status_code, 200)
        self.assertEqual(str(conn.execute.call_args.args[0]), 'SET TRANSACTION READ ONLY')

    def test_without_the_key_it_does_not_touch_the_database(self):
        with mock.patch.object(db.session, 'connection') as connection:
            self.assertEqual(self.get('/questions', key=None).status_code, 401)
        connection.assert_not_called()

    # --- nothing about people ---

    def test_no_user_data_in_any_answer(self):
        forbidden = (EMAIL, self.person.password_hash, NOTE_TEXT)
        names = {'email', 'password', 'password_hash', 'user', 'user_id', 'users', 'notes', 'interactions', 'queue_items'}

        def keys(value):
            if isinstance(value, dict):
                for k, v in value.items():
                    yield k
                    yield from keys(v)
            elif isinstance(value, list):
                for v in value:
                    yield from keys(v)
        for url in self.urls():
            with self.subTest(url=url):
                response = self.get(url)
                self.assertEqual(response.status_code, 200)
                body = response.get_data(as_text=True)
                for text in forbidden:
                    self.assertNotIn(text, body)
                self.assertFalse(names & set(keys(response.get_json())))

    def test_no_route_reaches_people(self):
        for rule in rules():
            self.assertNotRegex(rule.rule, r'user|account|login|interaction|queue|funnel|note')
        for path in ('/users', '/users/1', '/user/1', '/interactions', '/notes'):
            self.assertEqual(self.get(path).status_code, 404, path)

    # --- the answers ---

    def test_a_recipe_with_its_draft_status_source_lines_and_steps(self):
        body = self.get(f'/recipes/{self.id}').get_json()
        self.assertEqual((body['status'], body['source_type'], body['source_text']), ('draft', 'text', 'The source said this.'))
        self.assertEqual(body['times']['saved_minutes'], 25)
        self.assertGreater(body['times']['planned_minutes'], 0)
        self.assertEqual([e['rule'] for e in body['validation_errors']], ['ask', 'asked', 'pantry'])
        linked = next(line for line in body['lines'] if line['name'] == 'vann')
        self.assertEqual(linked['pantry']['name'], 'butter')
        self.assertEqual(linked['pantry']['aliases'], ['100% smør'])  # why a line stays linked to an item
        spaghetti = next(line for line in body['lines'] if line['name'] == 'spaghetti')
        self.assertIsNone(spaghetti['pantry'])
        self.assertGreater(spaghetti['amount'], 0)
        self.assertTrue(body['steps'][0]['text'])
        self.assertTrue(any(step['after'] for step in body['steps']))

    def test_a_recipe_with_a_cycle_in_its_steps_can_still_be_read(self):
        with mock.patch('routes.review_api_routes.plan_v2', side_effect=ValueError('The steps form a cycle')):
            body = self.get(f'/recipes/{self.id}').get_json()
        self.assertIsNone(body['times']['planned_minutes'])
        self.assertTrue(body['steps'])

    def test_the_pantry_by_name_or_alias_in_any_status(self):
        self.assertEqual([i['name'] for i in self.get('/pantry?q=YOGURT').get_json()['items']], ['yogurt spread'])
        self.assertEqual(self.get('/pantry?q=yogurt').get_json()['items'][0]['status'], 'pending')
        self.assertEqual([i['name'] for i in self.get('/pantry?q=sm%C3%B8r').get_json()['items']], ['butter'])
        self.assertEqual(self.get('/pantry?q=butter').get_json()['items'][0]['aliases'], ['100% smør'])
        self.assertEqual(self.get('/pantry?q=%25').get_json()['items'][0]['name'], 'butter')  # a %, not a wildcard
        self.assertEqual(self.get('/pantry?q=_').get_json()['items'], [])
        self.assertEqual(self.get('/pantry').status_code, 400)

    def test_the_questions_and_the_answers(self):
        body = self.get('/questions').get_json()
        question = body['questions'][0]
        self.assertEqual(question['item']['name'], 'yogurt spread')
        self.assertTrue(question['can_swap'])
        waiting = question['recipes'][0]
        self.assertEqual((waiting['recipe_id'], waiting['lines'], waiting['reason']), (self.id, ['salt'], 'it matters'))
        self.assertEqual(waiting['swap_item'], {'food_id': 'b1', 'name': 'butter'})
        self.assertEqual(body['answered'][0]['answer'], 'added x to the pantry')
        self.assertEqual(body['answered'][0]['recipe_id'], self.id)
        self.assertEqual(self.get('/questions?limit=0').get_json()['answered'], [])

    def test_the_pantry_report(self):
        report = '\n'.join(self.get('/pantry-report').get_json()['report'])
        self.assertIn('- 100% smør -> butter: 0 lines, close enough', report)
        self.assertIn(f'- vann -> butter: {self.id}', report)
        self.assertIn('LINES LINKED TO AN ITEM', report)

    def test_the_report_leaves_stdout_alone(self):
        # A running app has threads: redirecting stdout in the report would swallow what they print
        stdout = sys.stdout
        self.get('/pantry-report')
        self.assertIs(sys.stdout, stdout)

    def test_the_report_works_without_scripts(self):
        # scripts/ is not in the production image (.dockerignore)
        with open(os.path.join(ROOT, '.dockerignore'), encoding='utf-8') as f:
            self.assertIn('scripts/', f.read().split())
        for path in ('routes/review_api_routes.py', 'services/recipe_v2/pantry_links.py'):
            with open(os.path.join(ROOT, path), encoding='utf-8') as f:
                self.assertNotRegex(f.read(), r'(?m)^\s*(from|import) scripts\b')


if __name__ == '__main__':
    unittest.main()
