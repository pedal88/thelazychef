"""One shop, five dinners: which five the week picks, and the post's slides (services/social_week.py)."""
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
from database.models import Recipe, RecipeMealType, db  # noqa: E402
from services import social_week as week  # noqa: E402
from services.recipe_v2.generate import refresh  # noqa: E402
from services.recipe_v2.store import save_v2  # noqa: E402


def cands(**recipes):
    """{id: {'protein', 'buy'}} from id=(protein, 'a b c')."""
    return {int(k[1:]): {'protein': p, 'buy': frozenset(items.split())} for k, (p, items) in recipes.items()}


class PickTests(unittest.TestCase):
    def test_the_week_needs_the_fewest_things_to_buy(self):
        c = cands(r1=('chicken', 'rice soy a1 a2 a3'), r2=('beef', 'rice soy b1 b2 b3'),
                  r3=('fish', 'rice c1 c2 c3'), r4=('egg', 'soy d1 d2 d3'), r5=('pork', 'rice soy e1 e2 e3'),
                  r6=('shrimp', 'x1 x2 x3 x4 x5 x6'), r7=('lamb', 'y1 y2 y3 y4 y5'))
        picked = week.pick(c)
        self.assertEqual(picked, [1, 2, 3, 4, 5])
        self.assertEqual(week._size(picked, c), 17)

    def test_a_week_does_not_hold_two_near_copies_of_one_dish(self):
        c = cands(r1=('beef', 'rice soy broccoli beef'), r2=('chicken', 'rice soy broccoli beef garlic'),
                  r3=('fish', 'pasta lemon'), r4=('egg', 'bread chives'), r5=('pork', 'potato cabbage'),
                  r6=('veg', 'lentil tomato'))
        picked = week.pick(c)
        self.assertFalse({1, 2} <= set(picked))
        self.assertEqual(len(picked), 5)

    def test_a_week_varies_its_proteins(self):
        c = cands(r1=('chicken', 'a b'), r2=('chicken', 'a c'), r3=('chicken', 'a d'), r4=('chicken', 'a e'),
                  r5=('beef', 'f g h i'), r6=('fish', 'j k l m'), r7=('egg', 'n o p q'))
        picked = week.pick(c)
        proteins = [c[i]['protein'] for i in picked]
        self.assertLessEqual(proteins.count('chicken'), week.WEEK_PER_PROTEIN)
        self.assertGreaterEqual(len(set(proteins)), week.WEEK_PROTEINS)

    def test_no_week_when_no_five_can_vary(self):
        c = cands(r1=('chicken', 'a'), r2=('chicken', 'b'), r3=('chicken', 'c'), r4=('chicken', 'd'),
                  r5=('chicken', 'e'), r6=('chicken', 'f'))
        self.assertEqual(week.pick(c), [])


class WeekPostTests(unittest.TestCase):
    PROTEINS = {'carbonara': 'pork', 'lasagne': 'beef', 'tikka': 'chicken', 'brownies': None, 'burger': 'beef'}

    def setUp(self):
        app.config['TESTING'] = True
        self.ctx = app.app_context()
        self.ctx.push()
        db.drop_all()
        db.create_all()
        self.ids = []
        for name, protein in self.PROTEINS.items():
            with open(os.path.join(ROOT, 'data', 'pilot_v2', 'fasit', f'{name}.json'), encoding='utf-8') as f:
                data = json.load(f)
            recipe = Recipe(title=data['title'], cuisine='', difficulty='', status='approved', schema_version=2,
                            image_filename=f'{name}.png')
            db.session.add(recipe)
            save_v2(recipe, data, {})
            db.session.flush()
            refresh(recipe)
            recipe.protein_type, recipe.prep_time_mins = protein, 20  # refresh() derives them from the recipe
            if 'Dinner' not in recipe.meal_types_list:  # what refresh() derived; the week takes dinners only
                db.session.add(RecipeMealType(recipe_id=recipe.id, meal_type='Dinner'))
            self.ids.append(recipe.id)
        db.session.commit()
        self.client = app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def test_candidates_leave_out_staples_drafts_long_dinners_and_dinners_without_a_picture(self):
        c = week.candidates()
        self.assertEqual(sorted(c), self.ids)
        self.assertTrue(all('salt' not in c[i]['buy'] and 'vann' not in c[i]['buy'] for i in c))
        db.session.get(Recipe, self.ids[0]).status = 'draft'
        db.session.get(Recipe, self.ids[1]).prep_time_mins = week.WEEK_HANDS_ON + 1
        db.session.get(Recipe, self.ids[2]).image_filename = None
        db.session.commit()
        self.assertEqual(sorted(week.candidates()), self.ids[3:])

    def test_candidates_are_dinners_and_not_baby_food(self):
        db.session.get(Recipe, self.ids[0]).age_from_months = 8
        db.session.execute(db.delete(RecipeMealType).where(RecipeMealType.recipe_id == self.ids[1]))
        db.session.add(RecipeMealType(recipe_id=self.ids[1], meal_type='Breakfast'))
        db.session.add(RecipeMealType(recipe_id=self.ids[2], meal_type='Baby Food'))  # marked dinner as well
        db.session.commit()
        self.assertEqual(sorted(week.candidates()), self.ids[3:])

    def test_the_post_goes_cover_list_week_five_days_address(self):
        response = self.client.get('/social/week')
        self.assertEqual(response.status_code, 200)
        count = int(response.headers['X-Slides'])
        kinds = [self.client.get(f'/social/week?slide={n}').get_data(as_text=True)
                 .split(' kind-', 1)[1].split('"', 1)[0] for n in range(1, count + 1)]
        self.assertEqual(kinds, ['week_cover', 'shop', 'week', 'day', 'day', 'day', 'day', 'day', 'end'])

    def test_the_shopping_list_says_how_many_dinners_use_a_thing_and_the_days_say_which(self):
        views = [{'title': f'Dish {i}', 'total': '20 min', 'total_min': 20 + i, 'shop_groups': [
            {'key': 'produce', 'items': [{'name': 'garlic', 'amount': '1', 'img': 'g.webp'},
                                         {'name': f'thing {i}', 'amount': '1', 'img': 't.webp'}]},
            {'key': 'staples', 'items': [{'name': 'salt', 'amount': '', 'img': None}]}]} for i in range(5)]
        slides = week.week_slides(views, [None] * 5)
        cover, shop = slides[0], slides[1]
        self.assertEqual((cover['count'], cover['lines'], cover['fastest'], cover['slowest']), (6, 10, 20, 24))
        self.assertEqual((shop['tiles'][0]['name'], shop['tiles'][0]['times']), ('garlic', 5))
        self.assertEqual(shop['staples'], ['salt'])
        monday = slides[3]
        garlic = next(t for t in monday['tiles'] if t['name'] == 'garlic')
        self.assertEqual(garlic['also'], ['Tue', 'Wed', 'Thu', 'Fri'])
        self.assertTrue(garlic['shared'])

    def test_one_pantry_item_is_one_thing_to_buy_whatever_the_recipes_call_it(self):
        names = ['boneless, skinless chicken thighs', 'chicken thighs', 'chicken thighs (skin on)', 'chicken thighs',
                 'chicken thighs, boned']
        views = [{'title': f'Dish {i}', 'total': '20 min', 'total_min': 20, 'shop_groups': [
            {'key': 'meat', 'items': [{'name': name, 'amount': '1', 'img': 'c.webp', 'pantry_id': 'p47'}]},
            {'key': 'staples', 'items': [{'name': ['ground black pepper', 'black pepper'][i % 2], 'amount': '',
                                          'img': None, 'pantry_id': 'p9'}]}]} for i, name in enumerate(names)]
        slides = week.week_slides(views, [None] * 5)
        shop = slides[1]
        self.assertEqual([(t['name'], t['times']) for t in shop['tiles']], [('chicken thighs', 5)])
        self.assertEqual(shop['staples'], ['black pepper'])
        self.assertEqual(slides[0]['count'], 1)
        self.assertEqual(slides[3]['tiles'][0]['also'], ['Tue', 'Wed', 'Thu', 'Fri'])

    def test_five_chosen_dinners_in_their_order_and_the_caption_names_them(self):
        order = ','.join(str(i) for i in reversed(self.ids))
        first = self.client.get(f'/social/week?ids={order}&slide=4').get_data(as_text=True)
        self.assertIn(db.session.get(Recipe, self.ids[-1]).title, first)
        caption = self.client.get(f'/social/week?ids={order}&caption=1&size=tt&code=4').get_data(as_text=True)
        self.assertIn('thelazychef.app/tiktok/4', caption)
        self.assertIn(db.session.get(Recipe, self.ids[0]).title, caption)

    def test_a_week_that_is_not_five_approved_dinners_is_not_found(self):
        self.assertEqual(self.client.get('/social/week?ids=1,2').status_code, 404)
        self.assertEqual(self.client.get('/social/week?ids=a,b,c,d,e').status_code, 404)
        db.session.get(Recipe, self.ids[0]).status = 'draft'
        db.session.commit()
        ids = ','.join(map(str, self.ids))
        self.assertEqual(self.client.get(f'/social/week?ids={ids}').status_code, 404)
        for r in self.ids[1:]:
            db.session.get(Recipe, r).protein_type = 'beef'
        db.session.commit()
        self.assertEqual(self.client.get('/social/week').status_code, 404)  # nothing left that varies


if __name__ == '__main__':
    unittest.main()
