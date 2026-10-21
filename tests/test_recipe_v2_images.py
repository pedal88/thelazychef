"""Dish and component images (services/recipe_v2/images.py). The image model and Claude are fakes."""
import io
import json
import os
import sys
import unittest
from types import SimpleNamespace
from unittest import mock

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(ROOT)

from tests import test_recipe_v2_view as view_tests  # noqa: E402  (sets the test environment)
from database.models import Recipe, db  # noqa: E402
from services.recipe_v2 import images  # noqa: E402

LOOK = {'plating': 'A square portion on a plate with salad beside it.',
        'components': [{'name': 'Kjøttsaus', 'visible': False, 'appearance': 'Inside the layers.'},
                       {'name': 'Hvit saus', 'visible': False, 'appearance': 'Inside the layers.'},
                       {'name': 'Lasagne', 'visible': True, 'appearance': 'Layers under a golden crust.'},
                       {'name': 'Grønn salat', 'visible': True, 'appearance': 'Torn romaine and cucumber.'}]}


def png(aspect):
    from PIL import Image

    w, h = (40, 30) if aspect == '4:3' else (30, 30)
    out = io.BytesIO()
    Image.new('RGB', (w, h), 'orange').save(out, 'PNG')
    return out.getvalue()


class Fakes:
    """The image model and Claude. verdicts: what the vision checks answer, in order (then ok)."""
    def __init__(self, verdicts=()):
        self.drawn, self.checked, self.verdicts = [], [], list(verdicts)

    def draw(self, prompt, references=None, aspect_ratio='1:1'):
        self.drawn.append({'prompt': prompt, 'references': references, 'aspect': aspect_ratio})
        return png(aspect_ratio), {}

    def call(self, model, effort, messages, schema=None, system=None):
        if 'plating' in schema['properties']:
            answer = LOOK
        else:
            self.checked.append(messages[0]['content'])
            answer = self.verdicts.pop(0) if self.verdicts else {'ok': True, 'missing': []}
        return SimpleNamespace(content=[SimpleNamespace(type='text', text=json.dumps(answer))]), {'cost_usd': 0.01}


class Storage:
    def __init__(self):
        self.saved = {}

    def save(self, data, filename, folder):
        self.saved[f'{folder}/{filename}'] = data
        return filename


class ImageTests(unittest.TestCase):
    setUp, tearDown, page = (view_tests.RecipeV2ViewTests.setUp, view_tests.RecipeV2ViewTests.tearDown,
                             view_tests.RecipeV2ViewTests.page)

    def recipe(self, name):
        return db.session.get(Recipe, self.ids[name])

    def test_the_dish_first_then_each_part_from_it(self):
        r, fakes, storage = self.recipe('lasagne'), Fakes(), Storage()
        report = images.make_images(r, storage, draw=fakes.draw, call=fakes.call)
        dish, *parts = fakes.drawn
        self.assertEqual(dish['aspect'], '4:3')
        self.assertIsNone(dish['references'])
        self.assertIn('isolated on a pure white background', dish['prompt'])  # the provisional style, cutout
        self.assertIn('Lasagne: Layers under a golden crust.', dish['prompt'])
        self.assertNotIn('Inside the layers', dish['prompt'])  # parts not seen on their own are left out
        # Only the parts you can see get an image, made from the dish image
        self.assertEqual([p['aspect'] for p in parts], ['1:1', '1:1'])
        self.assertTrue(all(p['references'] == [png('4:3')] for p in parts))
        self.assertIn('only one part of it: Grønn salat.', parts[1]['prompt'])
        comps = {c.name: c for c in r.components}
        self.assertEqual(comps['Kjøttsaus'].appearance, '')
        self.assertIsNone(comps['Kjøttsaus'].image_filename)
        self.assertEqual(comps['Lasagne'].image_from, r.image_filename)
        self.assertEqual((r.plating, r.image_style), (LOOK['plating'], 'cutout'))
        self.assertEqual(len(storage.saved), 3)
        self.assertTrue(all(k.startswith('recipes/') and k.endswith('.webp') for k in storage.saved))
        self.assertEqual((report['parts'], report['notes']), (2, []))
        # The part checks get the dish image first, then the part
        self.assertEqual(len(fakes.checked), 3)
        self.assertEqual([b['type'] for b in fakes.checked[1]], ['image', 'image', 'text'])

    def test_a_failed_check_tries_once_more_and_keeps_the_note(self):
        r = self.recipe('lasagne')
        fakes = Fakes([{'ok': False, 'missing': ['no salad']}, {'ok': False, 'missing': ['still no salad']}])
        report = images.make_images(r, Storage(), draw=fakes.draw, call=fakes.call)
        self.assertIn('Make sure of this: no salad.', fakes.drawn[1]['prompt'])
        self.assertEqual(report['notes'], ['Dish image: still no salad'])
        self.assertEqual(r.validation_errors[-1], {'rule': 'image', 'message': 'Dish image: still no salad'})
        # Not a validation error of the recipe; the admin sees it with the image button
        db.session.commit()
        self.client.post('/login', data={'email': 'admin@test', 'password': 'pw'})
        _, html = self.page('lasagne')
        self.assertIn('The image check found: Dish image: still no salad', html)
        self.assertNotIn('It did not pass validation', html)

    def test_a_dish_of_one_part_needs_no_part_images(self):
        r, fakes = self.recipe('carbonara'), Fakes()
        report = images.make_images(r, Storage(), draw=fakes.draw, call=fakes.call)
        self.assertEqual((len(fakes.drawn), report['parts']), (1, 0))

    def test_the_description_is_made_once(self):
        r, fakes = self.recipe('lasagne'), Fakes()
        images.make_images(r, Storage(), draw=fakes.draw, call=fakes.call)
        with mock.patch.object(images.appearance, 'describe') as describe:
            images.make_images(r, Storage(), draw=fakes.draw, call=fakes.call)
        describe.assert_not_called()

    def test_the_admin_button_and_the_page(self):
        url = f'/new-recipe/v2/images/{self.ids["lasagne"]}'
        self.assertEqual(self.client.post(url).status_code, 302)  # to the login
        self.assertIsNone(self.recipe('lasagne').image_filename)
        self.client.post('/login', data={'email': 'admin@test', 'password': 'pw'})
        _, html = self.page('lasagne')
        self.assertIn('Make images', html)
        fakes = Fakes()
        with mock.patch.object(images, 'generate_image', fakes.draw), mock.patch.object(images.claude, 'call', fakes.call), \
                mock.patch('routes._shared.get_storage', return_value=Storage()):
            res = self.client.post(url)
        self.assertEqual(res.status_code, 302)
        r = self.recipe('lasagne')
        self.assertTrue(r.image_filename.startswith(f'dish_{r.id}_'))
        _, html = self.page('lasagne')
        self.assertIn('<figure class="hero">', html)
        self.assertIn('class="part-images"', html)
        self.assertIn('Make the images again', html)

    def test_a_trial_style_is_kept_apart_from_the_recipes_own_images(self):
        r, fakes, storage = self.recipe('lasagne'), Fakes(), Storage()
        images.make_images(r, storage, draw=fakes.draw, call=fakes.call)
        own, parts = r.image_filename, {c.local_id: c.image_filename for c in r.components}
        report = images.make_images(r, storage, draw=fakes.draw, call=fakes.call, style='editorial')
        self.assertTrue(report['trial'])
        self.assertIn('An editorial food photograph', fakes.drawn[-3]['prompt'])  # the dish, then two parts
        self.assertEqual((r.image_filename, {c.local_id: c.image_filename for c in r.components}), (own, parts))
        variant = r.image_variants['editorial']
        self.assertIn('_editorial_', variant['dish'])
        self.assertEqual(len(variant['parts']), 2)
        db.session.commit()
        url = f'/recipe/{self.ids["lasagne"]}'
        self.client.post('/login', data={'email': 'admin@test', 'password': 'pw'})
        self.assertIn(own, self.client.get(url).get_data(as_text=True))
        self.client.set_cookie('dish_images', 'editorial')
        html = self.client.get(url).get_data(as_text=True)
        self.assertIn(variant['dish'], html)  # the admin sees the trial style
        self.assertIn('data-img="editorial" aria-pressed="true"', html)
        self.client.set_cookie('dish_images', 'overhead')
        html = self.client.get(url + '/prep').get_data(as_text=True)
        self.assertIn('Make “From above” images', html)  # none in that style yet
        self.client.get('/logout')
        self.client.set_cookie('dish_images', 'editorial')
        html = self.client.get(f'/recipe/{self.ids["carbonara"]}').get_data(as_text=True)
        self.assertNotIn('trialbar', html)  # visitors see neither the switch nor trial images

    def test_make_images_takes_only_known_styles(self):
        self.client.post('/login', data={'email': 'admin@test', 'password': 'pw'})
        res = self.client.post(f'/new-recipe/v2/images/{self.ids["lasagne"]}', data={'style': 'sketchy'})
        self.assertEqual(res.status_code, 400)


if __name__ == '__main__':
    unittest.main()
