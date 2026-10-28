"""The ingredient galaxy's data (routes/explore_routes.py): the category tree as stored, and the category symbols."""
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
from database.models import ConceptVisual, Ingredient, Recipe, db  # noqa: E402
from services.recipe_v2.store import save_v2  # noqa: E402

with open(os.path.join(ROOT, 'data', 'pilot_v2', 'fasit', 'carbonara.json'), encoding='utf-8') as f:
    CARBONARA = json.load(f)


class IngredientGalaxyTests(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        self.ctx = app.app_context()
        self.ctx.push()
        db.drop_all()
        db.create_all()

        def ing(food_id, name, main, sub, image=None, status='active'):
            i = Ingredient(food_id=food_id, name=name, main_category=main, sub_category=sub, image_url=image, status=status)
            db.session.add(i)
            return i

        self.spaghetti = ing('1', 'spaghetti', 'cereal grains and pasta', 'pasta', 'https://b/spaghetti.webp')
        ing('2', 'penne', 'cereal grains and pasta', 'pasta', 'https://b/penne.webp')
        ing('3', 'orzo', 'cereal grains and pasta', 'pasta')
        ing('4', 'apple juice', 'fruit and fruit products', 'juices', 'https://b/apple.webp')
        ing('5', 'orange juice', 'non-alcoholic beverages', 'juices', 'https://b/orange.webp')
        ing('6', 'canned tuna', 'canned and preserved', 'canned\xa0fish\xa0& seafood')
        ing('7', 'canned crab', 'canned and preserved', 'canned fish & seafood')
        ing('8', 'hidden', 'meat', 'beef', status='pending')
        db.session.add(ConceptVisual(concept_type='ingredient_category', concept_name='cereal grains and pasta',
                                     image_url='https://b/grains.webp'))
        db.session.flush()
        for status in ('approved', 'approved', 'draft'):
            r = Recipe(title='Carbonara', cuisine='Italian', difficulty='Simplistic', status=status)
            db.session.add(r)
            save_v2(r, CARBONARA, {'i1': self.spaghetti.id})  # i1 is the spaghetti line
        db.session.commit()
        self.data = app.test_client().get('/api/graph/ingredient-galaxy').get_json()
        self.nodes = {n['id']: n for n in self.data['nodes']}

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def test_the_tree_is_as_stored(self):
        # One node per main and sub category pair: juices under fruit and under drinks are two
        juices = [n for n in self.nodes if n.startswith('sub_') and n.endswith('|juices')]
        self.assertEqual(len(juices), 2)
        # Non-breaking spaces do not make a second canned fish node
        fish = [n for n in self.nodes.values() if n['group'] == 'sub_cat' and 'fish' in n['name']]
        self.assertEqual([n['name'] for n in fish], ['canned fish & seafood'])
        # Pending ingredients are left out
        self.assertNotIn('hidden', [n['name'] for n in self.nodes.values()])

    def test_categories_show_their_symbols(self):
        self.assertEqual(self.nodes['main_cereal grains and pasta']['image'], 'https://b/grains.webp')
        self.assertIsNone(self.nodes['main_canned and preserved']['image'])  # no symbol made yet
        # A sub category shows its most used ingredient: spaghetti is in two approved recipes, penne in none
        pasta = self.nodes['sub_cereal grains and pasta|pasta']
        self.assertEqual((pasta['image'], pasta['uses']), ('https://b/spaghetti.webp', 2))
        self.assertEqual(self.nodes[f'ing_{self.spaghetti.id}']['uses'], 2)
        # Nothing used: the first ingredient with a symbol; none with one: no image
        self.assertEqual(self.nodes['sub_fruit and fruit products|juices']['image'], 'https://b/apple.webp')
        self.assertIsNone(self.nodes['sub_canned and preserved|canned fish & seafood']['image'])

    def test_a_sub_category_symbol_of_its_own_wins(self):
        db.session.add(ConceptVisual(concept_type='ingredient_subcategory', concept_name='pasta', image_url='https://b/own.webp'))
        db.session.commit()
        nodes = {n['id']: n for n in app.test_client().get('/api/graph/ingredient-galaxy').get_json()['nodes']}
        self.assertEqual(nodes['sub_cereal grains and pasta|pasta']['image'], 'https://b/own.webp')

    def test_the_page_uses_the_app_style(self):
        page = app.test_client().get('/explore/ingredient-galaxy').get_data(as_text=True)
        self.assertIn('Ingredient galaxy', page)
        self.assertNotIn('🥦', page)

    def test_every_main_category_has_a_symbol_description(self):
        with open(os.path.join(ROOT, 'data', 'constraints', 'categories.json'), encoding='utf-8') as f:
            mains = json.load(f)['main_categories']
        with open(os.path.join(ROOT, 'data', 'constraints', 'category_symbols.json'), encoding='utf-8') as f:
            looks = json.load(f)['looks']
        self.assertEqual(sorted(looks), sorted(mains))


if __name__ == '__main__':
    unittest.main()
