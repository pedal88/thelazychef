"""Prep (Gjør klart): mise elements derived from the graph (services/recipe_v2/mise.py) and the page that shows them."""
import os
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(ROOT)

from tests import test_recipe_v2_view as view_tests  # noqa: E402  (sets the test environment)
from services.recipe_v2 import mise  # noqa: E402
from services.recipe_v2.planner import plan_v2  # noqa: E402
from services.recipe_v2.view import build  # noqa: E402
from database.models import Recipe, db  # noqa: E402


def ready(name, plan='calm'):
    v2 = view_tests.fasit(name)
    return mise.build(v2, plan_v2(v2, plan), 'nb')


def names(items):
    return [f['line']['name'] for f in items]


class MiseModelTests(unittest.TestCase):
    def test_the_pantry_decides_what_is_a_staple(self):
        self.assertTrue(mise.staple({'name': 'hvetemel', 'pantry_tier': 'staple'}))
        self.assertFalse(mise.staple({'name': 'salt', 'pantry_tier': 'core'}))  # the pantry wins over the name
        self.assertTrue(mise.staple({'name': 'salt'}))  # not in the pantry: by name
        self.assertFalse(mise.staple({'name': 'smør'}))

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

    def test_a_bowl_knows_the_steps_that_fill_it(self):
        # A tick on the bowl ticks them off on the cooking screen, and the other way round (static/js/ready.js)
        v2 = view_tests.fasit('burger')
        short = {s['local_id']: s['short'] for s in v2['steps']}
        r = ready('burger')
        bowls = r['bowls'] + [b for g in r['later'] for b in g['bowls']]
        fries = next(b for b in bowls if b['name'] == 'Tørk og olje')
        self.assertEqual([short[x] for x in fries['steps']], ['Skjær potetene', 'Tørk og olje'])  # the whole chain, in order
        every = [x for b in bowls for x in b['steps']]
        self.assertEqual(sorted(every), sorted(r['done_here']))  # each prep step done here is in one bowl
        cheese = ready('carbonara')['bowls'][2]
        self.assertEqual((cheese['name'], cheese['steps']), ('Pecorino romano', []))  # no step behind it: a tick of its own

    def test_names_join_in_the_recipe_language(self):
        self.assertEqual(mise.joined(['onion', 'carrot', 'garlic'], 'en'), 'Onion, carrot and garlic')
        self.assertEqual(mise.joined(['løk', 'gulrot'], 'nb'), 'Løk og gulrot')
        self.assertEqual(mise.joined(['a', 'b', 'c', 'd', 'e'], None), 'A, b and 3 more')

    def test_no_steps_nothing_to_prep(self):
        self.assertIsNone(mise.build({'steps': [], 'ingredients': []}, {'order': [], 'plan': {}}))


class GetReadyPageTests(unittest.TestCase):
    setUp, tearDown, page = (view_tests.RecipeV2ViewTests.setUp, view_tests.RecipeV2ViewTests.tearDown,
                             view_tests.RecipeV2ViewTests.page)

    def test_the_bowls_button_says_how_many_bowls(self):
        _, html = self.page('carbonara', servings=6)
        self.assertIn('<span data-bowl-count>0/3</span>', html)

    def test_the_bowls_sheet_shows_bowls_tiles_and_equipment(self):
        status, html = self.page('carbonara', servings=6)
        self.assertEqual(status, 200)
        sheet = html[html.index('id="sheet-bowls"'):]
        for text in ('Pisk eggeblandingen', 'Take out', 'You probably have', 'Equipment', 'data-tick="b:',
                     '600 g', '0 of 3 bowls ready'):
            self.assertIn(text, sheet)
        self.assertIn('js/ready.js', html)
        self.assertIn('https://example.com/spaghetti.webp', sheet)

    def test_take_out_is_one_list_in_kitchen_groups(self):
        takeout = build(db.session.get(Recipe, self.ids['lasagne']))['ready']['takeout']
        self.assertEqual(takeout[-1]['key'], 'staples')
        staples = [t['line']['name'] for t in takeout[-1]['items']]
        self.assertEqual(staples.count('salt'), 1)  # once, though it is taken out for three steps
        salt = next(t for t in takeout[-1]['items'] if t['line']['name'] == 'salt')
        self.assertGreater(len(salt['steps']), 1)
        self.assertIn('to taste', salt['amount'])

    def test_a_line_without_a_state_is_used_as_it_comes_even_in_a_cutting_step(self):
        from database.models import RecipeLine
        recipe = db.session.get(Recipe, self.ids['carbonara'])
        line = next(ln for ln in recipe.lines if 'guanciale' in ln.name)
        line.state, line.cut, line.prep_style = None, None, None  # "Skjær guancialen" is method slice, but the line says nothing
        recipe.language = 'nb'
        db.session.commit()
        bowls = build(db.session.get(Recipe, self.ids['carbonara']))['ready']['bowls']
        tile = next(t for b in bowls for t in b['lines'] if 'guanciale' in t['name'])
        self.assertEqual((tile['cut'], tile['state'], tile['mark']), (None, '', None))
        self.assertIsInstance(line, RecipeLine)

    def test_the_old_addresses_open_the_page_at_prep(self):
        rid = self.ids['carbonara']
        for path in ('/prep', '/get-ready'):
            res = self.client.get(f'/recipe/{rid}{path}', query_string={'servings': 6})
            self.assertEqual(res.status_code, 302)
            self.assertTrue(res.headers['Location'].endswith(f'/recipe/{rid}?servings=6#prep'), res.headers['Location'])

    def test_drafts_only_for_admins(self):
        self.assertEqual(self.page('lasagne')[0], 302)
        self.client.post('/login', data={'email': 'admin@test', 'password': 'pw'})
        status, html = self.page('lasagne')
        self.assertEqual(status, 200)
        self.assertIn('Later, while:', html)

if __name__ == '__main__':
    unittest.main()
