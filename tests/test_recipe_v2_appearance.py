"""How a dish looks (services/recipe_v2/appearance.py), and the dish image lab task built on it.

Claude is replaced by a fake that answers with fixed JSON, so no model is called.
"""
import json
import os
import sys
import tomllib
import unittest
from types import SimpleNamespace

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(ROOT)
os.environ.setdefault('GOOGLE_API_KEY', 'test-key')

from promptlab.compose import load_task  # noqa: E402
from scripts.dish_image_samples import to_toml  # noqa: E402
from services.recipe_v2.appearance import describe  # noqa: E402

LOOK = {'plating': 'A square portion on a white plate, with salad beside it.',
        'components': [{'name': 'Lasagne', 'appearance': 'Layers of pasta, meat sauce and white sauce under a golden crust.'},
                       {'name': 'grønn salat', 'appearance': 'Torn romaine, cucumber half-moons and halved cherry tomatoes.'},
                       {'name': 'Something else', 'appearance': 'Not visible.'}]}


def fasit(name):
    with open(os.path.join(ROOT, 'data', 'pilot_v2', 'fasit', name + '.json'), encoding='utf-8') as f:
        return json.load(f)


class AppearanceTests(unittest.TestCase):
    def test_parts_are_matched_to_the_components(self):
        asked = []

        def call(model, effort, messages, schema=None, system=None):
            asked.append((messages[0]['content'], schema))
            return SimpleNamespace(content=[SimpleNamespace(type='text', text=json.dumps(LOOK))]), {'cost_usd': 0.01}

        v2 = fasit('lasagne')
        look, usage = describe(v2, call=call)
        prompt, schema = asked[0]
        self.assertIn('Write in English, whatever the language of the recipe', prompt)
        self.assertIn('RECIPE\nLasagne\n\nServings: 4', prompt)
        self.assertEqual(schema['required'], ['plating', 'components'])
        comps = {c['name']: c['local_id'] for c in v2['components']}
        # By name, ignoring case; a part with another name gets the first component left over
        self.assertEqual(look['components'][0]['local_id'], comps['Lasagne'])
        self.assertEqual(look['components'][1], {'local_id': comps['Grønn salat'], 'name': 'Grønn salat',
                                                 'appearance': LOOK['components'][1]['appearance']})
        self.assertEqual(look['components'][2]['local_id'], comps['Kjøttsaus'])
        self.assertEqual(usage['cost_usd'], 0.01)


class DishImageTaskTests(unittest.TestCase):
    def test_the_prompt_is_built_from_the_appearance(self):
        task = load_task('dish_image')
        self.assertEqual(task.aspect, '4:3')
        self.assertEqual(set(task.variants('style')), {'editorial', 'overhead', 'cutout', 'illustrated'})
        sample = {'id': 'lasagne', 'title': 'Lasagne', **LOOK}
        prompt = task.compose({'style': 'overhead'}, sample)
        self.assertTrue(prompt.startswith('One serving of a home-cooked dish'))
        self.assertIn('taken straight from above', prompt)
        self.assertIn('The dish is Lasagne. A square portion on a white plate', prompt)
        self.assertIn('grønn salat: Torn romaine', prompt)

    def test_samples_are_written_as_toml(self):
        sample = {'id': 'lasagne', 'title': 'Lasagne "al forno"', **LOOK}
        data = tomllib.loads(to_toml([sample]))
        self.assertEqual(data['default'][0]['title'], 'Lasagne "al forno"')
        self.assertEqual(data['default'][0]['components'][1]['name'], 'grønn salat')


if __name__ == '__main__':
    unittest.main()
