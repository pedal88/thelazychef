"""Get ready: mise elements derived from the graph (services/recipe_v2/mise.py) and the page that shows them."""
import os
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(ROOT)

from tests import test_recipe_v2_view as view_tests  # noqa: E402  (sets the test environment)
from services.recipe_v2 import mise  # noqa: E402
from services.recipe_v2.planner import plan_v2  # noqa: E402


def ready(name, plan='calm'):
    v2 = view_tests.fasit(name)
    return mise.build(v2, plan_v2(v2, plan), 'nb')


def names(items):
    return [f['line']['name'] for f in items]


class MiseModelTests(unittest.TestCase):
    def test_carbonara(self):
        r = ready('carbonara')
        self.assertEqual([b['name'] for b in r['bowls']], ['Skjær guancialen', 'Pisk eggeblandingen', 'Pecorino romano'])
        self.assertEqual([b['no'] for b in r['bowls']], [1, 2, 3])
        self.assertEqual(names(r['fetch']), ['spaghetti'])
        # Water and salt for the pasta are staples: they stay on the counter, no bowl
        self.assertEqual(names(r['bench']), ['vann', 'salt'])
        eggs = r['bowls'][1]
        self.assertEqual(eggs['used']['short'], 'Rør inn eggeblandingen')
        self.assertEqual(len(eggs['lines']), 4)

    def test_a_step_on_the_clock_is_not_folded_into_a_bowl(self):
        r = ready('burger')
        dough = r['bowls'][0]
        self.assertEqual((dough['name'], dough['used']['short']), ('Elt deigen', 'Hev'))  # kneaded, then it rises
        self.assertNotIn('egg', [i['name'] for i in dough['lines']])  # the egg wash is a bowl of its own

    def test_marinade_and_spice_mix(self):
        r = ready('tikka')
        bowls = {b['name']: b for b in r['bowls']}
        self.assertEqual(bowls['Rør marinaden']['used']['short'], 'Mariner kyllingen')
        self.assertEqual(bowls['Bland krydderet']['why'], 'prep')
        self.assertEqual(bowls['Hvitløk, ingefær og tomatpuré']['why'], 'prep')  # named after its lines, in Norwegian
        # The coriander is chopped while the sauce simmers
        self.assertEqual([(g['while'], [b['name'] for b in g['bowls']]) for g in r['later']], [('Kok sausen', ['Hakk korianderen'])])

    def test_lines_without_a_reason_for_a_bowl_are_taken_out(self):
        r = ready('lasagne')
        self.assertEqual(len(r['fetch']), 11)
        self.assertIn('kjøttdeig av storfe', names(r['fetch']))
        self.assertTrue(all(f['line'].get('amount') is None for f in r['bench']))  # salt and pepper to taste

    def test_the_prep_done_here_is_listed_for_cooking_mode(self):
        r = ready('carbonara')
        v2 = view_tests.fasit('carbonara')
        prep = {s['local_id'] for s in v2['steps'] if s['phase'] == 'prep'}
        self.assertTrue(r['done_here'])
        self.assertTrue(set(r['done_here']) <= prep)

    def test_names_join_in_the_recipe_language(self):
        self.assertEqual(mise.joined(['onion', 'carrot', 'garlic'], 'en'), 'Onion, carrot and garlic')
        self.assertEqual(mise.joined(['løk', 'gulrot'], 'nb'), 'Løk og gulrot')
        self.assertEqual(mise.joined(['a', 'b', 'c', 'd', 'e'], None), 'A, b and 3 more')

    def test_no_steps_nothing_to_get_ready(self):
        self.assertIsNone(mise.build({'steps': [], 'ingredients': []}, {'order': [], 'plan': {}}))


class GetReadyPageTests(unittest.TestCase):
    setUp, tearDown, page = (view_tests.RecipeV2ViewTests.setUp, view_tests.RecipeV2ViewTests.tearDown,
                             view_tests.RecipeV2ViewTests.page)

    def get(self, name, **args):
        res = self.client.get(f'/recipe/{self.ids[name]}/get-ready', query_string=args)
        return res.status_code, res.get_data(as_text=True)

    def test_the_overview_links_to_get_ready(self):
        _, html = self.page('carbonara', servings=6)
        self.assertIn(f'/recipe/{self.ids["carbonara"]}/get-ready?servings=6&amp;plan=calm', html)
        self.assertIn('3 bowls to fill', html)

    def test_the_page_shows_bowls_tiles_and_equipment(self):
        status, html = self.get('carbonara', servings=6)
        self.assertEqual(status, 200)
        for text in ('Get ready', 'Pisk eggeblandingen', 'Take out', 'On the counter', 'Equipment', 'data-tick="b:',
                     '600 g', 'js/ready.js', '0 of 3 bowls ready'):
            self.assertIn(text, html)
        self.assertIn('https://example.com/spaghetti.webp', html)

    def test_drafts_only_for_admins(self):
        self.assertEqual(self.get('lasagne')[0], 302)
        self.client.post('/login', data={'email': 'admin@test', 'password': 'pw'})
        status, html = self.get('lasagne')
        self.assertEqual(status, 200)
        self.assertIn('Later, while:', html)


if __name__ == '__main__':
    unittest.main()
