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
    CollectionItem, Ingredient, Instruction, Recipe, RecipeCollection, RecipeDiet,
    RecipeIngredient, RecipeMealType, SocialMediaPost, User, UserQueue,
    UserRecipeInteraction, db,
)
from services.ingredient_service import merge_ingredients  # noqa: E402
from services.recipe_service import delete_recipes  # noqa: E402


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

    def _ingredient(self, name, **kw):
        ing = Ingredient(food_id=f"id-{name}", name=name, status='active', default_unit='g', **kw)
        db.session.add(ing)
        db.session.flush()
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
        collection = RecipeCollection(title='Weeknight', slug='weeknight')
        db.session.add(collection)
        db.session.flush()
        db.session.add_all([
            RecipeIngredient(recipe_id=recipe.id, ingredient_id=onion.id, amount=100, unit='g'),
            Instruction(recipe_id=recipe.id, phase='prep', step_number=1, text='Chop'),
            RecipeMealType(recipe_id=recipe.id, meal_type='Dinner'),
            RecipeDiet(recipe_id=recipe.id, diet='vegetarian'),
            CollectionItem(collection_id=collection.id, recipe_id=recipe.id),
            UserQueue(user_id=user.id, recipe_id=recipe.id),
            UserRecipeInteraction(user_id=user.id, recipe_id=recipe.id, status='favorite'),
            SocialMediaPost(recipe_id=recipe.id, platform='tiktok', template_name='x.jinja2'),
        ])
        stock = self._ingredient('stock', sub_recipe_id=recipe.id)
        db.session.commit()

        self.assertEqual(delete_recipes([recipe.id]), 1)

        self.assertIsNone(db.session.get(Recipe, recipe.id))
        for model in (RecipeIngredient, Instruction, RecipeMealType, RecipeDiet, CollectionItem,
                      UserQueue, UserRecipeInteraction, SocialMediaPost):
            self.assertEqual(_count(model, recipe_id=recipe.id), 0, model.__name__)
        self.assertIsNone(db.session.get(Ingredient, stock.id).sub_recipe_id)
        self.assertIsNotNone(db.session.get(Ingredient, onion.id))

    def test_delete_ignores_unknown_ids(self):
        self.assertEqual(delete_recipes([999]), 0)

    def test_merge_moves_lines_even_when_recipe_already_has_winner(self):
        recipe = self._recipe()
        winner = self._ingredient('red onion')
        loser = self._ingredient('red onion, diced', aliases='["Red Onion", "rødløk"]')
        db.session.add_all([
            RecipeIngredient(recipe_id=recipe.id, ingredient_id=winner.id, amount=100, unit='g'),
            RecipeIngredient(recipe_id=recipe.id, ingredient_id=loser.id, amount=2, unit='pcs'),
        ])
        db.session.commit()
        loser_id = loser.id

        result = merge_ingredients(winner.id, loser_id)

        self.assertTrue(result['success'], result['message'])
        self.assertIsNone(db.session.get(Ingredient, loser_id))
        lines = db.session.execute(
            db.select(RecipeIngredient).filter_by(recipe_id=recipe.id).order_by(RecipeIngredient.amount)
        ).scalars().all()
        self.assertEqual([(line.ingredient_id, line.amount, line.unit) for line in lines],
                         [(winner.id, 2, 'pcs'), (winner.id, 100, 'g')])

    def test_merge_aliases_are_case_insensitive_and_skip_winner_name(self):
        winner = self._ingredient('red onion', aliases='["rødløk"]')
        loser = self._ingredient('Red onion, diced', aliases='["Red Onion", "RØDLØK", "purple onion"]')
        db.session.commit()

        merge_ingredients(winner.id, loser.id)

        import json
        self.assertEqual(json.loads(db.session.get(Ingredient, winner.id).aliases),
                         ['rødløk', 'Red onion, diced', 'purple onion'])

    def test_merge_keeps_sub_recipe_link_from_loser(self):
        recipe = self._recipe('Chicken stock')
        winner = self._ingredient('chicken stock')
        loser = self._ingredient('chicken broth', sub_recipe_id=recipe.id)
        db.session.commit()

        merge_ingredients(winner.id, loser.id)

        self.assertEqual(db.session.get(Ingredient, winner.id).sub_recipe_id, recipe.id)


if __name__ == '__main__':
    unittest.main()
