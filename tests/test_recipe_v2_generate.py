"""Making a v2 recipe: both rounds, the validator loop, pantry matching and saving.

Claude is replaced by recorded answers from the phase 0b pilot
(data/pilot_v2/results_0b/opus-low), so no model is called.
"""
import copy
import json
import os
import sys
import unittest
from types import SimpleNamespace

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(ROOT)

os.environ['DB_BACKEND'] = 'local'
os.environ['DATABASE_URL'] = 'sqlite://'
os.environ['STORAGE_BACKEND'] = 'local'
os.environ.setdefault('SECRET_KEY', 'test-secret')
os.environ.setdefault('GOOGLE_API_KEY', 'test-key')
os.environ.pop('K_SERVICE', None)

from app import app  # noqa: E402
from database.models import Ingredient, Recipe, RecipeLine, db  # noqa: E402
from services.recipe_v2 import generate  # noqa: E402
from services.recipe_v2_validator import validate_recipe_v2  # noqa: E402


def recorded(name):
    with open(os.path.join(ROOT, 'data', 'pilot_v2', 'results_0b', 'opus-low', 'fasit', name + '.json'), encoding='utf-8') as f:
        return json.load(f)


def message(text, stop='end_turn'):
    return SimpleNamespace(content=[SimpleNamespace(type='text', text=text)], stop_reason=stop, model='claude-opus-5-5')


class FakeClaude:
    """Answers in order and records what it was asked."""

    def __init__(self, *answers):
        self.answers, self.requests = list(answers), []

    def __call__(self, model, effort, messages, system=None, schema=None):
        self.requests.append({'model': model, 'effort': effort, 'messages': copy.deepcopy(messages), 'system': system, 'schema': schema})
        usage = {'cost_usd': 0.01, 'seconds': 1.0, 'input_tokens': 100, 'output_tokens': 50}
        return self.answers.pop(0), usage


class GenerateTests(unittest.TestCase):
    def setUp(self):
        self.ctx = app.app_context()
        self.ctx.push()
        db.drop_all()
        db.create_all()
        self.run_ = recorded('carbonara')
        for food_id, name in (('000322', 'spaghetti'), ('000217', 'eggs'), ('000190', 'pecorino romano')):
            db.session.add(Ingredient(food_id=food_id, name=name, status='active', default_unit='g', main_category='pantry'))
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def _good(self):
        return message(json.dumps(self.run_['recipe'], ensure_ascii=False))

    def test_idea_becomes_a_saved_draft(self):
        fake = FakeClaude(message(self.run_['source_text']), self._good())
        recipe, report = generate.create_recipe('idea', 'Spaghetti carbonara for four', call=fake)

        self.assertTrue(report['valid'])
        self.assertEqual(report['attempts'], 1)
        saved = db.session.get(Recipe, recipe.id)
        self.assertEqual((saved.schema_version, saved.status, saved.source_type), (2, 'draft', 'description'))
        self.assertEqual(saved.source_text, self.run_['source_text'])
        self.assertEqual(saved.validation_errors, [])
        self.assertEqual(len(saved.steps), len(self.run_['recipe']['steps']))
        # Round 1 writes in the language of the idea; round 2 gets its text, with rules and pantry in the cached system prompt
        self.assertIn('Write a recipe for: Spaghetti carbonara for four\nWrite it in the language the idea is written in.',
                      fake.requests[0]['messages'][0]['content'])
        self.assertIn(self.run_['source_text'][:40], fake.requests[1]['messages'][0]['content'])
        self.assertIn('000322 spaghetti', fake.requests[1]['system'])
        self.assertNotIn(self.run_['source_text'][:40], fake.requests[1]['system'])
        self.assertIsNotNone(fake.requests[1]['schema'])

    def test_verb_state_and_metadata_are_asked_for_and_saved(self):
        answer = copy.deepcopy(self.run_['recipe'])
        answer.update(cuisine='Italian', difficulty='Moderate', meal_types=['Dinner', 'Main Dish'],
                      spice_level=0, keeps_days=1, freezes=True)
        answer['steps'][0]['verb'] = answer['steps'][0]['short'].split()[0].lower()
        cut_line = next(i for i in answer['ingredients'] if 'pecorino' in i['name'].lower())
        cut_line.update(state='grate', grade='fine', variety='Romano')
        fake = FakeClaude(message(self.run_['source_text']), message(json.dumps(answer, ensure_ascii=False)))
        recipe, report = generate.create_recipe('idea', 'Spaghetti carbonara for four', call=fake)

        self.assertTrue(report['valid'])
        saved = db.session.get(Recipe, recipe.id)
        self.assertEqual((saved.cuisine, saved.difficulty), ('Italian', 'Moderate'))
        self.assertEqual((saved.spice_level, saved.keeps_days, saved.freezes), (0, 1, True))
        # Freezer Friendly is set by the app from freezes, never by the model
        self.assertEqual(sorted(saved.meal_types_list), ['Dinner', 'Freezer Friendly', 'Main Dish'])
        self.assertNotIn('Freezer Friendly', fake.requests[1]['schema']['properties']['meal_types']['items']['enum'])
        # Derived after saving: what it is finished in, clean-up and the planned total time
        self.assertEqual(saved.heat_source, 'pan')
        self.assertIn(saved.cleanup_factor, range(1, 6))
        self.assertGreater(saved.prep_time_mins, 0)
        self.assertEqual(saved.steps[0].verb, answer['steps'][0]['verb'])
        line = next(line for line in saved.lines if line.local_id == cut_line['local_id'])
        self.assertEqual((line.state, line.grade, line.variety, line.cut), ('grate', 'fine', 'Romano', None))
        # The catalogs are in the prompt, and the schema only allows their values
        system, schema = fake.requests[1]['system'], fake.requests[1]['schema']
        for text in ('STATE CATALOG: chop (chopped / hakket; grades: fine, coarse)', 'CUISINE LIST: Nordic (Norwegian first', 'DIFFICULTY LIST: Simplistic', 'MEAL TYPE LIST: Breakfast', '20b. verb'):
            self.assertIn(text, system)
        self.assertEqual(schema['properties']['difficulty']['enum'], ['Simplistic', 'Moderate', 'Elevated'])
        line_schema = schema['$defs']['IngredientLineV2']['properties']
        self.assertIn('soften', line_schema['state']['enum'])
        self.assertIn('stiff', line_schema['grade']['enum'])
        self.assertNotIn('cut', line_schema)

    def test_lines_are_matched_to_the_pantry_and_the_rest_flags_the_recipe(self):
        fake = FakeClaude(message('text'), self._good())
        recipe, report = generate.create_recipe('idea', 'carbonara', call=fake)

        lines = db.session.execute(db.select(RecipeLine).filter_by(recipe_id=recipe.id)).scalars().all()
        linked = {line.name for line in lines if line.ingredient_id}
        self.assertTrue(any('spaghetti' in n.lower() for n in linked), linked)
        self.assertTrue(report['missing_in_pantry'])
        self.assertTrue(recipe.is_flagged_for_review)

    def test_a_failed_attempt_is_sent_back_with_the_errors(self):
        broken = copy.deepcopy(self.run_['recipe'])
        broken['steps'][0]['method'] = 'teleport'
        fake = FakeClaude(message('text'), message(json.dumps(broken)), self._good())
        recipe, report = generate.create_recipe('text', 'pasted recipe', call=fake)

        self.assertTrue(report['valid'])
        self.assertEqual(report['attempts'], 2)
        retry = fake.requests[2]['messages']
        self.assertEqual(retry[1]['role'], 'assistant')
        self.assertIn('teleport', retry[2]['content'])
        self.assertEqual(recipe.source_type, 'text')

    def test_still_invalid_after_retries_is_kept_as_a_flagged_draft(self):
        broken = message(json.dumps({'title': 'Broken', 'servings': 4, 'components': [], 'ingredients': [], 'steps': []}))
        fake = FakeClaude(message('the round 1 text'), broken, broken, broken)
        recipe, report = generate.create_recipe('idea', 'something', call=fake)

        self.assertFalse(report['valid'])
        self.assertEqual(report['attempts'], 1 + generate.MAX_RETRIES)
        self.assertTrue(recipe.is_flagged_for_review)
        self.assertTrue(recipe.validation_errors)
        self.assertEqual(recipe.source_text, 'the round 1 text')
        self.assertEqual(recipe.steps, [])

    def test_answers_cut_off_by_max_tokens_count_as_failed(self):
        fake = FakeClaude(message('text'), message('{"title": "Car', stop='max_tokens'), self._good())
        _, report = generate.create_recipe('idea', 'carbonara', call=fake)
        self.assertTrue(report['valid'])
        self.assertEqual(report['attempts'], 2)

    def test_an_empty_title_falls_back_to_the_round_1_title(self):
        data = dict(self.run_['recipe'], title='')
        fake = FakeClaude(message('Spaghetti Carbonara\n\nServes 4\n...'), message(json.dumps(data, ensure_ascii=False)))
        recipe, _ = generate.create_recipe('idea', 'carbonara for four please', call=fake)
        self.assertEqual(recipe.title, 'Spaghetti Carbonara')

    def test_the_fuzzy_matcher_gets_the_pantry(self):
        import ai_engine
        ai_engine.pantry_map = {}
        generate.match_pantry({'ingredients': [{'local_id': 'i1', 'name': 'spagetti'}]})
        self.assertTrue(ai_engine.pantry_map)

    def test_recorded_answers_pass_the_validator(self):
        for name in ('carbonara', 'lasagne', 'tikka', 'burger', 'brownies'):
            with self.subTest(name):
                self.assertTrue(validate_recipe_v2(recorded(name)['recipe'])['valid'])

    def test_each_next_to_a_total_amount_is_a_warning(self):
        r = copy.deepcopy(self.run_['recipe'])
        step = next(s for s in r['steps'] if s['uses'])
        step['text'] += f" Legg {{{step['uses'][0]}}} på hver tallerken."
        codes = [w['code'] for w in validate_recipe_v2(r)['warnings']]
        self.assertIn('each_total', codes)


if __name__ == '__main__':
    unittest.main()
