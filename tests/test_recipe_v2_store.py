"""Recipe model v2 in the database: save and read back, delete, and merge.

Runs against an in-memory SQLite database with the five hand-made reference
recipes from the pilot (data/pilot_v2/fasit).
"""
import json
import os
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(ROOT)

os.environ['DB_BACKEND'] = 'local'
os.environ['DATABASE_URL'] = 'sqlite://'
os.environ['STORAGE_BACKEND'] = 'local'
os.environ.setdefault('SECRET_KEY', 'test-secret')
os.environ.setdefault('GOOGLE_API_KEY', 'test-key')
os.environ.pop('K_SERVICE', None)

from app import app  # noqa: E402
from database.models import Ingredient, Recipe, RecipeComponent, RecipeLine, RecipeStep, db, recipe_step_after  # noqa: E402
from services.ingredient_service import merge_ingredients  # noqa: E402
from services.recipe_service import delete_recipes  # noqa: E402
from services.recipe_v2.store import save_v2, to_v2  # noqa: E402
from services.recipe_v2_validator import validate_recipe_v2  # noqa: E402

FASIT = ('brownies', 'burger', 'carbonara', 'lasagne', 'tikka')


def fasit(name):
    with open(os.path.join(ROOT, 'data', 'pilot_v2', 'fasit', name + '.json'), encoding='utf-8') as f:
        return json.load(f)


def normalized(data):
    """Comparable form: after and uses are sets (their order is not stored), and absent optional fields are dropped."""
    out = json.loads(json.dumps(data))
    for s in out['steps']:
        s['after'] = sorted(s.get('after') or [])
        s['uses'] = sorted(s.get('uses') or [])
        s['equipment'] = list(s.get('equipment') or [])
        s['setup'] = bool(s.get('setup'))
        for k in list(s):
            if s[k] is None:
                del s[k]
    for i in out['ingredients']:
        i.pop('pantry_id', None)
        for k in list(i):
            if i[k] is None:
                del i[k]
    out.pop('chef_note', None)
    return out


class RecipeV2StoreTests(unittest.TestCase):
    def setUp(self):
        self.ctx = app.app_context()
        self.ctx.push()
        db.drop_all()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def _recipe(self, data):
        recipe = Recipe(title=data['title'], cuisine='', difficulty='', protein_type='', chef_id='gourmet')
        db.session.add(recipe)
        save_v2(recipe, data)
        db.session.commit()
        return recipe.id

    def _count(self, model_or_table, **filters):
        sel = db.select(db.func.count()).select_from(model_or_table)
        return db.session.execute(sel.filter_by(**filters) if filters else sel).scalar()

    def test_reference_recipes_survive_a_round_trip(self):
        for name in FASIT:
            with self.subTest(name):
                data = fasit(name)
                rid = self._recipe(data)
                db.session.expire_all()
                back = to_v2(db.session.get(Recipe, rid))
                self.assertTrue(validate_recipe_v2(back)['valid'], validate_recipe_v2(back)['errors'][:3])
                self.assertEqual(normalized(back), normalized(data))
                self.assertEqual(db.session.get(Recipe, rid).schema_version, 2)

    def test_saving_again_replaces_content_and_bumps_revision(self):
        rid = self._recipe(fasit('carbonara'))
        recipe = db.session.get(Recipe, rid)
        self.assertEqual(recipe.revision, 1)
        save_v2(recipe, fasit('brownies'))
        db.session.commit()
        db.session.expire_all()
        recipe = db.session.get(Recipe, rid)
        self.assertEqual(recipe.revision, 2)
        self.assertEqual([c.name for c in recipe.components], [c['name'] for c in fasit('brownies')['components']])
        self.assertEqual(self._count(RecipeStep), len(fasit('brownies')['steps']))

    def test_pantry_links_are_kept(self):
        egg = Ingredient(food_id='000217', name='eggs', status='active', default_unit='piece')
        db.session.add(egg)
        db.session.flush()
        data = fasit('carbonara')
        egg_line = next(i for i in data['ingredients'] if i['name'] == 'egg')
        recipe = Recipe(title='x', cuisine='', difficulty='', protein_type='', chef_id='gourmet')
        db.session.add(recipe)
        save_v2(recipe, data, {egg_line['local_id']: egg.id})
        db.session.commit()
        back = to_v2(recipe)
        self.assertEqual(next(i for i in back['ingredients'] if i['local_id'] == egg_line['local_id'])['pantry_id'], '000217')

    def test_deleting_the_recipe_removes_every_v2_row(self):
        rid = self._recipe(fasit('lasagne'))
        self.assertGreater(self._count(recipe_step_after), 0)
        self.assertEqual(delete_recipes([rid]), 1)
        for model in (RecipeComponent, RecipeStep, RecipeLine):
            self.assertEqual(self._count(model, recipe_id=rid), 0, model.__name__)
        self.assertEqual(self._count(recipe_step_after), 0)

    def test_merge_moves_v2_lines(self):
        winner = Ingredient(food_id='w', name='garlic', status='active', default_unit='g')
        loser = Ingredient(food_id='l', name='garlic cloves', status='active', default_unit='g')
        db.session.add_all([winner, loser])
        db.session.flush()
        data = fasit('lasagne')
        garlic = next(i for i in data['ingredients'] if i['name'] == 'hvitløk')
        recipe = Recipe(title='x', cuisine='', difficulty='', protein_type='', chef_id='gourmet')
        db.session.add(recipe)
        save_v2(recipe, data, {garlic['local_id']: loser.id})
        db.session.commit()

        result = merge_ingredients(winner.id, loser.id)

        self.assertTrue(result['success'], result['message'])
        line = db.session.execute(db.select(RecipeLine).filter_by(local_id=garlic['local_id'])).scalar_one()
        self.assertEqual(line.ingredient_id, winner.id)
        self.assertIsNone(db.session.get(Ingredient, loser.id))

    def test_deleting_an_ingredient_does_not_unlink_v2_lines(self):
        # In Postgres the foreign key then blocks the delete. SQLite does not enforce
        # foreign keys, so this checks that the ORM leaves the link alone.
        onion = Ingredient(food_id='o', name='onion', status='active', default_unit='g')
        db.session.add(onion)
        db.session.flush()
        data = fasit('lasagne')
        line = next(i for i in data['ingredients'] if i['name'] == 'løk')
        recipe = Recipe(title='x', cuisine='', difficulty='', protein_type='', chef_id='gourmet')
        db.session.add(recipe)
        save_v2(recipe, data, {line['local_id']: onion.id})
        db.session.commit()
        onion_id = onion.id
        db.session.delete(onion)
        db.session.flush()
        stored = db.session.execute(db.select(RecipeLine.ingredient_id).filter_by(local_id=line['local_id'])).scalar_one()
        self.assertEqual(stored, onion_id)
        db.session.rollback()


if __name__ == '__main__':
    unittest.main()
