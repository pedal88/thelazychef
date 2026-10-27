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


def test_each_state_has_a_sign_from_its_group_or_its_own():
    assert (states.mark('chop'), states.mark('juice'), states.mark('soften'), states.mark('grind')) == ('knife', 'squeezer', 'thermometer', None)
    signs = [row[0] for row in states.key()]
    assert signs == ['knife', 'grater', 'squeezer', 'mortar', 'peeler', 'thermometer', 'whisk']
    assert 'softened' in dict((s, w) for s, _, w in states.key())['thermometer']


def test_what_takes_time_on_the_counter_is_taken_out_first():
    from services.recipe_v2 import mise
    v2 = {'ingredients': [{'local_id': 'i1', 'name': 'smør', 'state': 'soften'},
                          {'local_id': 'i2', 'name': 'smør', 'state': 'soften'},
                          {'local_id': 'i3', 'name': 'frosne erter', 'state': 'thaw'},
                          {'local_id': 'i4', 'name': 'løk', 'state': 'chop'}],
          'steps': [{'local_id': 's1', 'uses': ['i4']}, {'local_id': 's2', 'uses': ['i1', 'i3']}, {'local_id': 's3', 'uses': ['i2']}]}
    order = ['s1', 's2', 's3']
    jobs = mise.early(v2, order, {sid: n for n, sid in enumerate(order, 1)}, 'nb')
    assert [(j['short'], j['text']) for j in jobs] == [('Ta ut smør', 'Skal være romtemperert til steg 2.'),
                                                       ('Ta ut frosne erter', 'Skal være tint til steg 2.')]


def test_the_shopping_list_says_the_kind_to_buy():
    from services.recipe_v2.read import shopping_list
    v2 = {'components': [], 'ingredients': [
        {'local_id': 'i1', 'name': 'poteter', 'amount': 800, 'unit': 'g', 'variety': 'melne', 'state': 'strips'},
        {'local_id': 'i2', 'name': 'løk', 'amount': 1, 'unit': 'piece'}]}
    assert [e['varieties'] for e in shopping_list(v2)] == [['melne'], []]


def test_a_measured_line_keeps_an_old_cut_only_when_its_note_says_so():
    # The old generation gave salt and pepper the cut of their step ("Cut and season the chicken")
    r = recipe(
        [{'local_id': 'i1', 'name': 'salt', 'unit': 'tsp', 'cut': 'chop'},
         {'local_id': 'i2', 'name': 'ground black pepper', 'unit': 'tsp', 'cut': 'chop', 'prep_style': 'freshly ground'},
         {'local_id': 'i3', 'name': 'persille', 'unit': 'tbsp', 'cut': 'chop', 'prep_style': 'hakket'},
         {'local_id': 'i4', 'name': 'chicken thighs', 'unit': 'g', 'cut': 'chop'}],
        [{'local_id': 's1', 'phase': 'prep', 'method': 'chop', 'uses': ['i1', 'i2', 'i3', 'i4']}])
    states.fill(r)
    got = {i['local_id']: i.get('state') for i in r['ingredients']}
    assert got == {'i1': None, 'i2': 'grind', 'i3': 'chop', 'i4': 'chop'}
