"""Deleting recipes and merging ingredients must not lose or orphan data.

Runs against an in-memory SQLite database. SQLite does not enforce foreign
keys by default, so the tests count child rows directly instead of relying
on the database to complain.
"""
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
from database.models import (  # noqa: E402
    Ingredient, IngredientAlias, Recipe, RecipeDiet,
    RecipeLine, RecipeMealType, User, UserQueue,
    UserRecipeInteraction, db,
)
from services.ingredient_service import add_alias, merge_ingredients  # noqa: E402
from services.recipe_service import _resolve_ingredient, delete_recipes  # noqa: E402


def _count(model, **filters):
    return db.session.execute(
        db.select(db.func.count()).select_from(model).filter_by(**filters)
    ).scalar()


class DataIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.ctx = app.app_context()
        self.ctx.push()
        db.drop_all()
        db.create_all()

    def tearDown(self):
        # Other test modules share the in-memory database; leave it empty.
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def _ingredient(self, name, aliases=(), **kw):
        ing = Ingredient(food_id=f"id-{name}", name=name, status='active', default_unit='g', **kw)
        db.session.add(ing)
        db.session.flush()
        for alias in aliases:
            add_alias(ing, alias)
        return ing

    def _recipe(self, title='Pasta'):
        recipe = Recipe(title=title, cuisine='Italian', difficulty='Easy', protein_type='Vegetarian', chef_id='gourmet')
        db.session.add(recipe)
        db.session.flush()
        return recipe

    def test_delete_removes_every_child_row(self):
        user = User(email='a@b.c')
        user.set_password('pw')
        db.session.add(user)
        recipe = self._recipe()
        onion = self._ingredient('onion')
        db.session.flush()
        db.session.add_all([
            RecipeMealType(recipe_id=recipe.id, meal_type='Dinner'),
            RecipeDiet(recipe_id=recipe.id, diet='vegetarian'),
            UserQueue(user_id=user.id, recipe_id=recipe.id),
            UserRecipeInteraction(user_id=user.id, recipe_id=recipe.id, status='favorite'),
        ])
        stock = self._ingredient('stock', sub_recipe_id=recipe.id)
        db.session.commit()

        self.assertEqual(delete_recipes([recipe.id]), 1)

        self.assertIsNone(db.session.get(Recipe, recipe.id))
        for model in (RecipeMealType, RecipeDiet, UserQueue, UserRecipeInteraction):
            self.assertEqual(_count(model, recipe_id=recipe.id), 0, model.__name__)
        self.assertIsNone(db.session.get(Ingredient, stock.id).sub_recipe_id)
        self.assertIsNotNone(db.session.get(Ingredient, onion.id))

    def test_delete_ignores_unknown_ids(self):
        self.assertEqual(delete_recipes([999]), 0)

    def test_merge_moves_lines_even_when_recipe_already_has_winner(self):
        import json
        from services.recipe_v2.store import save_v2

        recipe = self._recipe()
        winner = self._ingredient('red onion')
        loser = self._ingredient('red onion, diced', aliases=['rødløk'])
        with open(os.path.join(os.path.dirname(__file__), '..', 'data', 'pilot_v2', 'fasit', 'carbonara.json'), encoding='utf-8') as f:
            data = json.load(f)
        first, second = data['ingredients'][:2]
        save_v2(recipe, data, {first['local_id']: winner.id, second['local_id']: loser.id})
        db.session.commit()
        loser_id = loser.id

        result = merge_ingredients(winner.id, loser_id)

        self.assertTrue(result['success'], result['message'])
        self.assertIsNone(db.session.get(Ingredient, loser_id))
        moved = db.session.execute(
            db.select(RecipeLine.ingredient_id).filter(RecipeLine.recipe_id == recipe.id,
                                                       RecipeLine.local_id.in_([first['local_id'], second['local_id']]))
        ).scalars().all()
        self.assertEqual(moved, [winner.id, winner.id])

    def test_merge_moves_aliases_and_adds_loser_name(self):
        winner = self._ingredient('red onion', aliases=['rødløk'])
        loser = self._ingredient('Red onion, diced', aliases=['purple onion'])
        db.session.commit()

        merge_ingredients(winner.id, loser.id)

        self.assertEqual(sorted(db.session.get(Ingredient, winner.id).aliases),
                         ['purple onion', 'red onion, diced', 'rødløk'])
        self.assertEqual(_count(IngredientAlias), 3)

    def test_add_alias_skips_own_name_and_duplicates(self):
        onion = self._ingredient('Red Onion')
        shallot = self._ingredient('shallot')
        self.assertFalse(add_alias(onion, '  red   ONION '))
        self.assertTrue(add_alias(onion, 'Rødløk'))
        self.assertFalse(add_alias(shallot, 'rødløk'))
        self.assertEqual(onion.aliases, ['rødløk'])

    def test_resolver_prefers_exact_name_then_alias(self):
        onion = self._ingredient('spring onion', aliases=['scallion'])
        scallion = self._ingredient('Scallion')
        db.session.commit()

        self.assertEqual(_resolve_ingredient({'name': 'scallion'}).id, scallion.id)
        scallion.status = 'inactive'
        db.session.commit()
        self.assertEqual(_resolve_ingredient({'name': 'Scallion'}).id, onion.id)

    def test_ingredient_names_are_stored_lower_case(self):
        onion = self._ingredient('  Red   Onion ')
        self.assertEqual(onion.name, 'red onion')

    def test_deleting_ingredient_removes_its_aliases(self):
        onion = self._ingredient('spring onion', aliases=['scallion', 'green onion'])
        db.session.commit()
        db.session.delete(onion)
        db.session.commit()
        self.assertEqual(_count(IngredientAlias), 0)

    def test_merge_keeps_sub_recipe_link_from_loser(self):
        recipe = self._recipe('Chicken stock')
        winner = self._ingredient('chicken stock')
        loser = self._ingredient('chicken broth', sub_recipe_id=recipe.id)
        db.session.commit()

        merge_ingredients(winner.id, loser.id)

        self.assertEqual(db.session.get(Ingredient, winner.id).sub_recipe_id, recipe.id)


if __name__ == '__main__':
    unittest.main()
