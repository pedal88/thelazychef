"""The recipe page: what each step needs on the cooking screen (services/recipe_v2/view.cook_needs), and the page."""
import os
import re
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(ROOT)

from tests import test_recipe_v2_view as view_tests  # noqa: E402  (sets the test environment)
from database.models import Recipe, db  # noqa: E402
from services.recipe_v2.view import build  # noqa: E402


class CookTests(unittest.TestCase):
    setUp, tearDown, page = (view_tests.RecipeV2ViewTests.setUp, view_tests.RecipeV2ViewTests.tearDown,
                             view_tests.RecipeV2ViewTests.page)

    def steps(self, name):
        return {s['short']: s for s in build(db.session.get(Recipe, self.ids[name]))['steps']}

    def test_each_step_gets_its_bowls_and_waits(self):
        s = self.steps('carbonara')
        self.assertEqual([b['name'] for b in s['Rør inn eggeblandingen']['bowls']], ['Pisk eggeblandingen'])
        self.assertEqual([b['no'] for b in s['Stek guancialen']['bowls']], [1])  # the cut guanciale comes as bowl 1
        self.assertEqual(s['Kok pastaen']['bowls'], [])
        self.assertEqual(s['Kok pastaen']['passive_min'], 9)
        self.assertTrue(s['Kok pastaen']['after'])  # it waits for the boiling water

    def test_the_old_addresses_open_the_page(self):
        rid = self.ids['carbonara']
        for path, end in (('/cook', '#cook'), ('/make', '')):
            location = self.client.get(f'/recipe/{rid}{path}', query_string={'servings': 6}).headers['Location']
            self.assertTrue(location.endswith(f'/recipe/{rid}?servings=6{end}'), location)

    def test_the_bowls_and_the_steps_share_their_ticks(self):
        rid = self.ids['carbonara']
        html = self.client.get(f'/recipe/{rid}').get_data(as_text=True)
        bowls = re.findall(r'data-bowl data-key="(b:[^"]+)" data-steps="([^"]*)" data-lines="([^"]*)"', html)
        self.assertEqual(len(bowls), 3)
        self.assertTrue(bowls[0][1] and bowls[0][2])  # the guanciale: its prep step and its line
        self.assertEqual(bowls[2][1], '')  # the pecorino has no step behind it
        for key, steps, _ in bowls:
            self.assertIn(f'data-bowls="{key}', html.replace(f' {key}', key))  # the step it goes into knows it
            for sid in steps.split():
                self.assertIn(f'data-st="{sid}"', html)
        self.assertIn('class="pill" data-l="', html)  # the card swaps a ready bowl's lines for the bowl
        self.assertIn('data-bowls-go', html)
        # Each bowl's step is a button, with the key to the colours
        self.assertEqual(html.count('data-goto-step="'), 3)
        self.assertIn('class="bowl-key"', html)

    def test_the_bowls_for_later_know_the_wait_they_are_for(self):
        rid = self.ids['tikka']
        html = self.client.get(f'/recipe/{rid}').get_data(as_text=True)
        wait = re.search(r'<details class="later" id="later-([^"]+)" data-while="([^"]+)"', html)
        self.assertTrue(wait and wait.group(1) == wait.group(2))
        self.assertIn(f'data-st="{wait.group(2)}"', html)  # the step it waits for is a step of the list

    def test_the_recipe_page_is_one_page_with_the_dish_and_the_steps_as_a_list(self):
        rid = self.ids["carbonara"]
        self.client.set_cookie('flow', 'tabs')  # the cookie of the old trial changes nothing
        html = self.client.get(f'/recipe/{rid}?servings=2').get_data(as_text=True)  # a visitor
        for text in ('class="ovl ovl-poster"', 'data-fit-ings', 'id="ings-h"', 'Get ready', 'class="heat-line"', 'Heat on', 'class="st ', 'data-start',
                     'data-view="timeline"', 'data-view="delta"', 'id="sheet-bowls"', 'data-bowl', 'js/ready.js', 'js/steps.js',
                     'js/kitchen.js', 'data-cook-open', 'id="cook"', 'data-cook-close', 'data-view-menu',
                     'class="slist focus"', 'class="st-line"', 'class="st-more"', 'data-details', 'id="sheet-step"'):
            self.assertIn(text, html)
        self.assertNotIn('class="flowbar"', html)
        self.assertNotIn('class="trialbar"', html)  # the admin chip is for admins
        # The steps in the order of the plan, numbered, and the line before the first step that heats the food
        rows = re.findall(r'class="(st [a-z ]+|heat-line)"', html)
        line = rows.index('heat-line')
        self.assertTrue(line > 0 and all(r.startswith('st ') for r in rows[:line] + rows[line + 1:]))
        self.assertEqual(re.findall(r'data-n="(\d+)"', html), [str(k) for k in range(1, len(rows))])
        self.assertEqual(html.count('data-servings-form'), 1)

    def test_the_views_on_the_one_page(self):
        self.client.post('/login', data={'email': 'admin@test', 'password': 'pw'})
        rid = self.ids["carbonara"]
        html = self.client.get(f'/recipe/{rid}').get_data(as_text=True)
        # The timeline and the metro map with the chosen step beside them; the map as a transit map with time
        self.assertIn('class="vpanel split tl-panel"', html)
        self.assertIn('class="vpanel split mt-panel"', html)
        # The rail, the timeline, the metro map and the delta all have the page card
        self.assertEqual(html.count('class="side-card pagecard"'), 4)
        # The delta: the card and every step on it as trials, the steps it folds away listed on their box
        self.assertIn('class="vpanel dv-rivers dv-progress dl-panel"', html)
        self.assertNotIn('data-dlx="float"', html)  # the step in a strip; the small card is gone
        # The key to the delta's signs, and the trial for how a tap on a step's number works
        self.assertIn('class="dl-key"', html)
        self.assertIn('What is done to it first', html)  # one sign per group in the state catalog
        self.assertIn('temperature and texture: softened, melted', html)
        self.assertIn('data-state="', html)  # the word for how a cut ingredient is cut, on its sign
        self.assertIn('data-dltap="1"', html)
        self.assertIn('data-dltap="2"', html)
        self.assertIn('data-dlx="steps"', html)
        self.assertIn('class="fx-folds"', html)
        # The metro map: its parts as buttons (a trial), each station and name on its part's line, clock times down the side
        self.assertIn('data-mt-lane="0"', html)
        self.assertIn('class="mt-ticks"', html)
        self.assertRegex(html, r'class="mt-ticks"[^<]*<li[^>]*data-min="0"')
        # Its parts in two forms (a trial): a row above the map, or each above its own line
        self.assertIn('data-mtx="row"', html)
        self.assertIn('data-mtx="lines"', html)
        self.assertEqual(html.count('class="mt-head '), html.count('class="mt-part '))
        self.assertEqual(html.count('class="mt-term '), html.count('class="mt-part '))
        self.assertIn('data-mtx="ends"', html)
        # The line in full down to where you are; the trials Times and Work are gone
        self.assertIn('data-mt-travelled', html)
        self.assertNotIn('data-mtt=', html)
        for part in ('class="mt"', 'class="mt-key"', 'data-mt-now', 'class="mt-ticks"'):
            self.assertIn(part, html)
        # The delta with rivers, filling as you cook
        self.assertIn('class="vpanel dv-rivers dv-progress dl-panel"', html)
        self.assertIn('data-delta-flow', html)
        self.assertNotIn('data-trial-key', html)

    def test_the_overview_layouts_on_the_one_page(self):
        rid = self.ids["carbonara"]
        self.client.post('/login', data={'email': 'admin@test', 'password': 'pw'})
        # A, the poster, unless C is chosen; the first layout, with the bar at the bottom, is gone
        for cookie, key in (('now', 'poster'), ('poster', 'poster'), ('compact', 'compact')):
            self.client.set_cookie('overview_layout', cookie)
            html = self.client.get(f'/recipe/{rid}').get_data(as_text=True)
            for text in (f'class="ovl ovl-{key}"', 'overview_layouts.css', 'js/overview_fit.js', 'data-fit-ings', 'data-site-menu',
                         'id="sheet-more"', 'data-jump="more-facts"' if key == 'poster' else 'data-jump="more-top"',
                         'data-cook-open', 'id="cook"', 'id="sheet-bowls"', 'class="slist focus"', f'data-ov="{key}" aria-pressed="true"'):
                self.assertIn(text, html)
            for gone in ('class="ov-bar"', 'class="factbar"', 'data-ov="now"'):
                self.assertNotIn(gone, html)
            self.assertEqual(html.count('data-servings-form'), 1)  # in the layout, not again in the sheet
            # The time and the equipment in the sheet; in C also beside the ingredients
            self.assertEqual(html.count('class="tstrip"'), 2 if key == 'compact' else 1)
            self.assertIn('id="more-tools"', html)
            self.assertEqual('class="cc-glance"' in html, key == 'compact')

    def test_the_steps_are_a_rail_beside_the_step_you_are_on(self):
        self.client.post('/login', data={'email': 'admin@test', 'password': 'pw'})
        rid = self.ids["carbonara"]
        html = self.client.get(f'/recipe/{rid}').get_data(as_text=True)
        # One list, fitted to the height on a wide screen, beside the card with what belongs to the page
        self.assertEqual(html.count('data-slist'), 1)
        self.assertIn('class="rail-main" data-fit-steps', html)
        self.assertIn('data-total="', html)
        for part in ('data-side-card-count', 'data-side-card-left', 'data-side-card-needs', 'data-sc-done', 'data-side-card-then', 'css/rail.css'):
            self.assertIn(part, html)
        self.assertEqual(len(re.findall(r'class="side-card[ "]', html)), 4)  # the rail, the timeline, the metro map and the delta
        self.assertEqual(len(re.findall(r'data-st="[^"]+"[^>]*data-at="\d+"', html)), html.count('class="st-tick"'))
        # data-start marks a timer button (static/js/steps.js); on a step it made every tap on it start a timer
        self.assertIsNone(re.search(r'<li[^>]*\bdata-start\b', html))
        # The free time for "While you wait" and the clock; no trials left
        self.assertIn('data-from="', html)
        self.assertIn('data-min="', html)
        self.assertNotIn('data-tlx="', html)
        self.assertNotIn('data-fx="', html)
        self.assertNotIn('data-rx="', html)
        self.assertNotIn('data-sl="', html)

    def test_the_time_strip_is_prep_cook_and_serve(self):
        from services.recipe_v2.view import time_strip
        steps = [{'start': 0, 'heat': False, 'phase': 'prep'}, {'start': 15, 'heat': True, 'phase': 'cook'},
                 {'start': 40, 'heat': False, 'phase': 'serve'}]
        self.assertEqual([(p['phase'], p['minutes']) for p in time_strip(steps, 45)], [('prep', 15), ('cook', 25), ('serve', 5)])
        # Never heated: one part; heated from the first step: no prep
        self.assertEqual([p['phase'] for p in time_strip(steps[:1], 10)], ['prep'])
        self.assertEqual([p['phase'] for p in time_strip([{'start': 0, 'heat': True, 'phase': 'cook'}], 10)], ['cook'])

    def test_a_long_wait_on_the_metro_map_is_cut_short(self):
        from services.recipe_v2 import whole
        v2 = {'components': [{'local_id': 'c1', 'name': 'Dish'}],
              'steps': [{'local_id': 'a', 'short': 'Marinate', 'phase': 'prep', 'component_id': 'c1', 'uses': ['i1'], 'after': [],
                         'active_minutes': 5, 'passive_minutes': 60},
                        {'local_id': 'b', 'short': 'Grill', 'phase': 'cook', 'component_id': 'c1', 'uses': ['i2'], 'after': ['a'],
                         'active_minutes': 10, 'passive_minutes': 0}]}
        sch = {'order': ['a', 'b'], 'T': 75, 'plan': {'a': {'start': 0, 'a_end': 5, 'end': 65}, 'b': {'start': 65, 'a_end': 75, 'end': 75}}}
        m = whole.metro_map(v2, sch, {'c1': 'Dish'})
        self.assertEqual([(br['minutes'], br['from'], br['to']) for br in m['breaks']], [(65, 0, 65)])
        a, b = m['stations']
        self.assertLess(b['y'] - a['y'], 65 * 4)  # drawn far shorter than 65 minutes
        self.assertTrue(all(not 0 < t['m'] < 65 for t in m['ticks']))  # no minute marks inside the cut

    def test_drafts_only_for_admins(self):
        url = f'/recipe/{self.ids["lasagne"]}'
        self.assertEqual(self.client.get(url).status_code, 302)
        self.client.post('/login', data={'email': 'admin@test', 'password': 'pw'})
        self.assertEqual(self.client.get(url).status_code, 200)

    def test_a_recipe_with_no_steps_is_only_its_overview(self):
        from database.models import RecipeStep
        recipe = db.session.get(Recipe, self.ids['carbonara'])
        for line in recipe.lines:
            db.session.delete(line)
        for step in db.session.execute(db.select(RecipeStep).where(RecipeStep.recipe_id == recipe.id)).scalars():
            db.session.delete(step)
        db.session.commit()
        status, html = self.page('carbonara')
        self.assertEqual(status, 200)
        self.assertIn('No steps yet.', html)
        for gone in ('id="cook"', 'id="sheet-bowls"', 'data-cook-open'):
            self.assertNotIn(gone, html)

if __name__ == '__main__':
    unittest.main()
