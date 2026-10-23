"""Cooking mode: what each step needs (services/recipe_v2/view.cook_needs) and the page."""
import os
import re
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(ROOT)

from tests import test_recipe_v2_view as view_tests  # noqa: E402  (sets the test environment)
from database.models import Recipe, db  # noqa: E402
from services.recipe_v2.view import build  # noqa: E402


class CookTests(unittest.TestCase):
    setUp, tearDown, page = (view_tests.RecipeV2ViewTests.setUp, view_tests.RecipeV2ViewTests.tearDown,
                             view_tests.RecipeV2ViewTests.page)

    def steps(self, name):
        return {s['short']: s for s in build(db.session.get(Recipe, self.ids[name]))['steps']}

    def test_each_step_gets_its_bowls_lines_and_results(self):
        s = self.steps('carbonara')
        stir = s['Rør inn eggeblandingen']
        self.assertEqual([b['name'] for b in stir['bowls']], ['Pisk eggeblandingen'])
        self.assertEqual([(r['no'], r['short']) for r in stir['results']], [(7, 'Vend pastaen i fettet')])
        self.assertEqual([t['name'] for t in s['Kok pastaen']['tiles']], ['spaghetti'])
        # The boiling water is a result for the pasta, from the setup step that used it
        self.assertEqual([r['no'] for r in s['Kok pastaen']['results']], [1])

    def test_prep_done_in_prep_is_marked_and_not_a_result(self):
        s = self.steps('carbonara')
        self.assertTrue(s['Pisk eggeblandingen']['ahead'])
        self.assertTrue(s['Skjær guancialen']['ahead'])
        self.assertFalse(s['Kok pastaen']['ahead'])
        self.assertEqual(s['Stek guancialen']['results'], [])  # the cut guanciale comes as bowl 1
        self.assertEqual([b['no'] for b in s['Stek guancialen']['bowls']], [1])

    def test_the_step_standing_while_this_one_is_done(self):
        s = self.steps('carbonara')
        self.assertEqual(s['Ta av pastavann']['standing']['short'], 'Stek guancialen')
        self.assertEqual(s['Kok pastaen']['passive_min'], 9)

    def test_the_page(self):
        res = self.client.get(f'/recipe/{self.ids["carbonara"]}/cook', query_string={'servings': 6})
        html = res.get_data(as_text=True)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(re.findall(r'<article class="card ', html)), 9)
        self.assertEqual(len(re.findall(r'<article class="card [^>]*data-ahead', html, re.S)), 2)
        for text in ('js/cook.js', 'You need', 'from step 7', 'Done when', 'Start, then next', '600 g',
                     'class="cook-side"', 'data-passive="9"'):
            self.assertIn(text, html)

    def test_prep_leads_to_cooking(self):
        html = self.client.get(f'/recipe/{self.ids["carbonara"]}/prep').get_data(as_text=True)
        self.assertIn(f'/recipe/{self.ids["carbonara"]}/cook?servings=4&amp;plan=calm', html)
        _, overview = self.page('carbonara')
        self.assertIn(f'/recipe/{self.ids["carbonara"]}/cook?', overview)

    def test_one_page_flow_is_for_admins_and_has_the_dish_and_the_steps_as_a_list(self):
        rid = self.ids["carbonara"]
        self.client.set_cookie('flow', 'one')
        html = self.client.get(f'/recipe/{rid}').get_data(as_text=True)
        self.assertIn('>Prep</a>', html)  # visitors get the tabs, whatever the cookie says
        self.assertNotIn('Start cooking', html)
        self.assertTrue(self.client.get(f'/recipe/{rid}/make').headers['Location'].endswith(f'/recipe/{rid}'))
        self.client.post('/login', data={'email': 'admin@test', 'password': 'pw'})
        self.client.set_cookie('flow', 'tabs')
        self.assertIn('>Prep</a>', self.client.get(f'/recipe/{rid}').get_data(as_text=True))
        # An admin who picks the one page gets Overview, Prep and Cook on the recipe's own page, with no tabs
        self.client.set_cookie('flow', 'one')
        html = self.client.get(f'/recipe/{rid}?servings=2').get_data(as_text=True)
        for text in ('class="factbar"', 'id="ings-h"', 'Get ready', 'class="heat-line"', 'Heat on', 'class="st ', 'data-start',
                     'data-view="timeline"', 'data-view="delta"', 'id="sheet-bowls"', 'data-bowl', 'js/ready.js', 'js/steps.js',
                     'js/kitchen.js', 'Versions'):
            self.assertIn(text, html)
        self.assertNotIn('class="flowbar"', html)
        self.assertNotIn('js/cook.js', html)
        # The steps in the order of the plan, numbered, and the line before the first step that heats the food
        rows = re.findall(r'class="(st [a-z ]+|heat-line)"', html)
        line = rows.index('heat-line')
        self.assertTrue(line > 0 and all(r.startswith('st ') for r in rows[:line] + rows[line + 1:]))
        self.assertEqual(re.findall(r'data-n="(\d+)"', html), [str(k) for k in range(1, len(rows))])
        self.assertEqual(html.count('data-servings-form'), 1)
        # Prep, Cook and the old address lead to it, at their part of the page
        for path, end in (('/prep', '#prep'), ('/cook', '#cook'), ('/make', '')):
            location = self.client.get(f'/recipe/{rid}{path}?servings=2').headers['Location']
            self.assertTrue(location.endswith(f'/recipe/{rid}?servings=2{end}'), location)

    def test_drafts_only_for_admins(self):
        url = f'/recipe/{self.ids["lasagne"]}/cook'
        self.assertEqual(self.client.get(url).status_code, 302)
        self.client.post('/login', data={'email': 'admin@test', 'password': 'pw'})
        self.assertEqual(self.client.get(url).status_code, 200)


if __name__ == '__main__':
    unittest.main()
