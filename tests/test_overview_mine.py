"""Saved and Cook next on the recipe page's first screen (components/overview_layouts.html, save_buttons), unsaving
that keeps what else the cook stored about the dish (Made, the rating, the comment), and that note shown again when the
dish is made again (note_card, my_photo, the sheet's Your note, the note button while cooking)."""
import json
import os
import sys
import unittest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

os.environ['DB_BACKEND'] = 'local'
os.environ['DATABASE_URL'] = 'sqlite://'
os.environ['STORAGE_BACKEND'] = 'local'
os.environ.setdefault('SECRET_KEY', 'test-secret')
os.environ.setdefault('GOOGLE_API_KEY', 'test-key')
os.environ.pop('K_SERVICE', None)

from app import app  # noqa: E402
from database.models import Recipe, User, UserQueue, UserRecipeInteraction, db  # noqa: E402
from services.recipe_v2.store import save_v2  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
with open(os.path.join(ROOT, 'data', 'pilot_v2', 'fasit', 'carbonara.json'), encoding='utf-8') as f:
    CARBONARA = json.load(f)


class OverviewMineTests(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        self.ctx = app.app_context()
        self.ctx.push()
        db.drop_all()
        db.create_all()
        self.user = User(email='cook@test')
        self.user.set_password('pw')
        self.recipe = Recipe(title='Carbonara', status='approved', cuisine='Italian', difficulty='Simplistic')
        db.session.add_all([self.user, self.recipe])
        save_v2(self.recipe, CARBONARA)
        db.session.commit()
        self.client = app.test_client()
        self.url = f'/recipe/{self.recipe.id}'

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def login(self):
        self.client.post('/login', data={'email': 'cook@test', 'password': 'pw'})

    def test_only_for_a_signed_in_cook(self):
        self.assertNotIn('data-mine=', self.client.get(self.url).get_data(as_text=True))
        self.login()
        html = self.client.get(self.url).get_data(as_text=True)
        self.assertIn('data-mine="save" aria-pressed="false"', html)
        self.assertIn('data-mine="queue" aria-pressed="false"', html)

    def test_the_buttons_show_what_is_saved_and_queued(self):
        self.login()
        self.assertEqual(self.client.post(f'/api/recipes/{self.recipe.id}/favorite').get_json()['status'], 'added')
        self.assertEqual(self.client.post(f'/api/queue/add/{self.recipe.id}').get_json()['action'], 'added')
        html = self.client.get(self.url).get_data(as_text=True)
        self.assertIn('data-mine="save" aria-pressed="true"', html)
        self.assertIn('>Saved</span>', html)
        self.assertIn('data-mine="queue" aria-pressed="true"', html)
        self.assertIn('>In Cook next</span>', html)

    def test_unsaving_keeps_made_and_the_rating(self):
        self.login()
        self.client.post(f'/api/recipes/{self.recipe.id}/favorite')
        self.client.post(f'/api/interactions/recipe/{self.recipe.id}/cooked')
        self.client.post(f'/api/interactions/recipe/{self.recipe.id}/feedback', data={'rating': '4', 'comment': 'Less salt'})
        self.assertEqual(self.client.post(f'/api/recipes/{self.recipe.id}/favorite').get_json()['status'], 'removed')
        db.session.expire_all()
        mark = db.session.get(UserRecipeInteraction, (self.user.id, self.recipe.id))
        self.assertEqual((mark.status, mark.is_made, mark.made_count, mark.rating, mark.comment), ('pass', True, 1, 4, 'Less salt'))
        self.assertIn('data-mine="save" aria-pressed="false"', self.client.get(self.url).get_data(as_text=True))
        # Saved again, and only saved: unsaving then removes the row as before
        other = Recipe(title='Lasagne', status='approved', cuisine='Italian', difficulty='Simplistic')
        db.session.add(other)
        db.session.commit()
        self.client.post(f'/api/recipes/{other.id}/favorite')
        self.client.post(f'/api/recipes/{other.id}/favorite')
        self.assertIsNone(db.session.get(UserRecipeInteraction, (self.user.id, other.id)))
        self.assertEqual(db.session.execute(db.select(UserQueue)).first(), None)

    def test_the_note_from_last_time_is_on_the_page(self):
        self.login()
        html = self.client.get(self.url).get_data(as_text=True)
        self.assertNotIn('class="ovl-note"', html)
        self.assertNotIn('id="more-mine"', html)
        self.assertNotIn('class="ovl-myphoto"', html)
        self.assertNotIn('data-noted="1"', html)
        self.assertIn('data-st-finished hidden', html)  # the food is ready: back to the recipe (static/js/steps.js)

        self.client.post(f'/api/interactions/recipe/{self.recipe.id}/cooked')
        self.client.post(f'/api/interactions/recipe/{self.recipe.id}/feedback',
                         data={'rating': '4', 'comment': 'Next time 11, 12 and 13 min'})
        mark = db.session.get(UserRecipeInteraction, (self.user.id, self.recipe.id))
        mark.user_photos = ['/static/user_uploads/mine.jpg']
        db.session.commit()
        html = self.client.get(self.url).get_data(as_text=True)
        self.assertIn('class="ovl-note"', html)
        self.assertIn('Next time 11, 12 and 13 min', html)
        self.assertIn('Your note · made once, last', html)
        self.assertIn('aria-label="4 of 5"', html)
        self.assertIn('id="more-mine"', html)
        self.assertIn('data-noted="1"', html)  # the finished card offers Edit your note
        self.assertIn('data-jump="more-mine" aria-label="Your note from last time"', html)  # while cooking
        # The AI image stays the dish's picture; the cook's photo is the small round one
        self.assertIn('class="ovl-myphoto"', html)
        self.assertIn('<img src="/static/user_uploads/mine.jpg" alt="" width="96"', html)
        # and on the card in the Made list
        self.assertIn('class="rcard-mine" src="/static/user_uploads/mine.jpg"',
                      self.client.get('/recipes?view=made').get_data(as_text=True))

        # Another cook sees none of it, nor does a visitor
        other = User(email='other@test')
        other.set_password('pw')
        db.session.add(other)
        db.session.commit()
        self.client.get('/logout')
        self.assertNotIn('Next time 11', self.client.get(self.url).get_data(as_text=True))
        self.client.post('/login', data={'email': 'other@test', 'password': 'pw'})
        self.assertNotIn('Next time 11', self.client.get(self.url).get_data(as_text=True))


if __name__ == '__main__':
    unittest.main()
