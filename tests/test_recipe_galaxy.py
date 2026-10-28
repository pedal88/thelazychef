"""The recipe galaxy's data (routes/explore_routes.py): cuisines and proteins show the app's own symbols."""
import os
import sys
import unittest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

os.environ['DB_BACKEND'] = 'local'
os.environ['DATABASE_URL'] = 'sqlite://'
os.environ['STORAGE_BACKEND'] = 'local'
os.environ.setdefault('SECRET_KEY', 'test-secret')
os.environ.setdefault('GOOGLE_API_KEY', 'test-key')

from app import app  # noqa: E402
from database.models import ConceptVisual, Ingredient, Recipe, db  # noqa: E402


class RecipeGalaxyTests(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        self.ctx = app.app_context()
        self.ctx.push()
        db.drop_all()
        db.create_all()
        db.session.add_all([
            Ingredient(food_id='1', name='chicken breast', status='active', image_url='https://b/chicken.webp'),
            Ingredient(food_id='2', name='Lamb chops', status='active', image_url='https://b/lamb.webp'),
            Ingredient(food_id='3', name='eggs', status='pending', image_url='https://b/eggs.webp'),
            ConceptVisual(concept_type='cuisine', concept_name='Italian', image_url='https://b/italian.webp'),
            ConceptVisual(concept_type='main_protein', concept_name='Lamb', image_url='https://b/old-lamb.png'),
            ConceptVisual(concept_type='main_protein', concept_name='Duck', image_url='https://b/duck.png'),
        ])
        for title, cuisine, protein, status in [('Chicken pasta', 'Italian', 'Chicken', 'approved'),
                                                ('Lamb stew', 'Nordic', 'Lamb', 'approved'),
                                                ('Shakshuka', 'Middle Eastern', 'Eggs', 'approved'),
                                                ('Duck breast', 'French', 'Duck', 'approved'),
                                                ('Draft', 'Thai', 'Salmon', 'draft')]:
            db.session.add(Recipe(title=title, cuisine=cuisine, difficulty='Simplistic', status=status, protein_type=protein))
        db.session.commit()
        self.client = app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def test_planets_show_the_apps_symbols_not_flags_or_icons(self):
        data = self.client.get('/api/graph/galaxy').get_json()
        nodes = {n['id']: n for n in data['nodes']}
        self.assertEqual(nodes['attr_cuisine_Italian']['image'], 'https://b/italian.webp')
        self.assertIsNone(nodes['attr_cuisine_Nordic']['image'])  # not made yet: a plain planet, never a flag
        # A protein shows a typical pantry ingredient (main_protein.json symbol_from), in the same style; an older
        # concept image only where no such ingredient has a symbol
        self.assertEqual(nodes['attr_protein_Chicken']['image'], 'https://b/chicken.webp')
        self.assertEqual(nodes['attr_protein_Lamb']['image'], 'https://b/lamb.webp')
        self.assertEqual(nodes['attr_protein_Duck']['image'], 'https://b/duck.png')
        self.assertIsNone(nodes['attr_protein_Eggs']['image'])  # the eggs item is pending
        self.assertNotIn('attr_cuisine_Thai', nodes)  # drafts are not in the galaxy
        text = self.client.get('/api/graph/galaxy').get_data(as_text=True)
        self.assertNotIn('flagcdn', text)
        self.assertNotIn('icons8', text)

    def test_the_orbit_of_one_recipe_uses_the_same_symbols(self):
        rid = db.session.execute(db.select(Recipe.id).where(Recipe.title == 'Chicken pasta')).scalar()
        nodes = {n['id']: n for n in self.client.get(f'/api/graph/orbital/{rid}').get_json()['nodes']}
        self.assertEqual(nodes['attr_cuisine_Italian']['image'], 'https://b/italian.webp')
        self.assertEqual(nodes['attr_protein_Chicken']['image'], 'https://b/chicken.webp')

    def test_the_page_uses_the_app_style(self):
        page = self.client.get('/explore/galaxy').get_data(as_text=True)
        self.assertIn('Recipe galaxy', page)
        self.assertIn('css/galaxy.css', page)
        self.assertNotIn('🍳', page)
        self.assertNotIn('Cuisine Flags', page)

    def test_every_cuisine_has_a_symbol_description(self):
        import json
        from schemas.recipe_v2 import CUISINES
        with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'constraints',
                               'cuisine_symbols.json'), encoding='utf-8') as f:
            self.assertEqual(sorted(json.load(f)['looks']), sorted(CUISINES))


if __name__ == '__main__':
    unittest.main()
