import copy
import glob
import json
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from services.recipe_v2_validator import validate_recipe_v2  # noqa: E402

FASIT = sorted(glob.glob(os.path.join(ROOT, 'data', 'pilot_v2', 'fasit', '*.json')))


def load(name):
    with open(os.path.join(ROOT, 'data', 'pilot_v2', 'fasit', name + '.json'), encoding='utf-8') as f:
        return json.load(f)


def step(r, sid):
    return next(s for s in r['steps'] if s['local_id'] == sid)


def rules(r):
    return validate_recipe_v2(r)['failed_rules']


@pytest.mark.parametrize('path', FASIT, ids=[os.path.basename(p) for p in FASIT])
def test_fasit_is_valid(path):
    with open(path, encoding='utf-8') as f:
        result = validate_recipe_v2(json.load(f))
    assert result['errors'] == []


def test_rule1_duplicate_id():
    r = load('carbonara')
    r['steps'][1]['local_id'] = 's1'
    assert 1 in rules(r)


def test_rule2_unknown_after_and_step_placeholder():
    r = load('carbonara')
    step(r, 's4')['after'] = ['s99']
    assert 2 in rules(r)
    r = load('carbonara')
    step(r, 's4')['text'] = 'Legg {s3} i panna.'
    assert 2 in rules(r)


def test_rule3_placeholder_not_in_uses():
    r = load('carbonara')
    step(r, 's9')['text'] += ' Dryss over {i7}.'
    assert rules(r) == [3]


def test_rule4_unused_and_double_used():
    r = load('carbonara')
    step(r, 's9')['uses'] = []
    step(r, 's9')['text'] = 'Server carbonaraen med en gang.'
    assert rules(r) == [4]
    r = load('carbonara')
    step(r, 's9')['uses'].append('i5')
    step(r, 's9')['text'] += ' {i5}'
    assert 4 in rules(r)


def test_rule5_cycle_and_two_final_steps():
    r = load('carbonara')
    step(r, 's3')['after'] = ['s9']
    assert 5 in rules(r)
    r = load('lasagne')
    final = r['steps'][-1]
    final['after'] = [a for a in final['after'] if a != 's14']
    assert 5 in rules(r)


def test_rule5_ignores_preheat_and_equipment_only_steps():
    r = load('brownies')
    assert step(r, 's1')['setup'] and not step(r, 's1')['after']
    assert not step(r, 's2')['uses'] and not step(r, 's2')['after']
    assert 5 not in rules(r)


def test_rule6_heat_method_must_be_cook():
    r = load('lasagne')
    step(r, 's3')['phase'] = 'prep'
    assert rules(r) == [6]


def test_rule7_catalogs():
    r = load('tikka')
    step(r, 's2')['method'] = 'stir'
    step(r, 's2')['equipment'] = ['mixing_bowl']
    r['ingredients'][0]['unit'] = 'gram'
    assert rules(r) == [7]


def test_rule8_amount():
    r = load('lasagne')
    r['ingredients'][0]['amount'] = 0
    assert rules(r) == [8]
    r = load('lasagne')
    del r['ingredients'][0]['amount']
    assert 8 in rules(r)


def test_warning_time_words_but_technique_ok():
    r = load('lasagne')
    assert not [w for w in validate_recipe_v2(r)['warnings'] if w['code'] == 'time_words']  # «mens du visper»
    step(r, 's11')['text'] = 'Skyll {i19} mens lasagnen står i ovnen.'
    assert [w for w in validate_recipe_v2(r)['warnings'] if w['code'] == 'time_words']
