"""The state catalog: states in words, states read from a note, and filling the states of a recipe."""
import os

os.environ.setdefault('GOOGLE_API_KEY', 'test-key')

from services.recipe_v2 import states  # noqa: E402


def recipe(lines, steps):
    return {'ingredients': lines, 'steps': steps}


def test_a_state_is_written_with_its_grade():
    assert states.word('chop', 'fine') == 'finely chopped'
    assert states.word('chop', 'fine', 'nb') == 'fint hakket'
    assert states.word('whipped', 'stiff', 'nb') == 'pisket (stive topper)'
    assert states.word('chop', 'stiff') == 'chopped'  # a grade the state does not have is left out
    assert states.word(None) == ''


def test_a_note_says_a_state_a_grade_and_the_rest():
    assert states.from_text('finhakket') == ('chop', 'fine', '')
    assert states.from_text('thinly sliced, optional') == ('slice', 'thin', 'optional')
    assert states.from_text('straight from the fridge')[0] == 'chill'
    assert states.from_text('melne') == (None, None, 'melne')


def test_fill_takes_the_state_from_the_note_the_old_cut_or_the_prep_step():
    r = recipe(
        [{'local_id': 'i1', 'name': 'løk', 'unit': 'piece', 'prep_style': 'finhakket'},
         {'local_id': 'i2', 'name': 'skinke', 'unit': 'g', 'cut': 'slice', 'prep_style': 'tynne skiver'},
         {'local_id': 'i3', 'name': 'ris', 'unit': 'g'}],
        [{'local_id': 's1', 'phase': 'prep', 'method': 'chop', 'uses': ['i1']},
         {'local_id': 's2', 'phase': 'prep', 'method': 'slice', 'uses': ['i2']},
         {'local_id': 's3', 'phase': 'prep', 'method': 'rinse', 'uses': ['i3']}])
    assert states.fill(r) == 3
    got = {i['local_id']: (i.get('state'), i.get('grade'), i.get('prep_style'), i.get('cut')) for i in r['ingredients']}
    assert got == {'i1': ('chop', 'fine', None, None), 'i2': ('slice', 'thin', None, None), 'i3': ('rinse', None, None, None)}


def test_fill_leaves_products_and_what_a_step_only_mixes_in():
    r = recipe(
        [{'local_id': 'i1', 'name': 'hermetiske tomater', 'unit': 'g', 'prep_style': 'hakkede'},
         {'local_id': 'i2', 'name': 'epler', 'unit': 'piece'},
         {'local_id': 'i3', 'name': 'sitronsaft', 'unit': 'tbsp'},
         {'local_id': 'i4', 'name': 'kanel', 'unit': 'tsp'}],
        [{'local_id': 's1', 'phase': 'prep', 'method': 'slice', 'uses': ['i2', 'i3', 'i4']},
         {'local_id': 's2', 'phase': 'cook', 'method': 'simmer', 'uses': ['i1']}])
    states.fill(r)
    got = {i['local_id']: (i.get('state'), i.get('prep_style')) for i in r['ingredients']}
    assert got == {'i1': (None, 'hakkede'), 'i2': ('slice', None), 'i3': (None, None), 'i4': (None, None)}


def test_fill_keeps_a_state_the_model_gave():
    r = recipe([{'local_id': 'i1', 'name': 'smør', 'unit': 'g', 'state': 'soften'}],
               [{'local_id': 's1', 'phase': 'prep', 'method': 'melt', 'uses': ['i1']}])
    assert states.fill(r) == 0
    assert r['ingredients'][0]['state'] == 'soften'


def test_a_null_state_from_the_model_is_not_taken_from_the_step():
    r = recipe(
        [{'local_id': 'i1', 'name': 'peanøtter', 'unit': 'g', 'state': 'crush'},
         {'local_id': 'i2', 'name': 'koriander', 'unit': 'bunch', 'state': None},
         {'local_id': 'i3', 'name': 'hvitløk', 'unit': 'clove', 'state': None, 'prep_style': 'finhakket'}],
        [{'local_id': 's1', 'phase': 'prep', 'method': 'crush', 'uses': ['i1', 'i2', 'i3']}])
    states.fill(r)
    got = [(i.get('state'), i.get('grade'), 'state' in i) for i in r['ingredients']]
    assert got == [('crush', None, True), (None, None, False), ('chop', 'fine', True)]  # a note still says a state
