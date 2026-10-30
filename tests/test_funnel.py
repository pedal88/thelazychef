"""The funnel from TikTok and Instagram: ref codes, the short addresses, where a new user came from, the admin Funnel
page's numbers, and what a shared recipe link shows (services/funnel.py, routes/funnel_routes.py)."""
import datetime
import json
import os
import sys
import unittest
from unittest import mock

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(ROOT)

os.environ['DB_BACKEND'] = 'local'
os.environ['DATABASE_URL'] = 'sqlite://'
os.environ['STORAGE_BACKEND'] = 'local'
os.environ.setdefault('SECRET_KEY', 'test-secret')
os.environ.setdefault('GOOGLE_API_KEY', 'test-key')
os.environ.pop('K_SERVICE', None)

from app import app  # noqa: E402
from database.models import Recipe, ReferralVisit, SocialPost, User, UserRecipeInteraction, db  # noqa: E402
from services import funnel  # noqa: E402
from services.recipe_v2.generate import refresh  # noqa: E402
from services.recipe_v2.store import save_v2  # noqa: E402


class FunnelTests(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        self.ctx = app.app_context()
        self.ctx.push()
        db.drop_all()
        db.create_all()
        admin = User(email='admin@test', is_admin=True)
        admin.set_password('pw')
        db.session.add(admin)
        db.session.commit()
        self.client = app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def visits(self):
        return {(v.ref, v.count) for v in db.session.execute(db.select(ReferralVisit)).scalars()}

    def register(self, email='cook@test', source=''):
        return self.client.post('/register', data={'email': email, 'password': 'pw', 'source': source})

    def user(self, email='cook@test'):
        return db.session.execute(db.select(User).filter_by(email=email)).scalar()

    # The ref code

    def test_a_short_address_keeps_its_code_counts_the_visit_and_opens_the_home_page(self):
        response = self.client.get('/tiktok/3')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.location, '/')
        with self.client.session_transaction() as session:
            self.assertEqual(session['ref'], 'tiktok-3')
        self.assertEqual(self.visits(), {('tiktok-3', 1)})

    def test_every_short_address_names_its_channel(self):
        for path, ref in (('/tiktok', 'tiktok'), ('/tt', 'tiktok'), ('/ig', 'instagram'), ('/ig/7', 'instagram-7'),
                          ('/instagram', 'instagram')):
            with self.subTest(path=path):
                client = app.test_client()
                client.get(path, follow_redirects=True)  # /tt and /instagram redirect to /tiktok and /ig
                with client.session_transaction() as session:
                    self.assertEqual(session['ref'], ref)

    def test_the_first_code_of_a_session_wins(self):
        self.client.get('/tiktok')
        self.client.get('/recipes?ref=ig-2')
        with self.client.session_transaction() as session:
            self.assertEqual(session['ref'], 'tiktok')
        self.assertEqual(self.visits(), {('tiktok', 1)})

    def test_ref_on_any_page_is_cleaned_and_kept(self):
        self.client.get('/recipes?ref=IG-3 <b>')
        with self.client.session_transaction() as session:
            self.assertEqual(session['ref'], 'ig-3b')

    def test_visits_from_one_code_add_up_per_day(self):
        for _ in range(3):
            app.test_client().get('/ig')
        self.assertEqual(self.visits(), {('instagram', 3)})

    def test_a_signed_in_user_is_not_counted(self):
        self.client.post('/login', data={'email': 'admin@test', 'password': 'pw'})
        self.client.get('/tiktok')
        self.client.get('/recipes?ref=ig-1')
        self.assertEqual(self.visits(), set())

    # Signing up

    def test_the_sign_up_form_asks_how_they_found_us(self):
        html = self.client.get('/register').get_data(as_text=True)
        self.assertIn('How did you find us?', html)
        for _, label in funnel.SOURCES:
            self.assertIn(label, html)

    def test_a_new_user_keeps_their_answer_ref_and_time(self):
        self.client.get('/tiktok/4')
        self.register(source='tiktok')
        user = self.user()
        self.assertEqual((user.signup_source, user.signup_ref), ('tiktok', 'tiktok-4'))
        self.assertIsNotNone(user.created_at)

    def test_an_unknown_answer_and_no_ref_are_stored_as_empty(self):
        self.register(source='a billboard')
        user = self.user()
        self.assertEqual((user.signup_source, user.signup_ref), (None, None))

    # The numbers

    def test_the_ref_decides_the_channel_before_the_answer(self):
        def user(ref=None, source=None):
            return User(email='x', signup_ref=ref, signup_source=source)
        self.assertEqual(funnel.channel(user('ig-3', 'friend')), 'instagram')
        self.assertEqual(funnel.channel(user('tiktok', None)), 'tiktok')
        self.assertEqual(funnel.channel(user('newsletter', 'friend')), 'friend')
        self.assertEqual(funnel.channel(user(None, None)), 'unknown')

    def test_the_report_counts_users_per_channel_and_week_without_admins(self):
        today = datetime.date(2026, 11, 12)  # a Thursday
        now = datetime.datetime(2026, 11, 12, 9)
        week_ago = now - datetime.timedelta(days=7)
        rows = [('a@t', 'tiktok-1', None, now), ('b@t', 'tiktok-1', None, week_ago), ('c@t', None, 'instagram', now),
                ('d@t', None, None, None)]
        for email, ref, source, created in rows:
            db.session.add(User(email=email, password_hash='x', signup_ref=ref, signup_source=source,
                                created_at=created))
        db.session.add(Recipe(title='Soup', cuisine='', difficulty='', status='approved'))
        db.session.commit()
        recipe_id = db.session.execute(db.select(Recipe.id)).scalar()
        before = self.user('d@t')
        before.created_at = None  # signed up before the tracking (the insert filled in the default)
        db.session.commit()
        users = {u.email: u.id for u in db.session.execute(db.select(User)).scalars()}
        db.session.add(UserRecipeInteraction(user_id=users['a@t'], recipe_id=recipe_id, status='favorite',
                                             made_count=1))
        db.session.add(UserRecipeInteraction(user_id=users['c@t'], recipe_id=recipe_id, status='favorite'))
        db.session.add(ReferralVisit(ref='tiktok-1', day=today, count=40))
        db.session.add(ReferralVisit(ref='tiktok-1', day=today - datetime.timedelta(days=60), count=5))
        db.session.commit()

        r = funnel.report(weeks=4, today=today)
        self.assertEqual(r['totals'], {'signups': 4, 'saved': 2, 'made': 1, 'untracked': 1})
        channels = {c['key']: c for c in r['channels']}
        self.assertEqual((channels['tiktok']['signups'], channels['tiktok']['made']), (2, 1))
        self.assertEqual((channels['instagram']['signups'], channels['instagram']['saved']), (1, 1))
        self.assertEqual(channels['unknown']['signups'], 1)
        self.assertEqual(r['weeks'][0]['start'], datetime.date(2026, 11, 9))
        self.assertEqual(r['weeks'][0]['signups']['tiktok'], 1)
        self.assertEqual(r['weeks'][0]['total'], 2)
        self.assertEqual(r['weeks'][1]['signups']['tiktok'], 1)
        self.assertEqual(r['refs'], [{'ref': 'tiktok-1', 'visits': 45, 'visits_28': 40, 'signups': 2, 'made': 1}])

    def test_the_funnel_page_is_for_admins(self):
        self.assertEqual(self.client.get('/admin/funnel').status_code, 302)
        self.client.post('/login', data={'email': 'admin@test', 'password': 'pw'})
        html = self.client.get('/admin/funnel').get_data(as_text=True)
        self.assertIn('Sign-ups per week', html)
        self.assertIn('No visits with a code yet.', html)

    # The post log

    def log(self, **fields):
        form = {'platform': 'tiktok', 'code': '5', 'format': 'map', 'title': 'Teriyaki salmon',
                'posted_on': '2026-10-30', **fields}
        return self.client.post('/admin/funnel/posts/new', data=form)

    def test_the_next_code_is_above_every_number_in_use(self):
        self.assertEqual(funnel.next_code(), '1')
        self.client.get('/tiktok/2')
        app.test_client().get('/recipes?ref=ig-7')
        app.test_client().get('/ig/launch')
        self.assertEqual(funnel.next_code(), '8')
        self.client.post('/login', data={'email': 'admin@test', 'password': 'pw'})
        self.log(code='11', platform='instagram')
        self.assertEqual(funnel.next_code(), '12')
        html = self.client.get('/admin/funnel/posts/new?platform=instagram&format=grid&recipe=4').get_data(as_text=True)
        self.assertIn('name="code" value="12"', html)
        self.assertIn('<option value="grid" selected>', html)
        self.assertIn('name="recipe_id" value="4"', html)

    def test_a_logged_post_shows_its_numbers_beside_what_its_code_brought(self):
        for _ in range(3):
            app.test_client().get('/tiktok/5')
        app.test_client().get('/ig/5')  # the same code on Instagram is another post
        self.client.post('/login', data={'email': 'admin@test', 'password': 'pw'})
        post_id = int(self.log().location.rsplit('/', 1)[1])
        self.client.post(f'/admin/funnel/posts/{post_id}', data={'part': 'stats', 'day': '2', 'views': '1 500',
                                                                 'saves': '12'})
        self.client.post(f'/admin/funnel/posts/{post_id}', data={'part': 'stats', 'day': '2', 'views': '2,000'})
        [row] = funnel.report()['posts']
        self.assertEqual((row['ref'], row['visits'], row['latest'].views, row['latest'].saves, row['per_1000']),
                         ('tiktok-5', 3, 2000, None, 1.5))
        html = self.client.get('/admin/funnel').get_data(as_text=True)
        self.assertIn('Teriyaki salmon', html)
        self.assertIn('tiktok-5 · map · day 2', html)

    def test_the_post_form_says_what_is_wrong(self):
        recipe = Recipe(title='Pad Thai', cuisine='', difficulty='', status='approved', schema_version=2)
        db.session.add(recipe)
        db.session.commit()
        self.client.post('/login', data={'email': 'admin@test', 'password': 'pw'})
        self.assertEqual(self.log(title='', recipe_id=str(recipe.id)).status_code, 302)
        self.assertEqual(db.session.execute(db.select(SocialPost)).scalar().title, 'Pad Thai')
        for fields, message in (({}, 'TikTok already has a post with code 5.'),
                                ({'code': '6', 'recipe_id': '999'}, 'There is no recipe 999.'),
                                ({'code': 'tiktok-6'}, 'Give the code from the address'),
                                ({'code': '6', 'title': ''}, 'Give the post a title'),
                                ({'code': '6', 'posted_on': ''}, 'Give the day it went up.')):
            with self.subTest(fields=fields):
                response = self.log(**fields)
                self.assertEqual(response.status_code, 400)
                self.assertIn(message, response.get_data(as_text=True))
        self.assertEqual(len(db.session.execute(db.select(SocialPost)).scalars().all()), 1)

    def test_the_render_script_ends_with_the_address_that_logs_the_post(self):
        from scripts.social_render import log_url
        self.assertEqual(log_url('https://thelazychef.app', 'tt', '5', 'map', 297),
                         'https://thelazychef.app/admin/funnel/posts/new?platform=tiktok&code=5&format=map&recipe=297')
        self.assertEqual(log_url('http://127.0.0.1:8000/', 'ig', '6', 'week', None),
                         'http://127.0.0.1:8000/admin/funnel/posts/new?platform=instagram&code=6&format=week')

    # Shared links

    def test_every_page_has_a_default_share_card(self):
        html = self.client.get('/recipes').get_data(as_text=True)
        self.assertIn('<meta property="og:title" content="The Lazy Chef">', html)
        self.assertIn('<meta property="og:image" content="http://localhost/static/brand/share.png">', html)

    def test_a_recipe_link_shows_the_dish_with_whole_addresses(self):
        with open(os.path.join(ROOT, 'data', 'pilot_v2', 'fasit', 'carbonara.json'), encoding='utf-8') as f:
            data = json.load(f)
        recipe = Recipe(title=data['title'], cuisine='', difficulty='', status='approved', schema_version=2,
                        image_filename='carbonara.png')
        db.session.add(recipe)
        save_v2(recipe, data, {})
        db.session.flush()
        refresh(recipe)
        db.session.commit()
        # Behind Cloud Run the app sees http on the public host; APP_BASE_URL is Cloud Run's own address
        with mock.patch.dict(os.environ, {'APP_BASE_URL': 'https://lazy-chef-app.run.app'}):
            html = self.client.get(f'/recipe/{recipe.id}', base_url='http://thelazychef.app').get_data(as_text=True)
        self.assertIn(f'<meta property="og:title" content="{recipe.title}">', html)
        self.assertIn(f'<meta property="og:url" content="https://thelazychef.app/recipe/{recipe.id}">', html)
        self.assertIn('<meta property="og:image" content="https://thelazychef.app/static/recipes/carbonara.png">', html)
        self.assertEqual(html.count('property="og:title"'), 1)


if __name__ == '__main__':
    unittest.main()
