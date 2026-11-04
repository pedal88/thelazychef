"""Translating recipes and the pantry (services/recipe_v2/translate.py). Claude is replaced by a stand-in, so nothing outside
the test is called."""
import json
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(ROOT)

os.environ['DB_BACKEND'] = 'local'
os.environ['DATABASE_URL'] = 'sqlite://'
os.environ['STORAGE_BACKEND'] = 'local'
os.environ.setdefault('SECRET_KEY', 'test-secret')
os.environ.setdefault('GOOGLE_API_KEY', 'test-key')

from app import app  # noqa: E402
from database.models import Ingredient, Recipe, RecipeTranslation, db  # noqa: E402
from scripts import translate as script  # noqa: E402
from services.ai_models import CLAUDE_OPUS, TRANSLATE_MODEL  # noqa: E402
from services.recipe_v2 import translate, translation  # noqa: E402
from services.recipe_v2.store import save_v2  # noqa: E402

with open(os.path.join(ROOT, 'data', 'pilot_v2', 'fasit', 'carbonara.json'), encoding='utf-8') as f:
    CARBONARA = json.load(f)


def _norwegian(answer):
    """What a good answer looks like: the rows Claude was given, with their words marked, placeholders intact."""
    def row(fields):
        out = {f: None for f in fields}
        return out
    asked = answer
    return {
        'title': f"{asked['title']} NB", 'chef_note': f"{asked['chef_note']} NB" if asked.get('chef_note') else None,
        'yield_text': f"{asked['yield_text']} NB" if asked.get('yield_text') else None,
        'components': [{'id': c['id'], 'name': f"{c['name']} NB"} for c in asked['components']],
        'lines': [{**row(translation.LINE_FIELDS), 'id': i['id'], **{k: f'{v} NB' for k, v in i.items() if k in translation.LINE_FIELDS}} for i in asked['lines']],
        'steps': [{**row(translation.STEP_FIELDS), 'id': s['id'], **{k: f'{v} NB' for k, v in s.items() if k in translation.STEP_FIELDS}} for s in asked['steps']],
    }


def stand_in(change=None, seen=None):
    """claude.call answering each attempt with a good translation, after change(answer, attempt)."""
    attempts = []

    def call(model, effort, messages, system=None, schema=None):
        attempts.append(messages)
        if seen is not None:
            seen.append({'model': model, 'system': system, 'schema': schema, 'messages': messages})
        answer = _norwegian(json.loads(messages[0]['content']))
        if change:
            change(answer, len(attempts))
        msg = SimpleNamespace(content=[SimpleNamespace(type='text', text=json.dumps(answer))], stop_reason='end_turn', model=model)
        return msg, {'cost_usd': 0.02, 'seconds': 1.0}
    return call


class TranslateTests(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        self.ctx = app.app_context()
        self.ctx.push()
        db.drop_all()
        db.create_all()
        self.recipe = Recipe(title='placeholder', cuisine='', difficulty='', language='en', status='approved')
        db.session.add(self.recipe)
        db.session.flush()
        save_v2(self.recipe, CARBONARA)
        self.recipe.title = 'Carbonara'
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def test_a_good_answer_can_be_saved_and_is_shown(self):
        words, attempts = translate.translate_recipe(self.recipe, call=stand_in())
        self.assertEqual(len(attempts), 1)
        translation.save(self.recipe, 'nb', words)
        db.session.commit()
        self.assertEqual(translation.of(self.recipe, 'nb')['title'], 'Carbonara NB')
        self.assertEqual(attempts[0]['cost_usd'], 0.02)

    def test_the_prompt_has_the_glossary_and_the_model_comes_from_ai_models(self):
        seen = []
        translate.translate_recipe(self.recipe, call=stand_in(seen=seen))
        self.assertEqual(seen[0]['model'], TRANSLATE_MODEL)
        self.assertIn('cream: fløte', seen[0]['system'])
        self.assertIn('Never swap one food for another', seen[0]['system'])
        self.assertIn('kefalotyri', seen[0]['system'])
        self.assertRegex(seen[0]['messages'][0]['content'], r'\{i\d+\}')

    def test_a_step_that_lost_its_placeholder_goes_back_and_is_put_right(self):
        def lose(answer, attempt):
            if attempt == 1:
                step = next(s for s in answer['steps'] if '{' in (s['text'] or ''))
                step['text'] = re.sub(r'\{i\d+\}', 'noe', step['text'])
        seen = []
        words, attempts = translate.translate_recipe(self.recipe, call=stand_in(lose, seen))
        self.assertIsNotNone(words)
        self.assertEqual(len(attempts), 2)
        self.assertTrue(attempts[0]['problems'])
        self.assertIn('placeholders', seen[1]['messages'][-1]['content'])

    def test_an_answer_that_stays_wrong_gives_none_and_nothing_is_saved(self):
        def always(answer, attempt):
            answer['steps'] = answer['steps'][1:]
        words, attempts = translate.translate_recipe(self.recipe, call=stand_in(always))
        self.assertIsNone(words)
        self.assertEqual(len(attempts), 1 + translate.MAX_RETRIES)
        self.assertIsNone(db.session.get(RecipeTranslation, (self.recipe.id, 'nb')))

    def test_an_answer_that_is_not_json_goes_back(self):
        calls = []

        def call(model, effort, messages, system=None, schema=None):
            calls.append(1)
            text = 'not json' if len(calls) == 1 else json.dumps(_norwegian(json.loads(messages[0]['content'])))
            return SimpleNamespace(content=[SimpleNamespace(type='text', text=text)], stop_reason='end_turn'), {'cost_usd': 0.01}
        words, attempts = translate.translate_recipe(self.recipe, call=call)
        self.assertIsNotNone(words)
        self.assertEqual(len(attempts), 2)

    def test_a_field_the_original_does_not_have_goes_back(self):
        def invent(answer, attempt):
            if attempt == 1:
                answer['lines'][0]['variety'] = 'oppdiktet'
        self.recipe.lines[0].variety = None
        db.session.commit()
        words, attempts = translate.translate_recipe(self.recipe, call=stand_in(invent))
        self.assertEqual(len(attempts), 2)
        self.assertNotIn('variety', words['lines'][self.recipe.lines[0].local_id])

    def test_the_schema_is_closed_and_asks_for_every_field(self):
        def walk(node):
            if node.get('type') == 'object':
                self.assertIs(node['additionalProperties'], False)
                self.assertEqual(set(node['required']), set(node['properties']))
                for value in node['properties'].values():
                    walk(value)
            if node.get('type') == 'array':
                walk(node['items'])
        walk(translate.RECIPE_SCHEMA)
        walk(translate.PANTRY_SCHEMA)

    def test_the_pantry_name_goes_with_its_line(self):
        item = Ingredient(food_id='900001', name='garlic', name_nb='hvitløk', status='active')
        db.session.add(item)
        self.recipe.lines[0].ingredient = item
        db.session.commit()
        seen = []
        translate.translate_recipe(self.recipe, call=stand_in(seen=seen))
        asked = json.loads(seen[0]['messages'][0]['content'])
        self.assertEqual(asked['lines'][0]['pantry_name_nb'], 'hvitløk')
        self.assertEqual(asked['lines'][0]['amount'], self.recipe.lines[0].amount)
        self.assertNotIn('pantry_name_nb', asked['lines'][1])

    def test_pantry_names_in_batches_and_only_what_was_asked(self):
        items = [Ingredient(food_id=f'9{n:05}', name=f'item {n}', status='active') for n in range(translate.PANTRY_BATCH + 2)]
        db.session.add_all(items)
        db.session.commit()
        calls = []

        def call(model, effort, messages, system=None, schema=None):
            calls.append(schema)
            asked = json.loads(messages[0]['content'])['pantry']
            rows = [{'id': r['id'], 'name_nb': f"{r['name']} nb"} for r in asked[:-1]] + [{'id': 999999, 'name_nb': 'not asked'}, {'id': asked[-1]['id'], 'name_nb': '  '}]
            return SimpleNamespace(content=[SimpleNamespace(type='text', text=json.dumps({'items': rows}))], stop_reason='end_turn'), {'cost_usd': 0.01}
        names, usages = translate.translate_pantry(items, call=call)
        self.assertEqual(len(calls), 2)
        self.assertEqual(len(usages), 2)
        self.assertEqual(names[items[0].id], 'item 0 nb')
        self.assertNotIn(999999, names)
        self.assertNotIn(items[-1].id, names)  # left without a name, not blank

    def _script(self, *args, call=None):
        env = {'ANTHROPIC_API_KEY': 'test', 'DB_BACKEND': 'local'}
        with mock.patch.object(sys, 'argv', ['translate', *args]), mock.patch.dict(os.environ, env), \
                mock.patch('services.recipe_v2.claude.call', call or mock.Mock(side_effect=AssertionError('called Claude'))), \
                mock.patch.object(Path, 'home', return_value=self.home), mock.patch('builtins.print'):
            script.main()
        db.session.expire_all()

    def test_the_script_without_apply_calls_nothing_and_saves_nothing(self):
        with tempfile.TemporaryDirectory() as home:
            self.home = Path(home)
            self._script('--ids', str(self.recipe.id))
            self._script('--pantry')
            self.assertIsNone(db.session.get(RecipeTranslation, (self.recipe.id, 'nb')))

    def test_the_script_translates_keeps_a_file_leaves_what_is_done_and_can_take_it_away(self):
        with tempfile.TemporaryDirectory() as home:
            self.home = Path(home)
            self._script('--ids', str(self.recipe.id), '--apply', call=stand_in())
            self.assertEqual(db.session.get(RecipeTranslation, (self.recipe.id, 'nb')).title, 'Carbonara NB')
            self.assertEqual(len(list((self.home / 'promptlab-runs' / 'translate').glob('*.json'))), 1)
            self._script('--ids', str(self.recipe.id), '--apply')  # already done: Claude is not called
            self._script('--remove', '--ids', str(self.recipe.id), '--apply')
            self.assertIsNone(db.session.get(RecipeTranslation, (self.recipe.id, 'nb')))

    def test_the_script_can_try_a_model_and_save_the_file_later_without_paying_again(self):
        item = Ingredient(food_id='900001', name='garlic', status='active')
        db.session.add(item)
        self.recipe.lines[0].ingredient = item
        db.session.commit()
        seen = []

        def call(model, effort, messages, system=None, schema=None):
            if 'pantry' in messages[0]['content'][:12]:
                seen.append(model)
                rows = [{'id': r['id'], 'name_nb': 'hvitløk'} for r in json.loads(messages[0]['content'])['pantry']]
                return SimpleNamespace(content=[SimpleNamespace(type='text', text=json.dumps({'items': rows}))], stop_reason='end_turn'), {'cost_usd': 0.01}
            seen.append(model)
            return stand_in()(model, effort, messages, system=system, schema=schema)
        with tempfile.TemporaryDirectory() as home:
            self.home = Path(home)
            self._script('--ids', str(self.recipe.id), '--try', '--model', 'opus', call=call)
            self.assertEqual(set(seen), {CLAUDE_OPUS})
            self.assertIsNone(db.session.get(RecipeTranslation, (self.recipe.id, 'nb')))
            self.assertIsNone(db.session.execute(db.select(Ingredient).filter_by(food_id='900001')).scalar_one().name_nb)
            kept = next((self.home / 'promptlab-runs' / 'translate').glob('*.json'))
            self._script('--from-file', str(kept))  # without --apply: nothing yet
            self.assertIsNone(db.session.get(RecipeTranslation, (self.recipe.id, 'nb')))
            self._script('--from-file', str(kept), '--apply')  # Claude is not called
            self.assertEqual(db.session.get(RecipeTranslation, (self.recipe.id, 'nb')).title, 'Carbonara NB')
            self.assertEqual(db.session.execute(db.select(Ingredient).filter_by(food_id='900001')).scalar_one().name_nb, 'hvitløk')

    def test_a_saved_file_is_left_out_when_the_words_have_changed(self):
        with tempfile.TemporaryDirectory() as home:
            self.home = Path(home)
            self._script('--ids', str(self.recipe.id), '--try', call=stand_in())
            kept = next((self.home / 'promptlab-runs' / 'translate').glob('*.json'))
            self.recipe.steps[0].short = 'Something else'
            db.session.commit()
            self._script('--from-file', str(kept), '--apply')
            self.assertIsNone(db.session.get(RecipeTranslation, (self.recipe.id, 'nb')))

    def test_the_script_leaves_a_recipe_written_in_norwegian(self):
        self.recipe.language = 'nb'
        db.session.commit()
        with tempfile.TemporaryDirectory() as home:
            self.home = Path(home)
            self._script('--ids', str(self.recipe.id), '--apply')
            self.assertIsNone(db.session.get(RecipeTranslation, (self.recipe.id, 'nb')))

    def test_the_glossary_is_well_formed(self):
        words = translate.glossary()
        self.assertEqual(words['food']['cream'], 'fløte')
        self.assertEqual(words['food']['sirloin'], 'ytrefilet')
        self.assertTrue(all(isinstance(v, str) and v for part in ('food', 'cooking') for v in words[part].values()))


if __name__ == '__main__':
    unittest.main()
