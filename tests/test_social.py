"""Slides for TikTok and Instagram posts: what each format shows, that it fits the slide, the address on the last slide,
and who may see the slide pages (services/social.py, routes/social_routes.py)."""
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
from services import social  # noqa: E402
from services.recipe_v2.generate import refresh  # noqa: E402
from services.recipe_v2.store import save_v2  # noqa: E402


class SocialTests(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        self.ctx = app.app_context()
        self.ctx.push()
        db.drop_all()
        db.create_all()
        admin = User(email='admin@test', is_admin=True)
        admin.set_password('pw')
        db.session.add(admin)
        with open(os.path.join(ROOT, 'data', 'pilot_v2', 'fasit', 'tikka.json'), encoding='utf-8') as f:
            data = json.load(f)
        recipe = Recipe(title=data['title'], cuisine='', difficulty='', status='approved', schema_version=2,
                        image_filename='tikka.png')
        db.session.add(recipe)
        save_v2(recipe, data, {})
        db.session.flush()
        refresh(recipe)
        db.session.commit()
        self.recipe = recipe
        self.client = app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def get(self, path, **args):
        return self.client.get(path, query_string=args)

    def kinds(self, fmt, size='ig'):
        response = self.get(f'/social/recipe/{self.recipe.id}/{fmt}', size=size)
        count = int(response.headers['X-Slides'])
        return [self.get(f'/social/recipe/{self.recipe.id}/{fmt}', size=size, slide=n).get_data(as_text=True)
                .split('class="slide size-', 1)[1].split('"', 1)[0].split(' kind-')[1] for n in range(1, count + 1)]

    def test_the_map_post_goes_dish_map_ingredients_steps_address(self):
        self.assertEqual(self.kinds('map'), ['cover', 'map', 'ingredients', 'steps', 'end'])

    def test_the_grid_post_goes_symbols_ingredients_dish_address(self):
        self.assertEqual(self.kinds('grid'), ['collage', 'ingredients', 'dish', 'end'])

    def test_the_grid_post_does_not_name_the_dish_before_the_reveal(self):
        base = f'/social/recipe/{self.recipe.id}/grid'
        first = self.get(base, slide=1).get_data(as_text=True)
        self.assertIn('Can you guess the dinner?', first)
        self.assertNotIn(self.recipe.title, first.split('<main', 1)[1])
        self.assertIn(self.recipe.title, self.get(base, slide=3).get_data(as_text=True))
        caption = self.get(base, caption=1).get_data(as_text=True)
        self.assertNotIn(self.recipe.title, caption)
        self.assertIn('ingredients, one dinner', caption)

    def test_a_slide_is_drawn_at_its_platforms_size_and_kept_out_of_search(self):
        response = self.get(f'/social/recipe/{self.recipe.id}/map', size='tt', slide=1)
        html = response.get_data(as_text=True)
        self.assertIn('width:1080px; height:1920px', html)
        self.assertIn('<meta name="robots" content="noindex">', html)
        self.assertEqual(response.headers['X-Robots-Tag'], 'noindex')
        self.assertIn(self.recipe.title, html)
        self.assertIn('/static/recipes/tikka.png', html)

    def test_a_slide_can_be_drawn_in_a_look_from_the_style_trial(self):
        base = f'/social/recipe/{self.recipe.id}/map'
        html = self.get(base, look='e', slide=1).get_data(as_text=True)
        self.assertIn('<html lang="en" data-look="e">', html)
        self.assertIn('/static/css/themes.css', html)
        self.assertIn('family=Archivo', html)
        for look in (None, 'z'):
            with self.subTest(look=look):
                html = self.get(base, look=look, slide=1).get_data(as_text=True)
                self.assertIn('<html lang="en">', html)
                self.assertNotIn('fonts.googleapis', html)

    def test_the_site_and_the_slides_read_the_looks_fonts_from_one_place(self):
        from routes._shared import LOOK_FONTS
        html = self.client.get('/recipes').get_data(as_text=True)
        self.assertIn(json.dumps(LOOK_FONTS['d']).replace('&', '\\u0026'), html)

    def test_the_last_slide_and_the_caption_give_the_posts_address(self):
        for size, address in (('ig', 'thelazychef.app/ig/4'), ('tt', 'thelazychef.app/tiktok/4')):
            with self.subTest(size=size):
                last = self.get(f'/social/recipe/{self.recipe.id}/map', size=size, code=4, slide=5)
                self.assertIn(address, last.get_data(as_text=True))
                caption = self.get(f'/social/recipe/{self.recipe.id}/map', size=size, code=4, caption=1)
                self.assertEqual(caption.mimetype, 'text/plain')
                self.assertIn(address, caption.get_data(as_text=True))

    def test_wrong_format_size_slide_or_a_draft_is_not_found(self):
        base = f'/social/recipe/{self.recipe.id}'
        self.assertEqual(self.get(f'{base}/poster').status_code, 404)
        self.assertEqual(self.get(f'{base}/map', size='a4').status_code, 404)
        self.assertEqual(self.get(f'{base}/map', slide=9).status_code, 404)
        self.assertEqual(self.get('/social/recipe/999/map').status_code, 404)
        self.recipe.status = 'draft'
        db.session.commit()
        self.assertEqual(self.get(f'{base}/map').status_code, 404)
        self.client.post('/login', data={'email': 'admin@test', 'password': 'pw'})
        self.assertEqual(self.get(f'{base}/map').status_code, 200)

    def test_the_steps_slide_shows_one_more_step_rather_than_and_1_more(self):
        view = {'title': 'Soup', 'total': '20 min', 'parts': [], 'shop_groups': [], 'metro_map': None,
                'steps': [{'short': f'Step {i}', 'duration': '1 min', 'phase': 'cook'} for i in range(11)]}
        steps = social.recipe_slides(view, 'map', None, 'ig')[-2]
        self.assertEqual((len(steps['steps']), steps['more']), (11, 0))
        view['steps'] *= 2
        steps = social.recipe_slides(view, 'map', None, 'ig')[-2]
        self.assertEqual((len(steps['steps']), steps['more']), (10, 12))

    def test_a_grid_takes_the_fewest_columns_that_fit(self):
        self.assertEqual(social.columns(6, 'ig'), 3)
        many = social.columns(30, 'ig')
        room = social.SIZES['ig'][1] - social.GRID_ROOM['ig']
        self.assertLessEqual(-(-30 // many) * (social.WIDTH / many + social.CAPTION + 20), room)
        self.assertGreater(-(-30 // (many - 1)) * (social.WIDTH / (many - 1) + social.CAPTION + 20), room)
        self.assertLessEqual(social.columns(30, 'tt'), many)

    def test_the_map_names_every_station_when_the_names_fit_beside_them(self):
        def stations(gap):
            return {'height': 20 * gap, 'width': 40, 'lanes': [{'name': 'Sauce', 'n': 0}, {'name': 'Rice', 'n': 1}],
                    'stations': [{'id': f's{i}', 'short': f'Step {i}', 'phase': 'cook', 'lane': i % 2,
                                  'y': i * gap, 'final': i == 19, 'merge': False, 'time': '2 min'} for i in range(20)]}
        roomy = social.map_slide(stations(60), 'tt')
        self.assertTrue(roomy['every'])
        self.assertEqual(len(roomy['labels']), 20)
        tight = social.map_slide(stations(8), 'ig')
        self.assertFalse(tight['every'])
        self.assertEqual([label['text'] for label in tight['labels']], ['Sauce', 'Rice', 'Step 19'])
        ys = [label['y'] for label in tight['labels']]
        self.assertTrue(all(b - a >= social.MAP_NAME_GAP for a, b in zip(ys, ys[1:])))

    def test_the_pantry_post_lists_the_foundation_by_group_without_overflowing(self):
        for i in range(60):
            db.session.add(Ingredient(food_id=f'f{i}', name=f'spice {i}', main_category='spices and herbs',
                                      tier='foundation', status='active', image_url=f'https://x/{i}.webp'))
        db.session.add(Ingredient(food_id='salt', name='table salt', main_category='spices and herbs', tier='staple',
                                  status='active'))
        db.session.add(Ingredient(food_id='saffron', name='saffron', main_category='spices and herbs', tier='core',
                                  status='active'))
        db.session.commit()
        slides = social.pantry_slides('ig')
        self.assertEqual(slides[0]['count'], 61)
        self.assertEqual([s['kind'] for s in slides[-2:]], ['coverage', 'end'])
        pages = [s for s in slides if s['kind'] == 'pantry']
        self.assertEqual(sum(len(g['items']) for p in pages for g in p['groups']), 61)
        self.assertEqual(pages[-1]['groups'][-1]['label'], 'You probably have')
        html = self.get('/social/pantry', slide=1).get_data(as_text=True)
        self.assertIn('The 61-ingredient pantry', html)
        self.assertIn('The 100 most used cover 84% of what goes into dinner', html)


if __name__ == '__main__':
    unittest.main()
