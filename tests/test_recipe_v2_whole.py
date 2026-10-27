"""The whole dish on the cooking screen: the timeline and the metro map (services/recipe_v2/whole.py)."""
import os
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(ROOT)

from tests import test_recipe_v2_view as view_tests  # noqa: E402  (sets the test environment)
from services.recipe_v2 import whole  # noqa: E402
from services.recipe_v2.planner import plan_v2  # noqa: E402


def views(name):
    v2 = view_tests.fasit(name)
    sch = plan_v2(v2, 'calm')
    comps = {c['local_id']: c['name'] for c in v2['components']}
    return v2, sch, whole.timeline(v2, sch, comps), whole.metro_map(v2, sch, comps)


class WholeDishTests(unittest.TestCase):
    def test_the_timeline_has_every_step_in_the_plan_order(self):
        v2, sch, t, _ = views('carbonara')
        self.assertEqual([r['id'] for r in t['rows']], sch['order'])
        self.assertEqual([r['no'] for r in t['rows']], list(range(1, len(sch['order']) + 1)))
        boil = t['rows'][0]
        self.assertEqual((boil['short'], boil['start']), ('Kok opp vann', 0))
        self.assertIsNotNone(boil['standing'])  # the water heats up on its own
        self.assertEqual(t['total'], sch['T'])

    def test_free_time_and_phase_lines(self):
        _, _, t, _ = views('lasagne')
        self.assertIn(30, [f['minutes'] for f in t['free']])  # while the lasagne is in the oven
        self.assertEqual([p['label'] for p in t['phases']], ['cook', 'serve'])

    def test_the_metro_map_has_a_line_per_part(self):
        v2, sch, _, m = views('lasagne')
        self.assertEqual([l['name'] for l in m['lanes']], ['Kjøttsaus', 'Hvit saus', 'Lasagne', 'Grønn salat'])
        self.assertEqual(sum(1 for s in m['stations'] if s['final']), 1)
        self.assertEqual(m['stations'][-1]['short'], 'Server')
        order = sch['order']
        self.assertTrue(all(s['no'] == order.index(s['id']) + 1 for s in m['stations']))
        ys = [s['y'] for s in m['stations']]
        self.assertEqual(ys, sorted(ys))  # top to bottom in the order you start them

    def test_no_steps_no_views(self):
        self.assertIsNone(whole.timeline({'steps': []}, {'order': [], 'plan': {}, 'T': 0}, {}))
        self.assertIsNone(whole.metro_map({'steps': []}, {'order': [], 'plan': {}, 'T': 0}, {}))


class WholeDishPageTests(unittest.TestCase):
    setUp, tearDown, page = (view_tests.RecipeV2ViewTests.setUp, view_tests.RecipeV2ViewTests.tearDown,
                             view_tests.RecipeV2ViewTests.page)

    def test_cooking_mode_has_the_three_views(self):
        _, html = self.page('carbonara')
        for text in ('data-view="timeline"', 'data-view="metro"', 'data-view="delta"', 'class="tl"', 'class="mt-svg"',
                     'data-delta-flow', 'data-tl-status'):
            self.assertIn(text, html)
        self.assertEqual(html.count('class="tl-row ph-'), 9)

if __name__ == '__main__':
    unittest.main()
