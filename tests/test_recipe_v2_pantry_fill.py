"""Filling the pantry for a made recipe's unlinked lines (services/recipe_v2/pantry_fill.py) and its queue job.

Claude is replaced by a stand-in that answers with fixed decisions, so nothing outside the test is called.
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
for key in ('TASKS_QUEUE', 'TASKS_SERVICE_ACCOUNT', 'APP_BASE_URL'):
    os.environ.pop(key, None)

from app import app  # noqa: E402
from database.models import Ingredient, IngredientAlias, Recipe, db  # noqa: E402
from scripts.fill_pantry import parse_ids  # noqa: E402
from services.recipe_v2 import pantry_fill, tasks  # noqa: E402
from services.recipe_v2.store import save_v2  # noqa: E402

with open(os.path.join(ROOT, 'data', 'pilot_v2', 'fasit', 'carbonara.json'), encoding='utf-8') as f:
    CARBONARA = json.load(f)  # nine lines, none in the empty test pantry

PECORINO = {'name': 'pecorino romano', 'main_category': 'dairy and egg', 'sub_category': 'cheese', 'default_unit': 'g',
            'average_g_per_unit': 0, 'calories': 387, 'protein': 32, 'carbs': 3.6, 'fat': 27, 'fat_saturated': 17,
            'sugar': 0.8, 'fiber': 0, 'sodium_mg': 1200, 'looks': 'pale wedge of hard sheep cheese'}


def answer(decisions, seen=None):
    """A stand-in for claude.call that answers with these decisions and keeps what it was asked."""
    def call(model, effort, messages, system=None, schema=None):
        if seen is not None:
            seen.append({'system': system, 'user': messages[0]['content']})
        msg = SimpleNamespace(content=[SimpleNamespace(type='text', text=json.dumps({'lines': decisions}))],
                              stop_reason='end_turn', model=model)
        return msg, {'cost_usd': 0.02, 'seconds': 1.0}
    return call


def decision(line, action, food_id='', new=None, reason='because'):
    return {'line': line, 'action': action, 'food_id': food_id, 'new': new, 'reason': reason}


class PantryFillTests(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        self.ctx = app.app_context()
        self.ctx.push()
        db.drop_all()
        db.create_all()
        self.pasta = Ingredient(food_id='000322', name='spaghetti', status='active', calories_per_100g=371,
                                protein_per_100g=13, carbs_per_100g=75, fat_per_100g=1.5, main_category='cereal grains and pasta')
        self.egg = Ingredient(food_id='000225', name='eggs', status='active', calories_per_100g=143, main_category='dairy and egg')
        db.session.add_all([self.pasta, self.egg])
        self.recipe = Recipe(title='Carbonara', cuisine='Italian', difficulty='Simplistic', status='draft')
        db.session.add(self.recipe)
        save_v2(self.recipe, CARBONARA)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def lines(self, name):
        return [line for line in self.recipe.lines if line.name == name]

    def test_aliases_new_items_and_skips_are_carried_out_and_noted(self):
        seen = []
        decisions = [decision('spaghetti', 'alias', '000322', reason='the same pasta'),
                     decision('eggeplomme', 'alias', 'nope'),  # no such item: left as it is
                     decision('pecorino romano', 'new', new=PECORINO, reason='sold in Norway'),
                     decision('vann', 'skip', reason='water'),
                     decision('something not asked', 'alias', '000322')]
        result = pantry_fill.fill(self.recipe, call=answer(decisions, seen))
        db.session.commit()

        # Claude saw the pantry and each unlinked name once (pecorino is on two lines)
        self.assertIn('000322 spaghetti', seen[0]['system'])
        self.assertEqual(seen[0]['user'].count('pecorino romano'), 1)
        # Alias: the line is linked; the name equals the item's own name, so no alias row is needed
        self.assertEqual(self.lines('spaghetti')[0].ingredient, self.pasta)
        # New: an active item marked as Claude's, with its nutrition, on both pecorino lines
        cheese = db.session.execute(db.select(Ingredient).where(Ingredient.name == 'pecorino romano')).scalar_one()
        self.assertEqual((cheese.status, cheese.data_source, cheese.calories_per_100g), ('active', 'claude_auto', 387))
        self.assertTrue(cheese.food_id.startswith('auto-'))
        self.assertEqual(cheese.image_notes, 'pale wedge of hard sheep cheese')  # for the symbol prompt
        self.assertEqual({line.ingredient_id for line in self.lines('pecorino romano')}, {cheese.id})
        # Skipped and unknown stay unlinked
        self.assertIsNone(self.lines('vann')[0].ingredient_id)
        self.assertIsNone(self.lines('eggeplomme')[0].ingredient_id)
        # One note per decision about a line asked about, kept on the recipe as information
        self.assertEqual(len(result['notes']), 4)
        notes = [e['message'] for e in self.recipe.validation_errors if e['rule'] == 'pantry']
        self.assertEqual(notes, result['notes'])
        self.assertIn('new pantry item pecorino romano', ' '.join(notes))
        self.assertEqual(result['cost_usd'], 0.02)

    def test_an_alias_name_links_the_next_recipe_without_claude(self):
        pantry_fill.fill(self.recipe, call=answer([decision('sort pepper', 'alias', '000225')]))
        db.session.commit()
        self.assertEqual(db.session.execute(db.select(IngredientAlias.name)).scalars().all(), ['sort pepper'])
        other = Recipe(title='Again', cuisine='Italian', difficulty='Simplistic', status='draft')
        db.session.add(other)
        save_v2(other, CARBONARA)
        from services.recipe_v2.generate import recalculate
        recalculate(other)  # the matcher finds the alias
        self.assertEqual([line.ingredient_id for line in other.lines if line.name == 'sort pepper'], [self.egg.id])

    def test_a_new_item_with_a_known_name_reuses_it(self):
        pantry_fill.fill(self.recipe, call=answer([decision('egg', 'new', new=dict(PECORINO, name='Eggs'))]))
        self.assertEqual(self.lines('egg')[0].ingredient, self.egg)
        self.assertEqual(db.session.execute(db.select(db.func.count(Ingredient.id))).scalar(), 2)

    def test_pantry_notes_do_not_flag_a_recipe_that_is_otherwise_fine(self):
        names = {line.name for line in self.recipe.lines}
        pantry_fill.fill(self.recipe, call=answer([decision(n, 'alias', '000322') for n in names]))
        self.assertTrue(all(line.ingredient_id for line in self.recipe.lines))
        self.assertTrue(self.recipe.validation_errors)
        self.assertFalse(self.recipe.is_flagged_for_review)

    def test_nothing_to_do_calls_nobody(self):
        for line in self.recipe.lines:
            line.ingredient = self.pasta
        result = pantry_fill.fill(self.recipe, call=mock.Mock(side_effect=AssertionError('called')))
        self.assertEqual(result, {'notes': [], 'cost_usd': 0.0})
        self.assertFalse(pantry_fill.needs_filling(self.recipe.id))

    def test_the_queue_job_fills_then_queues_the_images_and_notes_its_last_failure(self):
        queue = {'TASKS_QUEUE': 'q', 'TASKS_SERVICE_ACCOUNT': 'sa@x', 'APP_BASE_URL': 'https://app.example'}
        with mock.patch.dict(os.environ, queue), mock.patch.object(tasks, 'enqueue_images') as images, \
                mock.patch.object(pantry_fill, 'fill') as fill:
            self.assertTrue(tasks.run_pantry(self.recipe.id))
            fill.assert_called_once()
            images.assert_called_once_with(self.recipe.id)
            with mock.patch.object(pantry_fill, 'make_symbols') as symbols:
                tasks.run_pantry(self.recipe.id, images=False)
            symbols.assert_called_once()  # the new items' symbols, after the fill
            self.assertEqual(images.call_count, 1)
            fill.side_effect = RuntimeError('overloaded')
            with self.assertRaises(RuntimeError):
                tasks.run_pantry(self.recipe.id, attempt=0)  # Cloud Tasks tries again
            self.assertTrue(tasks.run_pantry(self.recipe.id, attempt=tasks.MAX_ATTEMPTS - 1))
            self.assertEqual(images.call_count, 2)  # the images come anyway
        recipe = db.session.get(Recipe, self.recipe.id)
        self.assertEqual([e['rule'] for e in recipe.validation_errors], ['pantry'])
        self.assertNotIn('overloaded', recipe.validation_errors[0]['message'])

    def test_a_made_recipe_with_unlinked_lines_queues_the_pantry_job_first(self):
        with mock.patch.object(tasks, 'configured', return_value=True), \
                mock.patch.object(tasks, 'enqueue_pantry') as pantry, mock.patch.object(tasks, 'enqueue_images') as images, \
                mock.patch('services.recipe_v2.generate.create_recipe'):
            self.recipe.status = 'generating'
            db.session.commit()
            tasks.run(self.recipe.id, 'idea', 'Carbonara', images=False)
        pantry.assert_called_once_with(self.recipe.id, False)
        images.assert_not_called()

    def test_the_task_endpoint_needs_the_queue_token(self):
        client = app.test_client()
        url = f'/internal/tasks/recipe-v2-pantry/{self.recipe.id}'
        self.assertEqual(client.post(url, json={}).status_code, 401)
        with mock.patch.object(tasks, 'verified', return_value=True), mock.patch.object(tasks, 'run_pantry') as run:
            self.assertEqual(client.post(url, json={'images': False}, headers={'Authorization': 'Bearer ok'}).status_code, 200)
        self.assertEqual(run.call_args.kwargs['images'], False)

    def test_new_items_get_their_symbol_image_and_a_failure_leaves_one_without(self):
        pantry_fill.fill(self.recipe, call=answer([decision('pecorino romano', 'new', new=PECORINO),
                                                   decision('vann', 'new', new=dict(PECORINO, name='water'))]))
        db.session.commit()
        items = pantry_fill.without_symbol(self.recipe)
        self.assertEqual([i.name for i in items], ['pecorino romano', 'water'])
        self.assertEqual(pantry_fill.without_symbol(), items)  # the items of every recipe
        self.pasta.data_source = 'usda'
        saved = []
        storage = SimpleNamespace(save=lambda data, name, folder: saved.append((name, folder)) or f'https://b/{folder}/{name}')

        def draw(ing):
            if ing.name == 'water':
                raise RuntimeError('quota')
            from io import BytesIO
            from PIL import Image
            out = BytesIO()
            Image.new('RGB', (8, 8)).save(out, 'PNG')
            return out.getvalue(), 'a prompt', {}
        made = pantry_fill.make_symbols(items, storage, draw=draw)
        self.assertEqual(made, ['pecorino romano'])
        self.assertEqual(saved[0][1], 'pantry/symbols')
        self.assertTrue(items[0].image_url.startswith('https://b/pantry/symbols/auto-'))
        self.assertIsNone(items[1].image_url)
        self.assertEqual([i.name for i in pantry_fill.without_symbol()], ['water'])

    def test_ids_for_the_script(self):
        self.assertEqual(parse_ids('337-340, 345'), [337, 338, 339, 340, 345])


if __name__ == '__main__':
    unittest.main()
