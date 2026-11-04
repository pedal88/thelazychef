"""The report of pantry links nobody has looked at, and removing aliases (scripts/pantry_links.py)."""
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

from app import app  # noqa: E402
from database.models import Ingredient, IngredientAlias, Recipe, db  # noqa: E402
from scripts import pantry_links  # noqa: E402
from services.recipe_v2.store import save_v2  # noqa: E402

with open(os.path.join(ROOT, 'data', 'pilot_v2', 'fasit', 'carbonara.json'), encoding='utf-8') as f:
    CARBONARA = json.load(f)


class PantryLinksTests(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        self.ctx = app.app_context()
        self.ctx.push()
        db.drop_all()
        db.create_all()
        self.butter = Ingredient(food_id='b1', name='butter', status='active')
        self.pasta = Ingredient(food_id='p1', name='spaghetti', status='active')
        db.session.add_all([self.butter, self.pasta])
        self.draft = Recipe(title='Draft', cuisine='Italian', difficulty='Simplistic', status='draft')
        self.public = Recipe(title='Public', cuisine='Italian', difficulty='Simplistic', status='approved')
        db.session.add_all([self.draft, self.public])
        save_v2(self.draft, CARBONARA)
        save_v2(self.public, CARBONARA)
        db.session.flush()
        for recipe in (self.draft, self.public):
            next(line for line in recipe.lines if line.name == 'vann').ingredient = self.butter  # an alias
            next(line for line in recipe.lines if line.name == 'salt').ingredient = self.butter  # the model's own link
            next(line for line in recipe.lines if line.name == 'spaghetti').ingredient = self.pasta  # the same food
        db.session.add(IngredientAlias(ingredient=self.butter, name='vann'))
        db.session.add(IngredientAlias(ingredient=self.pasta, name='pasta'))  # not by the job
        self.draft.validation_errors = [{'rule': 'pantry', 'message': '"vann" is now an alias of butter (close enough)'}]
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def aliases(self):
        return db.session.execute(db.select(IngredientAlias)).scalars().all()

    def recipes(self):
        return db.session.execute(db.select(Recipe).order_by(Recipe.id)).scalars().all()

    def test_the_report_finds_the_jobs_aliases_and_the_silent_links(self):
        text = '\n'.join(pantry_links.report(self.recipes(), self.aliases()))
        self.assertIn('- vann -> butter: 2 lines, close enough', text)
        self.assertNotIn('- pasta ->', text)  # an alias from elsewhere
        self.assertIn(f'- salt -> butter: {self.draft.id}, {self.public.id}', text)
        self.assertNotIn('- spaghetti ->', text)  # its name matches
        self.assertNotIn('- vann -> butter: 1', text.split('LINES LINKED')[1])  # an alias explains the link

    def test_removing_an_alias_unlinks_drafts_and_leaves_approved_recipes(self):
        removed, ids = pantry_links.remove({'vann', 'nothing like it'}, self.aliases(), self.recipes())
        db.session.commit()
        self.assertEqual(removed, ['vann'])
        self.assertEqual(ids, [self.draft.id])
        self.assertEqual([a.name for a in self.aliases()], ['pasta'])
        self.assertIsNone(next(line for line in self.draft.lines if line.name == 'vann').ingredient_id)
        self.assertEqual(next(line for line in self.public.lines if line.name == 'vann').ingredient_id, self.butter.id)


if __name__ == '__main__':
    unittest.main()
