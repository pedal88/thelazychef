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
        self.assertIn('<b class="amt">600 g</b> spaghetti', html)
        self.assertIn('600 g spaghetti', html[html.index('id="cook"'):])

    def test_us_units_follow_the_cookie(self):
        self.client.set_cookie('units', 'us')
        _, html = self.page('carbonara')
        self.assertIn('<b class="amt">14 oz</b> spaghetti', html)  # 400 g
        self.assertIn('data-units="us" aria-pressed="true"', html)  # the switch in the menu
        self.assertIn('staver på ca. ½ in', html)  # the step's own words too (1 cm)
        self.assertIn('Øs opp ¾ cup av vannet', html)  # 2 dl
        self.client.set_cookie('units', 'metric')
        _, html = self.page('carbonara')
        self.assertIn('<b class="amt">400 g</b> spaghetti', html)  # not the cached US page
        self.client.set_cookie('units', 'imperial')  # anything else is metric
        _, html = self.page('carbonara')
        self.assertIn('<b class="amt">400 g</b> spaghetti', html)

    def test_the_nutrition_label_follows_the_system(self):
        r = db.session.get(Recipe, self.ids['carbonara'])
        r.base_servings = 4
        for field, total in (('calories', 2400), ('protein', 100), ('carbs', 300), ('fat', 80), ('saturated_fat', 30),
                             ('fiber', 12), ('sugar', 8), ('sodium_mg', 4000)):
            setattr(r, 'total_' + field, total)
        db.session.commit()
        _, html = self.page('carbonara')
        self.assertIn('<tr><th>Salt</th><td>2.5 g</td></tr>', html)
        self.client.set_cookie('units', 'us')
        _, html = self.page('carbonara')
        self.assertIn('<tr><th>Calories</th><td>600</td></tr>', html)
        self.assertIn('<tr><th>Sodium</th><td>1000 mg</td></tr>', html)
        self.assertNotIn('<th>Salt</th>', html)

    def test_a_signed_in_choice_is_kept_on_the_user(self):
        _, html = self.page('carbonara')
        self.assertIn('data-unit-switch data-units-auto', html)  # nobody chose: the page may pick US for a US time zone
        self.assertEqual(self.client.post('/api/me/units', json={'units': 'us'}).status_code, 302)  # signed out
        self.client.post('/login', data={'email': 'admin@test', 'password': 'pw'})
        self.assertEqual(self.client.post('/api/me/units', json={'units': 'imperial'}).status_code, 400)
        self.assertEqual(self.client.post('/api/me/units', json={'units': 'us'}).get_json(), {'units': 'us'})
        self.assertEqual(db.session.execute(db.select(User.unit_system).where(User.email == 'admin@test')).scalar(), 'us')
        self.client.set_cookie('units', 'metric')  # another device's cookie: the user's choice wins
        _, html = self.page('carbonara')
        self.assertIn('<b class="amt">14 oz</b> spaghetti', html)
        self.assertNotIn('data-unit-switch data-units-auto', html)

    def test_the_ingredients_page_in_us(self):
        html = self.client.get('/ingredients').get_data(as_text=True)
        self.assertIn('Kilojoules', html)
        self.client.set_cookie('units', 'us')
        html = self.client.get('/ingredients').get_data(as_text=True)
        self.assertIn('per 100 g (about 3½ oz)', html)
        self.assertNotIn('Kilojoules', html)

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

    def test_tins_have_us_names(self):
        from services.recipe_v2.view import equipment_list, equipment_text
        self.assertEqual(equipment_list(['springform_24'])[0]['name'], '24 cm springform')
        self.assertEqual(equipment_list(['springform_24'], system='us')[0]['name'], '9-inch springform')
        step = {'equipment': ['form_20x20'], 'temp_c': 175}
        self.assertEqual(equipment_text(step, 'us').split(', ')[:2], ['8-inch square pan', '350 °F'])


if __name__ == '__main__':
    unittest.main()
