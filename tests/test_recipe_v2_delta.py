"""The river delta: the drawing decided from the graph (services/recipe_v2/delta.py), on the recipe page and on A4."""
import json
import os
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(ROOT)

from tests import test_recipe_v2_view as view_tests  # noqa: E402  (sets the test environment)
from services.recipe_v2 import delta  # noqa: E402
from services.recipe_v2.planner import plan_v2  # noqa: E402


def drawing(name):
    v2 = view_tests.fasit(name)
    lines = {i['local_id']: {'name': i['name'], 'img': None, 'amount': '', 'prep': '', 'cut': i.get('cut')}
             for i in v2['ingredients']}
    return v2, delta.build(v2, plan_v2(v2, 'calm')['order'], lines)


def node(d, sid):
    return next(n for n in d['nodes'] if n['id'] == sid)


class DeltaModelTests(unittest.TestCase):
    def test_prep_steps_fold_into_the_step_that_uses_them(self):
        v2, d = drawing('carbonara')
        self.assertEqual(len(d['nodes']), 6)
        shown = {s['id'] for n in d['nodes'] for s in n['chain']}
        # Cutting the guanciale and whisking the eggs are not steps of their own in the drawing
        self.assertEqual({s['local_id'] for s in v2['steps']} - shown, {'s2', 's3'})
        self.assertEqual(len(node(d, 's8')['bowls']), 1)  # the egg mixture is a field of what goes in the bowl

    def test_a_step_without_ingredients_joins_the_step_before_it(self):
        _, d = drawing('carbonara')
        self.assertEqual([s['label'] for s in node(d, 's5')['chain']], ['kok pastaen', 'ta av pastavann'])

    def test_numbers_are_the_numbers_of_the_method_list(self):
        for name in ('carbonara', 'lasagne', 'brownies', 'burger', 'tikka'):
            v2, d = drawing(name)
            order = plan_v2(v2, 'calm')['order']
            for n in d['nodes']:
                for s in n['chain']:
                    self.assertEqual(s['no'], order.index(s['id']) + 1, (name, s['id']))

    def test_the_main_line_runs_from_the_first_steps_to_the_dish(self):
        _, d = drawing('lasagne')
        self.assertEqual(d['max_depth'], 4)
        self.assertEqual(d['leaves'], 3)
        root = next(n for n in d['nodes'] if n['depth'] == 0)
        self.assertTrue(root['main'])
        self.assertEqual(root['span'], [0, d['leaves']])
        self.assertEqual(len(d['edges']), len(d['nodes']) - 1)  # a tree: every drawn step has one arrow out

    def test_the_oven_is_a_note_where_it_is_needed(self):
        _, d = drawing('lasagne')
        bake = node(d, 's8')
        self.assertEqual([s['label'] for s in bake['chain']], ['legg', 'stek lasagnen', 'hvil'])
        self.assertEqual(bake['notes'], ['forvarm ovnen 200°'])

    def test_a_long_side_branch_is_started_first(self):
        _, d = drawing('tikka')
        self.assertTrue(node(d, 's3')['early'])  # the marinade
        self.assertFalse(node(d, 's12')['early'])

    def test_no_steps_no_drawing(self):
        self.assertIsNone(delta.build({'steps': []}, [], {}))

    def test_labels(self):
        self.assertEqual(delta.label({'verb': 'Brun', 'short': 'Brun kjøttdeigen'}, True, []), 'brun')
        # Without pictures, or when the neighbour has the same verb, the short name says what it is
        self.assertEqual(delta.label({'verb': 'Brun', 'short': 'Brun kjøttdeigen'}, False, []), 'brun kjøttdeigen')
        self.assertEqual(delta.label({'verb': 'stek', 'short': 'Stek kjøttet'}, True, ['stek']), 'stek kjøttet')
        self.assertEqual(delta.label({'verb': 'cook', 'short': 'Cook the rice'}, True, []), 'cook the rice')
        self.assertEqual(delta.label({'verb': 'kok', 'short': 'Kok opp en stor kjele med vann'}, False, []), 'kok vann')


class DeltaPageTests(unittest.TestCase):
    setUp, tearDown, page = (view_tests.RecipeV2ViewTests.setUp, view_tests.RecipeV2ViewTests.tearDown,
                             view_tests.RecipeV2ViewTests.page)

    def test_cooking_mode_shows_the_delta_and_the_overview_prints_it(self):
        status, html = self.page('carbonara')
        self.assertEqual(status, 200)
        self.assertIn(f'/recipe/{self.ids["carbonara"]}/print?orient=landscape', html)
        self.assertIn('class="delta"', html)
        self.assertIn('data-tick="s8"', html)
        self.assertIn('js/delta.js', html)
        # the edges the browser draws
        self.assertIn('data-edges="[[', html)

    def test_print_page(self):
        res = self.client.get(f'/recipe/{self.ids["carbonara"]}/print', query_string={'orient': 'landscape', 'servings': 6})
        html = res.get_data(as_text=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn('size: A4 landscape', html)
        self.assertIn('data-print="landscape" data-autoprint="1"', html)
        self.assertIn('6 servings', html)
        self.assertNotIn('class="delta-head"', html)  # no buttons on paper
        res = self.client.get(f'/recipe/{self.ids["carbonara"]}/print', query_string={'orient': 'sideways', 'auto': 0})
        html = res.get_data(as_text=True)
        self.assertIn('size: A4 portrait', html)
        self.assertNotIn('data-autoprint', html)

    def test_drafts_print_only_for_admins(self):
        url = f'/recipe/{self.ids["lasagne"]}/print'
        self.assertEqual(self.client.get(url).status_code, 302)
        self.client.post('/login', data={'email': 'admin@test', 'password': 'pw'})
        self.assertEqual(self.client.get(url).status_code, 200)


if __name__ == '__main__':
    unittest.main()
