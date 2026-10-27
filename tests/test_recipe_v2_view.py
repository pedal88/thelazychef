"""The recipe page for v2 recipes: overview, shopping list and the steps in planned order."""
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
from database.models import Ingredient, Recipe, User, db  # noqa: E402
from services.recipe_v2.store import save_v2  # noqa: E402
from services.recipe_v2.view import fmt_amount, frac  # noqa: E402


def fasit(name):
    with open(os.path.join(ROOT, 'data', 'pilot_v2', 'fasit', name + '.json'), encoding='utf-8') as f:
        return json.load(f)


class RecipeV2ViewTests(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        self.ctx = app.app_context()
        self.ctx.push()
        db.drop_all()
        db.create_all()
        admin = User(email='admin@test', is_admin=True)
        admin.set_password('pw')
        spaghetti = Ingredient(food_id='000322', name='spaghetti', status='active', default_unit='g',
                               main_category='pasta', image_url='https://example.com/spaghetti.webp')
        db.session.add_all([admin, spaghetti])
        db.session.flush()
        self.ids = {}
        for name, status in (('carbonara', 'approved'), ('tikka', 'approved'), ('lasagne', 'draft')):
            data = fasit(name)
            r = Recipe(title=data['title'], status=status, cuisine='', difficulty='', chef_id='gourmet', language='nb')
            db.session.add(r)
            links = {i['local_id']: spaghetti.id for i in data['ingredients'] if i['name'] == 'spaghetti'}
            save_v2(r, data, links)
            self.ids[name] = r
        db.session.commit()
        self.ids = {k: r.id for k, r in self.ids.items()}
        self.client = app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def page(self, name, part='', **args):
        res = self.client.get(f'/recipe/{self.ids[name]}{part}', query_string=args)
        return res.status_code, res.get_data(as_text=True)

    def test_page_shows_overview_and_shopping_list(self):
        status, html = self.page('carbonara')
        self.assertEqual(status, 200)
        for text in ('Spaghetti carbonara', 'Ingredients', '26 min', 'data-cook-open', 'id="sheet-more"'):
            self.assertIn(text, html)
        self.assertIn('https://example.com/spaghetti.webp', html)  # the pantry symbol
        # The shopping list in kitchen groups, the staples last
        self.assertIn('class="shop-group"', html)
        self.assertLess(html.index('spaghetti.webp'), html.index('You probably have'))
        # The steps are on the cooking screen of the same page, in planned order: boil the water first, serve last
        cook = html[html.index('id="cook"'):]
        self.assertIn('400 g spaghetti', cook)
        self.assertIn('Done when', cook)
        self.assertLess(cook.index('Kok opp vann'), cook.index('>Server<'))

    def test_servings_scale_the_amounts(self):
        _, html = self.page('carbonara', servings=6)
        self.assertIn('name="servings" value="6"', html)
        self.assertIn('servings=6&amp;plan=prep', html)  # the plan links keep the servings
        # The amounts for 6
        self.assertIn('data-amounts=\'[[600.0, "g"]]\'', html)
        self.assertIn('600 g spaghetti', html[html.index('id="cook"'):])

    def test_the_state_follows_the_ingredient_in_cook_steps(self):
        _, html = self.page('tikka')
        self.assertIn('3 cloves hvitløk</span> <span class="prep">(fint revet)</span>', html)  # the state and grade in the recipe's language
        self.assertIn('used 2 times', html)  # garlic in the marinade and in the sauce

    def test_the_plan_can_be_changed(self):
        _, calm = self.page('carbonara', plan='calm')
        _, prep = self.page('carbonara', plan='prep')
        self.assertIn('aria-current="true">Calm', calm)
        self.assertIn('aria-current="true">Prep first', prep)

    def test_drafts_are_hidden_from_visitors_and_marked_for_admins(self):
        status, _ = self.page('lasagne')
        self.assertEqual(status, 302)
        self.client.post('/login', data={'email': 'admin@test', 'password': 'pw'})
        status, html = self.page('lasagne')
        self.assertEqual(status, 200)
        self.assertIn('Only admins can see this recipe', html)
        self.assertIn('not in the pantry', html)

    def test_amount_formatting(self):
        self.assertEqual(frac(1.5), '1½')
        self.assertEqual(frac(0.25), '¼')
        self.assertEqual(fmt_amount(2, 'clove'), '2 cloves')
        self.assertEqual(fmt_amount(1, 'clove'), '1 clove')
        self.assertEqual(fmt_amount(3, 'piece'), '3')
        self.assertEqual(fmt_amount(1.5, 'tbsp'), '1½ tbsp')
        self.assertEqual(fmt_amount(437, 'g'), '440 g')


class EquipmentListTests(unittest.TestCase):
    def test_supplies_are_left_out_and_merged_items_listed_once(self):
        from services.recipe_v2.view import equipment_list
        items = equipment_list(['wide_pot', 'foil', 'dutch_oven', 'large_bowl', 'bowl', 'sous_vide', 'unknown_thing'])
        self.assertEqual([e['id'] for e in items], ['wide_pot', 'bowl', 'sous_vide', 'unknown_thing'])
        self.assertTrue(next(e for e in items if e['id'] == 'sous_vide')['special'])
        self.assertEqual(items[0]['name'], 'Wide pot')


if __name__ == '__main__':
    unittest.main()
