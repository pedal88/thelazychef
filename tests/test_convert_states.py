"""Step 4 of the state catalog: the plan for the saved v2 recipes (scripts/convert_states.py). No database."""
import os

os.environ.setdefault('GOOGLE_API_KEY', 'test-key')

from scripts.convert_states import plan_recipe  # noqa: E402


def test_the_plan_lists_what_changes_where_it_comes_from_and_what_to_look_at():
    v2 = {'ingredients': [
        {'local_id': 'i1', 'name': 'løk', 'unit': 'piece', 'cut': 'chop', 'prep_style': 'finhakket'},
        {'local_id': 'i2', 'name': 'poteter', 'unit': 'g', 'prep_style': 'melne, i staver'},
        {'local_id': 'i3', 'name': 'persille', 'unit': 'bunch'},
        {'local_id': 'i4', 'name': 'salt', 'unit': 'tsp', 'prep_style': 'etter smak'}],
        'steps': [{'local_id': 's1', 'phase': 'prep', 'method': 'chop', 'short': 'Hakk', 'uses': ['i1', 'i3']},
                  {'local_id': 's2', 'phase': 'prep', 'method': 'slice', 'short': 'Skjær potetene', 'uses': ['i2']},
                  {'local_id': 's3', 'phase': 'cook', 'method': 'simmer', 'short': 'Kok', 'uses': ['i4']}]}
    rows = {r['local_id']: r for r in plan_recipe(v2, {'i1': 11, 'i2': 12, 'i3': 13, 'i4': 14})}
    assert set(rows) == {'i1', 'i2', 'i3'}  # salt to taste stays as it is
    assert (rows['i1']['source'], rows['i1']['after']['state'], rows['i1']['after']['grade']) == ('cut', 'chop', 'fine')
    assert rows['i1']['before'] == {'state': None, 'grade': None, 'variety': None, 'prep_style': 'finhakket'}
    assert (rows['i2']['source'], rows['i2']['after']['state'], rows['i2']['after']['variety']) == ('note', 'strips', 'melne')
    assert rows['i2']['after']['prep_style'] is None and 'variety' in rows['i2']['flags']
    assert (rows['i3']['source'], rows['i3']['after']['state'], rows['i3']['flags']) == ('step', 'chop', ['mixed_step'])
    assert rows['i3']['line_id'] == 13


def test_a_state_from_the_old_cut_on_a_measured_line_is_taken_back():
    # Recipe 308: salt and pepper converted to "chopped" from the cut of "Cut and season chicken"
    v2 = {'ingredients': [
        {'local_id': 'i1', 'name': 'salt', 'unit': 'tsp', 'cut': 'chop', 'state': 'chop'},
        {'local_id': 'i2', 'name': 'chicken thighs', 'unit': 'g', 'cut': 'chop', 'state': 'chop'}],
        'steps': [{'local_id': 's1', 'phase': 'prep', 'method': 'chop', 'short': 'Cut and season chicken', 'uses': ['i1', 'i2']}]}
    rows = {r['local_id']: r for r in plan_recipe(v2, {'i1': 21, 'i2': 22})}
    assert set(rows) == {'i1'}  # the chicken is cut; the salt is not
    assert (rows['i1']['before']['state'], rows['i1']['after']['state'], rows['i1']['source']) == ('chop', None, 'cut')
