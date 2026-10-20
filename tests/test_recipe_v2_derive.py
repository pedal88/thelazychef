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
    assert derive.main_protein(lines) == 'Pork'
    assert derive.main_protein(lines[:1]) == 'Eggs'
    assert derive.main_protein([line('onion', 'vegetables', 'onions', 200)]) is None
    assert derive.main_protein([SimpleNamespace(gram_weight=10, ingredient=None)]) is None
