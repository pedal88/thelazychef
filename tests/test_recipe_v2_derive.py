"""Metadata derived from a v2 recipe (services/recipe_v2/derive.py), checked on the pilot reference recipes."""
import copy
import json
import os
import sys
from types import SimpleNamespace

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from services.recipe_v2 import derive  # noqa: E402


def fasit(name):
    with open(os.path.join(ROOT, 'data', 'pilot_v2', 'fasit', name + '.json'), encoding='utf-8') as f:
        return json.load(f)


@pytest.mark.parametrize('name, source', [('carbonara', 'pan'), ('lasagne', 'oven'), ('brownies', 'oven'), ('tikka', 'pot')])
def test_heat_source_is_what_the_dish_is_finished_in(name, source):
    assert derive.heat_source(fasit(name)) == source


def test_a_dish_without_heat_has_no_heat_source():
    r = fasit('carbonara')
    r['steps'] = [dict(s, method='mix', equipment=['bowl'], setup=False) for s in r['steps']]
    assert derive.heat_source(r) == 'none'
    assert not derive.one_pot(r)


def test_one_pot_means_one_vessel_with_heat():
    r = fasit('carbonara')
    assert not derive.one_pot(r)  # pasta pot and frying pan
    for s in r['steps']:
        if (s.get('equipment') or [None])[0] == 'frying_pan':
            s['equipment'] = ['large_pot'] + s['equipment'][1:]
    assert derive.one_pot(r)


def test_cleanup_counts_vessels_not_small_tools():
    r = fasit('carbonara')
    assert derive.cleanup_factor(r) == 3  # bowl, colander, frying pan, large pot
    more = copy.deepcopy(r)
    more['steps'][0]['equipment'] += ['whisk', 'grater', 'ladle']
    assert derive.cleanup_factor(more) == 3
    assert derive.cleanup_factor(fasit('tikka')) == 4


def line(name, main, sub, grams):
    return SimpleNamespace(gram_weight=grams, ingredient=SimpleNamespace(name=name, main_category=main, sub_category=sub))


def test_main_protein_prefers_the_heaviest_meat_or_fish():
    lines = [line('eggs', 'dairy and egg', 'eggs', 300), line('guanciale', 'meat', 'pork', 150),
             line('salmon', 'fish and seafood', 'salmon', 100)]
    assert derive.main_protein(lines) == 'Salmon'  # cured meat for flavour never beats real meat or fish
    assert derive.main_protein(lines[:1]) == 'Eggs'
    assert derive.main_protein([SimpleNamespace(gram_weight=10, ingredient=None)]) is None


def test_bacon_is_flavour_and_a_dish_without_protein_is_vegetarian():
    eggs, bacon = line('eggs', 'dairy and egg', 'eggs', 250), line('bacon', 'meat', 'pork', 200)
    assert derive.main_protein([eggs, bacon]) == 'Eggs'  # quiche lorraine: bacon counts as 100 g
    assert derive.main_protein([line('eggs', 'dairy and egg', 'eggs', 80), bacon]) == 'Pork'  # pancakes with bacon
    assert derive.main_protein([bacon, line('chicken breast', 'meat', 'chicken', 150)]) == 'Chicken'
    assert derive.main_protein([line('pork belly', 'meat', 'pork', 400), bacon]) == 'Pork'
    # Feta pasta, mushroom penne: nothing that counts as protein
    assert derive.main_protein([line('penne', 'cereal grains and pasta', 'pasta', 400),
                                line('feta', 'dairy and egg', 'cheese', 200)]) == 'Vegetarian'
    assert derive.main_protein([line('onion', 'vegetables', 'onions', 200)]) == 'Vegetarian'


def test_fish_by_kind_keeps_the_labels_people_filter_on():
    assert derive.main_protein([line('salmon fillet', 'fish and seafood', 'oily fish', 300)]) == 'Salmon'
    assert derive.main_protein([line('mackerel', 'fish and seafood', 'oily fish', 300)]) == 'Oily Fish'
    assert derive.main_protein([line('cod', 'fish and seafood', 'white fish', 300)]) == 'White Fish'
    assert derive.main_protein([line('shrimps', 'fish and seafood', 'shellfish', 300)]) == 'Shrimp'
    assert derive.main_protein([line('mussels', 'fish and seafood', 'shellfish', 300)]) == 'Shellfish'


def test_every_protein_label_can_be_filtered_on():
    """The labels main_protein writes are the recipe list's protein filter and the galaxy's protein planets."""
    import json
    import os
    with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'constraints',
                           'main_protein.json'), encoding='utf-8') as f:
        options = {e for c in json.load(f)['protein_types'] for e in c['examples']}
    labels = set(derive.MEAT_LABELS.values()) | {lab for _, lab in derive.OTHER_PROTEINS} | {derive.NO_PROTEIN}
    labels |= {lab for _, _, lab in derive.FISH_NAMES}
    assert labels <= options, labels - options
