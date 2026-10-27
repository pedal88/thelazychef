"""The planner gives the same plans as the prototype.

The expected plans come from the prototype's own code
(scripts/make_planner_golden.mjs): the five reference recipes and the Opus
results from phase 0b, in all three strategies.
"""
import json
import os
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(ROOT)

from services.recipe_v2.planner import plan_v2, steps_from_v2  # noqa: E402
from services.recipe_v2.read import shopping_list  # noqa: E402


def load(*parts):
    with open(os.path.join(ROOT, *parts), encoding='utf-8') as f:
        return json.load(f)


def v2_of(name):
    if name.startswith('fasit/'):
        return load('data', 'pilot_v2', 'fasit', name.split('/', 1)[1])
    return load('data', 'pilot_v2', 'results_0b', *name.split('/'))['recipe']


class PlannerTests(unittest.TestCase):
    golden = load('tests', 'fixtures', 'planner_golden.json')

    def test_same_plans_as_the_prototype(self):
        for name, modes in self.golden.items():
            v2 = v2_of(name)
            for mode, want in modes.items():
                with self.subTest(recipe=name, plan=mode):
                    got = plan_v2(v2, mode)
                    self.assertEqual(got['T'], want['T'])
                    self.assertEqual(got['A'], want['A'])
                    self.assertEqual(got['order'], want['order'])
                    self.assertEqual(got['ahead'], want['ahead'])
                    self.assertEqual(got['over'], want['over'])
                    self.assertEqual(got['me'], want['me'])
                    self.assertEqual((got['cook_start'], got['serve_start']), (want['cookStart'], want['serveStart']))
                    for sid, p in want['plan'].items():
                        g = got['plan'][sid]
                        self.assertEqual((g['start'], g['end'], g['use'], g.get('during')),
                                         (p['start'], p['end'], p['use'], p['during']), sid)

    def test_steps_wait_for_the_setup_step_at_the_same_temperature(self):
        v2 = {'steps': [
            {'local_id': 's1', 'phase': 'cook', 'setup': True, 'equipment': ['oven'], 'temp_c': 200, 'active_minutes': 1, 'passive_minutes': 14},
            {'local_id': 's2', 'phase': 'cook', 'setup': True, 'equipment': ['oven'], 'temp_c': 225, 'active_minutes': 1, 'passive_minutes': 5},
            {'local_id': 's3', 'phase': 'cook', 'equipment': ['oven'], 'temp_c': 225, 'uses': ['i1'], 'active_minutes': 1, 'passive_minutes': 30},
            {'local_id': 's4', 'phase': 'prep', 'equipment': ['form_20x20'], 'active_minutes': 2},
        ]}
        steps = {s.id: s for s in steps_from_v2(v2)}
        self.assertEqual(steps['s3'].waits, ['s2'])
        self.assertTrue(steps['s3'].excl)
        self.assertFalse(steps['s1'].excl)
        self.assertEqual(steps['s4'].waits, [])

    def test_an_air_fryer_with_two_drawers_cooks_two_things_at_once(self):
        def step(sid, after=(), eq=None, active=1, passive=0, phase='cook'):
            return {'local_id': sid, 'phase': phase, 'after': list(after), 'uses': [] if after else [f'i{sid}'],
                    'active_minutes': active, 'passive_minutes': passive, 'equipment': [eq] if eq else [],
                    'temp_c': 200 if eq else None, 'mode': 'high' if eq else None}
        fry = [step('s1', eq='airfryer', passive=8), step('s2', eq='airfryer', passive=8)]
        v2 = {'ingredients': [], 'steps': fry + [step('s9', after=['s1', 's2'], phase='serve', active=2)]}
        both = plan_v2(v2)['plan']
        self.assertLess(both['s1']['start'], both['s2']['end'])  # side by side: only the cook's minute apart
        self.assertEqual(plan_v2(v2)['T'], 12)
        # One drawer (the user's own kitchen over the catalog): one after the other
        self.assertEqual(plan_v2(v2, kitchen={'airfryer': 1})['T'], 20)
        # A third thing waits for a free drawer
        v2['steps'] = fry + [step('s3', eq='airfryer', passive=8), step('s9', after=['s1', 's2', 's3'], phase='serve', active=2)]
        self.assertEqual(plan_v2(v2)['T'], 20)
        # The oven still holds one thing
        v2['steps'] = [dict(s, equipment=['oven']) for s in fry] + [step('s9', after=['s1', 's2'], phase='serve', active=2)]
        self.assertEqual(plan_v2(v2)['T'], 20)

    def test_unknown_plan_is_an_error(self):
        with self.assertRaises(ValueError):
            plan_v2(v2_of('fasit/carbonara.json'), 'fast')


class ShoppingListTests(unittest.TestCase):
    def test_the_same_ingredient_on_two_lines_is_one_entry(self):
        items = {e['name']: e for e in shopping_list(v2_of('fasit/tikka.json'))}
        garlic = items['hvitløk']
        self.assertEqual(garlic['amounts'], [{'amount': 5, 'unit': 'clove'}])
        self.assertEqual((garlic['uses'], garlic['parts']), (2, ['Tikka masala']))

    def test_parts_and_to_taste(self):
        items = {e['name']: e for e in shopping_list(v2_of('fasit/lasagne.json'))}
        self.assertEqual(items['olivenolje']['parts'], ['Kjøttsaus', 'Grønn salat'])
        # Salt and pepper are separate lines (structure rule 2c): pepper only to taste, salt also measured for the white sauce.
        self.assertTrue(items['sort pepper']['to_taste'])
        self.assertEqual(items['sort pepper']['amounts'], [])
        self.assertTrue(items['salt']['to_taste'])
        self.assertEqual(items['salt']['amounts'], [{'amount': 0.5, 'unit': 'tsp'}])

    def test_scaling(self):
        items = {e['name']: e for e in shopping_list(v2_of('fasit/carbonara.json'), factor=1.5)}
        self.assertEqual(items['spaghetti']['amounts'], [{'amount': 600, 'unit': 'g'}])


if __name__ == '__main__':
    unittest.main()
