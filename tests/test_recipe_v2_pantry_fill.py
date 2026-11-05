"""Filling the pantry for a made recipe's unlinked lines (services/recipe_v2/pantry_fill.py) and its queue job.

Claude is replaced by a stand-in that answers with fixed decisions, so nothing outside the test is called.
"""
import json
import os
import sys
import unittest
from types import SimpleNamespace
from unittest import mock

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(ROOT)

os.environ['DB_BACKEND'] = 'local'
os.environ['DATABASE_URL'] = 'sqlite://'
os.environ['STORAGE_BACKEND'] = 'local'
os.environ.setdefault('SECRET_KEY', 'test-secret')
os.environ.setdefault('GOOGLE_API_KEY', 'test-key')
for key in ('TASKS_QUEUE', 'TASKS_SERVICE_ACCOUNT', 'APP_BASE_URL'):
    os.environ.pop(key, None)

from app import app  # noqa: E402
from flask import g  # noqa: E402
from sqlalchemy import event  # noqa: E402

from database.models import Ingredient, IngredientAlias, Recipe, User, db  # noqa: E402
from scripts.fill_pantry import parse_ids  # noqa: E402
from services.recipe_v2 import pantry_fill, tasks  # noqa: E402
from services.recipe_v2.store import save_v2  # noqa: E402

with open(os.path.join(ROOT, 'data', 'pilot_v2', 'fasit', 'carbonara.json'), encoding='utf-8') as f:
    CARBONARA = json.load(f)  # nine lines, none in the empty test pantry

PECORINO = {'name': 'pecorino romano', 'main_category': 'dairy and egg', 'sub_category': 'cheese', 'default_unit': 'g',
            'average_g_per_unit': 0, 'calories': 387, 'protein': 32, 'carbs': 3.6, 'fat': 27, 'fat_saturated': 17,
            'sugar': 0.8, 'fiber': 0, 'sodium_mg': 1200, 'looks': 'pale wedge of hard sheep cheese'}


def answer(decisions, seen=None):
    """A stand-in for claude.call that answers with these decisions and keeps what it was asked."""
    def call(model, effort, messages, system=None, schema=None):
        if seen is not None:
            seen.append({'system': system, 'user': messages[0]['content']})
        msg = SimpleNamespace(content=[SimpleNamespace(type='text', text=json.dumps({'lines': decisions}))],
                              stop_reason='end_turn', model=model)
        return msg, {'cost_usd': 0.02, 'seconds': 1.0}
    return call


def decision(line, action, food_id='', new=None, reason='because', name='', factor=1, replacements=None, unit=''):
    return {'line': line, 'action': action, 'food_id': food_id, 'new': new, 'reason': reason, 'name': name,
            'amount_factor': factor, 'unit': unit, 'replacements': replacements or []}


class PantryFillTests(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        self.ctx = app.app_context()
        self.ctx.push()
        db.drop_all()
        db.create_all()
        self.pasta = Ingredient(food_id='000322', name='spaghetti', status='active', calories_per_100g=371,
                                protein_per_100g=13, carbs_per_100g=75, fat_per_100g=1.5, main_category='cereal grains and pasta')
        self.egg = Ingredient(food_id='000225', name='eggs', status='active', calories_per_100g=143, main_category='dairy and egg')
        db.session.add_all([self.pasta, self.egg])
        self.recipe = Recipe(title='Carbonara', cuisine='Italian', difficulty='Simplistic', status='draft')
        db.session.add(self.recipe)
        save_v2(self.recipe, CARBONARA)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def lines(self, name):
        return [line for line in self.recipe.lines if line.name == name]

    def test_aliases_questions_and_skips_are_carried_out_and_noted(self):
        seen = []
        decisions = [decision('spaghetti', 'alias', '000322', reason='the same pasta'),
                     decision('eggeplomme', 'alias', 'nope'),  # no such item: left as it is
                     decision('pecorino romano', 'ask', new=PECORINO, reason='it is the dish'),
                     decision('vann', 'skip', reason='water'),
                     decision('something not asked', 'alias', '000322')]
        result = pantry_fill.fill(self.recipe, call=answer(decisions, seen))
        db.session.commit()

        # Claude saw the pantry, the recipe and each unlinked name once (pecorino is on two lines)
        self.assertIn('000322 spaghetti', seen[0]['system'])
        asked = seen[0]['user'].split('LINES NOT IN THE PANTRY')
        self.assertIn('Method', asked[0])
        self.assertEqual(asked[1].count('pecorino romano'), 1)
        # Alias: the line is linked; the name equals the item's own name, so no alias row is needed
        self.assertEqual(self.lines('spaghetti')[0].ingredient, self.pasta)
        # Ask: nothing joins the pantry. A pending item marked as Claude's, with its nutrition, on both pecorino lines
        cheese = db.session.execute(db.select(Ingredient).where(Ingredient.name == 'pecorino romano')).scalar_one()
        self.assertEqual((cheese.status, cheese.data_source, cheese.calories_per_100g), ('pending', 'claude_auto', 387))
        self.assertTrue(cheese.food_id.startswith('auto-'))
        self.assertEqual(cheese.image_notes, 'pale wedge of hard sheep cheese')  # for the symbol prompt
        self.assertEqual({line.ingredient_id for line in self.lines('pecorino romano')}, {cheese.id})
        self.assertEqual(cheese.aliases, [])
        # Skipped and unknown stay unlinked
        self.assertIsNone(self.lines('vann')[0].ingredient_id)
        self.assertIsNone(self.lines('eggeplomme')[0].ingredient_id)
        # One note per decision about a line asked about, kept on the recipe
        self.assertEqual(len(result['notes']), 4)
        self.assertEqual([e['message'] for e in self.recipe.validation_errors], result['notes'])
        self.assertEqual([e['rule'] for e in self.recipe.validation_errors], ['pantry', 'pantry', 'ask', 'pantry'])
        self.assertEqual(result['cost_usd'], 0.04)  # the decisions, and the advice on its question
        self.assertTrue(self.recipe.is_flagged_for_review)

    def test_an_alias_name_links_the_next_recipe_without_claude(self):
        pantry_fill.fill(self.recipe, call=answer([decision('sort pepper', 'alias', '000225')]))
        db.session.commit()
        self.assertEqual(db.session.execute(db.select(IngredientAlias.name)).scalars().all(), ['sort pepper'])
        other = Recipe(title='Again', cuisine='Italian', difficulty='Simplistic', status='draft')
        db.session.add(other)
        save_v2(other, CARBONARA)
        from services.recipe_v2.generate import recalculate
        recalculate(other)  # the matcher finds the alias
        self.assertEqual([line.ingredient_id for line in other.lines if line.name == 'sort pepper'], [self.egg.id])

    def test_a_question_about_an_item_the_pantry_has_is_no_question(self):
        pantry_fill.fill(self.recipe, call=answer([decision('egg', 'ask', new=dict(PECORINO, name='Eggs'))]))
        self.assertEqual(self.lines('egg')[0].ingredient, self.egg)
        self.assertEqual(db.session.execute(db.select(db.func.count(Ingredient.id))).scalar(), 2)
        self.assertNotIn('ask', [e['rule'] for e in self.recipe.validation_errors])

    def test_a_substitute_changes_this_recipe_only(self):
        step = self.lines('pecorino romano')[0].step
        step.short, step.done_when = 'Mix in the pecorino romano', 'The pecorino is melted'
        self.recipe.chef_note = 'Pecorino is salty.'
        revision, amount, grams = self.recipe.revision, self.lines('pecorino romano')[0].amount, self.lines('pecorino romano')[0].gram_weight
        text = step.text
        pantry_fill.fill(self.recipe, call=answer([decision(
            'pecorino romano', 'substitute', '000322', name='parmesan', factor=0.5, reason='close enough',
            replacements=[{'find': 'pecorino', 'replace': 'parmesan'}])]))
        db.session.commit()

        lines = self.lines('parmesan')
        self.assertEqual(len(lines), 2)  # both lines, and none under the old name
        self.assertEqual(self.lines('pecorino romano'), [])
        self.assertEqual({line.ingredient_id for line in lines}, {self.pasta.id})
        self.assertEqual(lines[0].amount, round(amount * 0.5, 2))
        self.assertEqual(lines[0].gram_weight, round(grams * 0.5, 1))
        self.assertEqual(step.short, 'Mix in the parmesan')
        self.assertEqual(step.done_when, 'The parmesan is melted')
        self.assertEqual(self.recipe.chef_note, 'Parmesan is salty.')  # a capital stays a capital
        self.assertIn('{i', text)
        self.assertEqual(self.recipe.revision, revision + 1)
        # It holds here only: no alias, so another recipe gets its own decision
        self.assertEqual(db.session.execute(db.select(IngredientAlias.name)).scalars().all(), [])
        note = next(e for e in self.recipe.validation_errors if e['rule'] == 'substitute')
        self.assertIn('"pecorino romano" is now parmesan (amount x 0.5)', note['message'])

    def test_a_swap_does_not_touch_a_word_that_only_contains_the_name(self):
        step = self.lines('vann')[0].step
        step.short = 'Vannbad med vann'
        pantry_fill.fill(self.recipe, call=answer([decision('vann', 'substitute', '000322', name='melk')]))
        self.assertEqual(step.short, 'Vannbad med melk')

    def test_a_substitute_needs_an_item_in_the_pantry_and_a_sane_amount(self):
        pending = Ingredient(food_id='p1', name='something pending', status='pending')
        db.session.add(pending)
        amount = self.lines('spaghetti')[0].amount
        pantry_fill.fill(self.recipe, call=answer([decision('vann', 'substitute', 'p1'), decision('egg', 'substitute', 'nope'),
                                                   decision('spaghetti', 'substitute', '000322', factor=50)]))
        self.assertIsNone(self.lines('vann')[0].ingredient_id)
        self.assertIsNone(self.lines('egg')[0].ingredient_id)
        self.assertEqual(self.pasta.food_id, self.lines('spaghetti')[0].ingredient.food_id)
        self.assertEqual(self.lines('spaghetti')[0].amount, amount)

    def test_a_swap_can_change_the_unit_and_a_made_up_unit_is_ignored(self):
        line = self.lines('spaghetti')[0]
        before = line.unit
        pantry_fill.fill(self.recipe, call=answer([decision('spaghetti', 'substitute', '000322', unit='cube')]))
        self.assertEqual(line.unit, before)
        for other in self.lines('pecorino romano'):
            other.unit, other.amount = 'tbsp', 1
        pantry_fill.fill(self.recipe, call=answer([decision('pecorino romano', 'substitute', '000322', name='parmesan', unit='piece')]))
        self.assertEqual({x.unit for x in self.lines('parmesan')}, {'piece'})

    def test_a_swap_in_a_question_keeps_its_unit(self):
        for line in self.lines('pecorino romano'):
            line.unit, line.amount = 'tbsp', 1
        pantry_fill.fill(self.recipe, call=answer([decision('pecorino romano', 'ask', '000322', new=PECORINO, name='parmesan', unit='piece')]))
        item = self.lines('pecorino romano')[0].ingredient
        pantry_fill.swap(item)
        self.assertEqual({x.unit for x in self.lines('parmesan')}, {'piece'})

    def test_claude_sees_the_kind_a_line_asks_for(self):
        self.lines('pecorino romano')[0].variety = '4 % fat'
        seen = []
        pantry_fill.fill(self.recipe, call=answer([], seen))
        self.assertIn('[kind: 4 % fat]', seen[0]['user'].split('LINES NOT IN THE PANTRY')[1])

    def test_the_prompts_say_what_stays_on_a_line(self):
        with open('data/prompts/recipe_v2/structure.jinja2', encoding='utf-8') as f:
            self.assertIn('"boneless", "skinless", "4 % fat"', f.read())
        with open('data/prompts/recipe_v2/pantry_fill.jinja2', encoding='utf-8') as f:
            prompt = f.read()
        self.assertIn('all five are true', prompt)
        self.assertIn('1 tbsp stock concentrate is 1 piece', prompt)

    def test_a_published_recipe_is_never_changed_or_held_back(self):
        self.recipe.status = 'approved'
        before = sorted(line.name for line in self.recipe.lines)
        pantry_fill.fill(self.recipe, call=answer([decision('vann', 'substitute', '000322', name='melk'),
                                                   decision('pecorino romano', 'ask', new=PECORINO),
                                                   decision('spaghetti', 'alias', '000322')]))
        self.assertEqual(sorted(line.name for line in self.recipe.lines), before)
        self.assertIsNone(pantry_fill.open_question(self.recipe))
        self.assertEqual(self.lines('spaghetti')[0].ingredient, self.pasta)

    def _ask_pecorino(self, swap_to='000322'):
        pantry_fill.fill(self.recipe, call=answer([decision(
            'pecorino romano', 'ask', swap_to, new=PECORINO, reason='it is the dish', name='parmesan', factor=2,
            replacements=[{'find': 'pecorino', 'replace': 'parmesan'}])]))
        db.session.commit()
        return db.session.execute(db.select(Ingredient).where(Ingredient.name == 'pecorino romano')).scalar_one()

    def test_the_questions_show_what_waits(self):
        item = self._ask_pecorino()
        q = pantry_fill.questions()
        self.assertEqual([x['item'] for x in q], [item])
        self.assertTrue(q[0]['can_swap'])
        row = q[0]['rows'][0]
        self.assertEqual((row['recipe'], row['reason'], row['swap_item']), (self.recipe, 'it is the dish', self.pasta))
        self.assertEqual(pantry_fill.open_question(self.recipe), item)

    def test_the_admin_menu_is_marked_while_a_question_waits(self):
        admin = User(email='menu-admin@test', is_admin=True)
        admin.set_password('test-password')
        cook = User(email='menu-cook@test')
        cook.set_password('test-password')
        db.session.add_all([admin, cook])
        db.session.commit()
        client = app.test_client()
        client.post('/login', data={'email': admin.email, 'password': 'test-password'})

        def unmarked(who):
            g.pop('_login_user', None)  # this test's app context, with who is signed in, is shared by the clients
            page = who.get('/explore/galaxy').get_data(as_text=True)
            self.assertEqual(page.count('class="menu-dot') + page.count('class="menu-count'), 0)

        self.assertEqual(pantry_fill.open_questions(), 0)
        unmarked(client)

        item = self._ask_pecorino()
        self.assertEqual(pantry_fill.open_questions(), 1)
        page = client.get('/explore/galaxy').get_data(as_text=True)
        self.assertEqual(page.count('<span class="menu-count" aria-label="1 waiting">1</span>'), 2)  # top bar and phone menu
        self.assertEqual(page.count('class="menu-dot'), 3)  # on Admin in both, and on the phone's menu button
        self.assertIn('menu-dot-corner', page)

        queries = []
        record = lambda conn, cursor, statement, *rest: queries.append(statement)
        event.listen(db.engine, 'before_cursor_execute', record)
        try:
            client.get('/explore/galaxy')
        finally:
            event.remove(db.engine, 'before_cursor_execute', record)
        self.assertEqual(len([q for q in queries if 'count(ingredient.id)' in q]), 1)  # the menu is drawn several times, asked once

        g.pop('_login_user', None)
        other = app.test_client()
        other.post('/login', data={'email': cook.email, 'password': 'test-password'})
        unmarked(other)  # nothing for others
        unmarked(app.test_client())

        pantry_fill.add_item(item)
        db.session.commit()
        unmarked(client)  # answered: gone

    def odds(self, add, *swaps):
        """A stand-in for claude.call that answers with Claude's shares."""
        def call(model, effort, messages, system=None, schema=None):
            self.asked = {'system': system, 'user': messages[0]['content'], 'schema': schema}
            text = json.dumps({'add': add, 'add_why': 'it is the dish',
                               'swaps': [{'food_id': f, 'share': s, 'why': 'close'} for f, s in swaps]})
            return SimpleNamespace(content=[SimpleNamespace(type='text', text=text)]), {'cost_usd': 0.02, 'seconds': 1.0}
        return call

    def test_claude_shares_100_across_adding_and_swaps(self):
        item = self._ask_pecorino()
        self.assertEqual(pantry_fill.weigh(self.recipe, item, call=self.odds(60, ('000322', 40))), 0.02)
        db.session.commit()
        self.assertIn('000322 spaghetti', self.asked['system'])
        self.assertIn('pecorino romano', self.asked['user'])
        self.assertIn('it is the dish', self.asked['user'])
        odds = pantry_fill.questions()[0]['rows'][0]['odds']
        self.assertEqual(odds, {'add': 60, 'add_why': 'it is the dish',
                                'swaps': [{'food_id': '000322', 'name': self.pasta.name, 'share': 40, 'why': 'close'}]})

    def test_the_shares_always_add_up_to_100_with_at_most_five_real_swaps(self):
        item = self._ask_pecorino()
        extra = [Ingredient(food_id=f'x{i}', name=f'item {i}', status='active') for i in range(6)]
        db.session.add_all([*extra, Ingredient(food_id='off', name='gone', status='inactive')])
        db.session.flush()
        answer_ = {'add': 10, 'add_why': '', 'swaps': [{'food_id': f'x{i}', 'share': 30 - i, 'why': ''} for i in range(6)]
                   + [{'food_id': 'off', 'share': 90, 'why': ''}, {'food_id': 'no such', 'share': 90, 'why': ''},
                      {'food_id': item.food_id, 'share': 90, 'why': 'itself'}, {'food_id': 'x0', 'share': 90, 'why': 'twice'}]}
        odds = pantry_fill._clean_odds(answer_, item)
        self.assertEqual([s['food_id'] for s in odds['swaps']], ['x0', 'x1', 'x2', 'x3', 'x4'])
        self.assertEqual(odds['add'] + sum(s['share'] for s in odds['swaps']), 100)
        self.assertEqual(pantry_fill._clean_odds({'add': 100, 'add_why': '', 'swaps': []}, item)['add'], 100)
        self.assertIsNone(pantry_fill._clean_odds({'add': 0, 'swaps': []}, item))
        self.assertEqual(pantry_fill._to_100([1, 1, 1]), [34, 33, 33])

    def test_the_job_weighs_its_questions_and_a_failure_leaves_the_question(self):
        calls = []

        def call(model, effort, messages, system=None, schema=None):
            calls.append(schema)
            if len(calls) == 1:
                return answer([decision('pecorino romano', 'ask', new=PECORINO, reason='it is the dish')])(model, effort, messages, system, schema)
            return self.odds(70, ('000322', 30))(model, effort, messages, system, schema)

        result = pantry_fill.fill(self.recipe, call=call)
        self.assertEqual(len(calls), 2)
        self.assertEqual(result['cost_usd'], 0.04)
        db.session.commit()
        self.assertEqual(pantry_fill.questions()[0]['rows'][0]['odds']['add'], 70)

        def broken(*args, **kwargs):
            raise RuntimeError('overloaded')
        self.recipe.validation_errors = [{k: v for k, v in e.items() if k != 'odds'} for e in self.recipe.validation_errors]
        self.assertEqual(pantry_fill._weigh_open(self.recipe, call=broken), 0.0)
        self.assertIsNone(pantry_fill.questions()[0]['rows'][0]['odds'])

    def test_the_page_shows_the_shares_and_asks_for_those_without(self):
        item = self._ask_pecorino()
        admin = User(email='odds-admin@test', is_admin=True)
        admin.set_password('test-password')
        db.session.add(admin)
        db.session.commit()
        client = app.test_client()
        client.post('/login', data={'email': admin.email, 'password': 'test-password'})
        self.assertIn('Ask Claude for advice', client.get('/admin/pantry-questions').get_data(as_text=True))
        with mock.patch.object(pantry_fill.claude, 'call', self.odds(60, ('000322', 40))):
            self.assertEqual(client.post(f'/admin/pantry-questions/{item.id}/weigh').status_code, 302)
        page = client.get('/admin/pantry-questions').get_data(as_text=True)
        self.assertNotIn('Ask Claude for advice', page)
        self.assertIn('>60%<', page)
        self.assertIn('>40%<', page)
        self.assertIn(f'data-pick="{self.pasta.name}"', page)
        self.assertIn('data-wait="Adding', page)
        with mock.patch.object(pantry_fill.claude, 'call', side_effect=RuntimeError('secret detail')):
            self.recipe.validation_errors = [{k: v for k, v in e.items() if k != 'odds'} for e in self.recipe.validation_errors]
            db.session.commit()
            refused = client.post(f'/admin/pantry-questions/{item.id}/weigh', follow_redirects=True).get_data(as_text=True)
        self.assertNotIn('secret detail', refused)

    def test_a_second_recipe_with_the_same_item_is_the_same_question(self):
        item = self._ask_pecorino()
        other = Recipe(title='Again', cuisine='Italian', difficulty='Simplistic', status='draft')
        db.session.add(other)
        save_v2(other, CARBONARA)
        pantry_fill.fill(other, call=answer([decision('pecorino romano', 'ask', new=PECORINO)]))
        db.session.commit()
        q = pantry_fill.questions()
        self.assertEqual([x['item'] for x in q], [item])
        self.assertEqual(len(q[0]['rows']), 2)
        self.assertFalse(q[0]['can_swap'])  # the second has no swap of its own

    def test_adding_the_item_answers_and_lets_it_in(self):
        item = self._ask_pecorino()
        self.assertEqual(pantry_fill.without_symbol(), [])  # no symbol is paid for before the answer
        pantry_fill.add_item(item)
        db.session.commit()
        self.assertEqual((item.status, item.tier), ('active', 'long_tail'))
        self.assertEqual(pantry_fill.questions(), [])
        self.assertIsNone(pantry_fill.open_question(self.recipe))
        rules = [e['rule'] for e in self.recipe.validation_errors]
        self.assertNotIn('ask', rules)
        self.assertIn('asked', rules)
        self.assertEqual(pantry_fill.without_symbol(), [item])

    def test_claudes_swap_answers_and_the_item_leaves(self):
        item = self._ask_pecorino()
        amount = self.lines('pecorino romano')[0].amount
        self.assertEqual(pantry_fill.swap(item), [self.recipe])
        db.session.commit()
        self.assertEqual(item.status, 'inactive')
        self.assertEqual(self.lines('parmesan')[0].ingredient, self.pasta)
        self.assertEqual(self.lines('parmesan')[0].amount, round(amount * 2, 2))
        self.assertIsNone(pantry_fill.open_question(self.recipe))

    def test_pals_own_item_answers_too_and_keeps_the_amount(self):
        item = self._ask_pecorino(swap_to='')
        amount = self.lines('pecorino romano')[0].amount
        self.assertEqual(pantry_fill.swap(item), [])  # no swap to take: the question stays
        self.assertEqual(item.status, 'pending')
        pantry_fill.swap(item, self.egg)
        self.assertEqual(self.lines('eggs')[0].amount, amount)
        self.assertEqual(item.status, 'inactive')

    def test_claude_sees_the_answers_the_next_time(self):
        item = self._ask_pecorino()
        pantry_fill.swap(item)
        db.session.commit()
        seen = []
        pantry_fill.fill(self.recipe, call=answer([], seen))
        self.assertIn('WHAT THE OWNER ANSWERED BEFORE', seen[0]['system'])
        self.assertIn(f'"pecorino romano" in {self.recipe.title}: not added, swapped to spaghetti', seen[0]['system'])

    def test_an_item_said_no_to_can_be_asked_about_again(self):
        item = self._ask_pecorino()
        pantry_fill.swap(item)
        other = Recipe(title='Again', cuisine='Italian', difficulty='Simplistic', status='draft')
        db.session.add(other)
        save_v2(other, CARBONARA)
        pantry_fill.fill(other, call=answer([decision('pecorino romano', 'ask', new=PECORINO)]))
        self.assertEqual(item.status, 'pending')
        self.assertEqual(db.session.execute(db.select(db.func.count(Ingredient.id)).where(Ingredient.name == 'pecorino romano')).scalar(), 1)

    def test_the_prompt_is_not_about_shops_in_norway(self):
        seen = []
        pantry_fill.fill(self.recipe, call=answer([], seen))
        self.assertNotIn('Norwegian shopper', seen[0]['system'])
        self.assertNotIn('WHAT THE OWNER ANSWERED BEFORE', seen[0]['system'])

    def test_a_recipe_with_a_question_cannot_be_approved(self):
        item = self._ask_pecorino()
        admin = User(email='admin@example.com', is_admin=True)
        admin.set_password('test-password')
        db.session.add(admin)
        db.session.commit()
        client = app.test_client()
        client.post('/login', data={'email': admin.email, 'password': 'test-password'})
        url = f'/admin/recipes/{self.recipe.id}/status'
        answer_ = client.post(url, json={'status': 'approved'})
        self.assertEqual(answer_.status_code, 409)
        self.assertIn('pecorino romano', answer_.get_json()['error'])
        self.assertEqual(db.session.get(Recipe, self.recipe.id).status, 'draft')

        page = client.get('/admin/pantry-questions')
        self.assertEqual(page.status_code, 200)
        self.assertIn(b'pecorino romano', page.data)
        with mock.patch.object(pantry_fill, 'make_symbols', return_value=['pecorino romano']) as symbols:
            self.assertEqual(client.post(f'/admin/pantry-questions/{item.id}/add').status_code, 302)
        symbols.assert_called_once()
        self.assertEqual(client.post(f'/admin/pantry-questions/{item.id}/add').status_code, 409)  # answered
        self.assertEqual(client.post(url, json={'status': 'approved'}).status_code, 200)
        self.assertIn(b'added pecorino romano', client.get('/admin/pantry-questions').data)

    def test_the_swap_route_refuses_what_the_pantry_lacks(self):
        item = self._ask_pecorino()
        admin = User(email='admin@example.com', is_admin=True)
        admin.set_password('test-password')
        db.session.add(admin)
        db.session.commit()
        client = app.test_client()
        client.post('/login', data={'email': admin.email, 'password': 'test-password'})
        client.post(f'/admin/pantry-questions/{item.id}/swap', data={'other': 'nothing like it'})
        self.assertEqual(db.session.get(Ingredient, item.id).status, 'pending')
        client.post(f'/admin/pantry-questions/{item.id}/swap', data={'other': 'Eggs'})
        self.assertEqual(db.session.get(Ingredient, item.id).status, 'inactive')

    def test_pantry_notes_do_not_flag_a_recipe_that_is_otherwise_fine(self):
        names = {line.name for line in self.recipe.lines}
        pantry_fill.fill(self.recipe, call=answer([decision(n, 'alias', '000322') for n in names]))
        self.assertTrue(all(line.ingredient_id for line in self.recipe.lines))
        self.assertTrue(self.recipe.validation_errors)
        self.assertFalse(self.recipe.is_flagged_for_review)

    def test_nothing_to_do_calls_nobody(self):
        for line in self.recipe.lines:
            line.ingredient = self.pasta
        result = pantry_fill.fill(self.recipe, call=mock.Mock(side_effect=AssertionError('called')))
        self.assertEqual(result, {'notes': [], 'cost_usd': 0.0})
        self.assertFalse(pantry_fill.needs_filling(self.recipe.id))

    def test_the_queue_job_fills_then_queues_the_images_and_notes_its_last_failure(self):
        queue = {'TASKS_QUEUE': 'q', 'TASKS_SERVICE_ACCOUNT': 'sa@x', 'APP_BASE_URL': 'https://app.example'}
        with mock.patch.dict(os.environ, queue), mock.patch.object(tasks, 'enqueue_images') as images, \
                mock.patch.object(pantry_fill, 'fill') as fill:
            self.assertTrue(tasks.run_pantry(self.recipe.id))
            fill.assert_called_once()
            images.assert_called_once_with(self.recipe.id)
            with mock.patch.object(pantry_fill, 'make_symbols') as symbols:
                tasks.run_pantry(self.recipe.id, images=False)
            symbols.assert_called_once()  # the new items' symbols, after the fill
            self.assertEqual(images.call_count, 1)
            fill.side_effect = RuntimeError('overloaded')
            with self.assertRaises(RuntimeError):
                tasks.run_pantry(self.recipe.id, attempt=0)  # Cloud Tasks tries again
            self.assertTrue(tasks.run_pantry(self.recipe.id, attempt=tasks.MAX_ATTEMPTS - 1))
            self.assertEqual(images.call_count, 2)  # the images come anyway
        recipe = db.session.get(Recipe, self.recipe.id)
        self.assertEqual([e['rule'] for e in recipe.validation_errors], ['pantry'])
        self.assertNotIn('overloaded', recipe.validation_errors[0]['message'])

    def test_a_made_recipe_with_unlinked_lines_queues_the_pantry_job_first(self):
        with mock.patch.object(tasks, 'configured', return_value=True), \
                mock.patch.object(tasks, 'enqueue_pantry') as pantry, mock.patch.object(tasks, 'enqueue_images') as images, \
                mock.patch('services.recipe_v2.generate.create_recipe'):
            self.recipe.status = 'generating'
            db.session.commit()
            tasks.run(self.recipe.id, 'idea', 'Carbonara', images=False)
        pantry.assert_called_once_with(self.recipe.id, False)
        images.assert_not_called()

    def test_the_task_endpoint_needs_the_queue_token(self):
        client = app.test_client()
        url = f'/internal/tasks/recipe-v2-pantry/{self.recipe.id}'
        self.assertEqual(client.post(url, json={}).status_code, 401)
        with mock.patch.object(tasks, 'verified', return_value=True), mock.patch.object(tasks, 'run_pantry') as run:
            self.assertEqual(client.post(url, json={'images': False}, headers={'Authorization': 'Bearer ok'}).status_code, 200)
        self.assertEqual(run.call_args.kwargs['images'], False)

    def test_new_items_get_their_symbol_image_and_a_failure_leaves_one_without(self):
        pantry_fill.fill(self.recipe, call=answer([decision('pecorino romano', 'ask', new=PECORINO),
                                                   decision('vann', 'ask', new=dict(PECORINO, name='water'))]))
        for item in db.session.execute(db.select(Ingredient).where(Ingredient.status == 'pending')).scalars():
            pantry_fill.add_item(item)
        db.session.commit()
        items = pantry_fill.without_symbol(self.recipe)
        self.assertEqual([i.name for i in items], ['pecorino romano', 'water'])
        self.assertEqual(pantry_fill.without_symbol(), items)  # the items of every recipe
        self.pasta.data_source = 'usda'
        saved = []
        storage = SimpleNamespace(save=lambda data, name, folder: saved.append((name, folder)) or f'https://b/{folder}/{name}')

        def draw(ing):
            if ing.name == 'water':
                raise RuntimeError('quota')
            from io import BytesIO
            from PIL import Image
            out = BytesIO()
            Image.new('RGB', (8, 8)).save(out, 'PNG')
            return out.getvalue(), 'a prompt', {}
        made = pantry_fill.make_symbols(items, storage, draw=draw)
        self.assertEqual(made, ['pecorino romano'])
        self.assertEqual(saved[0][1], 'pantry/symbols')
        self.assertTrue(items[0].image_url.startswith('https://b/pantry/symbols/auto-'))
        self.assertIsNone(items[1].image_url)
        self.assertEqual([i.name for i in pantry_fill.without_symbol()], ['water'])

    def test_ids_for_the_script(self):
        self.assertEqual(parse_ids('337-340, 345'), [337, 338, 339, 340, 345])


if __name__ == '__main__':
    unittest.main()
