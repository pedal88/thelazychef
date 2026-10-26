"""Phase 0b pilot: the Claude schema, the prompt split, and the checks for the phase 0 findings.

No model is called.
"""
import json
import os
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path[:0] = [ROOT, os.path.join(ROOT, 'scripts')]
os.environ.setdefault('GOOGLE_API_KEY', 'test-key')

import pilot_v2b as b  # noqa: E402
from services.recipe_v2_validator import validate_recipe_v2  # noqa: E402


def fasit(name):
    with open(os.path.join(ROOT, 'data', 'pilot_v2', 'fasit', name + '.json'), encoding='utf-8') as f:
        return json.load(f)


class PilotV2bTests(unittest.TestCase):
    def test_schema_closes_every_object(self):
        def objects(node):
            if isinstance(node, dict):
                if node.get('type') == 'object':
                    yield node
                for v in node.values():
                    yield from objects(v)
            elif isinstance(node, list):
                for v in node:
                    yield from objects(v)

        found = list(objects(b.recipe_json_schema()))
        self.assertGreaterEqual(len(found), 4)
        self.assertTrue(all(o['additionalProperties'] is False for o in found))
        # Every required field is also allowed: the recipe's title is a property, not a label to strip
        self.assertTrue(all(set(o.get('required') or []) <= set(o['properties']) for o in found))
        from services.recipe_v2 import claude
        self.assertIn('title', b.recipe_json_schema()['properties'])
        self.assertIn('title', claude.recipe_json_schema()['properties'])

    def test_prompt_splits_into_cached_rules_and_source(self):
        _, prompt = b.p0.structure_prompt('db-1', 'Title: Toast')
        system, user = b.split_prompt(prompt)
        self.assertIn('RULES FOR STEPS', system)
        self.assertNotIn('Title: Toast', system)
        self.assertTrue(user.startswith('SOURCE RECIPE') and user.endswith('Title: Toast'))

    def test_findings_on_the_reference_recipes(self):
        for name in ('brownies', 'burger', 'carbonara', 'lasagne', 'tikka'):
            f = b.findings(fasit(name))
            self.assertEqual((f['bad_components'], f['final_not_serve'], f['loose_equipment_steps'], f['no_preheat']),
                             ([], 0, 0, 0), name)

    def test_findings_catch_the_phase_0_problems(self):
        r = fasit('lasagne')
        r['components'][0]['name'] = 'Assembly and Garnish'
        step = next(s for s in r['steps'] if s['uses'])
        step['text'] += f" {{{step['uses'][0]}}} på hver."
        self.assertEqual(b.findings(r)['bad_components'], ['Assembly and Garnish'])
        self.assertEqual(b.findings(r)['each_with_total'], 1)

    def test_no_preheat_warning(self):
        r = fasit('lasagne')
        bake = next(s for s in r['steps'] if not s.get('setup') and (s.get('equipment') or [None])[0] == 'oven')
        bake['temp_c'] = 225
        codes = [w['code'] for w in validate_recipe_v2(r)['warnings']]
        self.assertIn('no_preheat', codes)

    def test_faithfulness_by_pantry_id(self):
        source = {'ingredients': [{'food_id': '1', 'amount': 100}, {'food_id': '2', 'amount': 2}]}
        recipe = {'ingredients': [{'pantry_id': '1', 'amount': 60}, {'pantry_id': '1', 'amount': 40},
                                  {'pantry_id': '3', 'amount': 1}]}
        self.assertEqual(b.faithfulness(recipe, source), {'missing': ['2'], 'added': ['3'], 'amount_changed': []})


if __name__ == '__main__':
    unittest.main()
