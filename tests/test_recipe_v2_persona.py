"""Chef personas in v2 generation (services/recipe_v2/persona.py): the prompt text and the hard rules."""
import json
import os
import sys
from types import SimpleNamespace

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from services.chef_service import rules_of  # noqa: E402
from services.recipe_v2 import persona  # noqa: E402


def seed(chef_id):
    with open(os.path.join(ROOT, 'data', 'agents', 'chefs.json'), encoding='utf-8') as f:
        c = next(c for c in json.load(f)['chefs'] if c['id'] == chef_id)
    return dict(c, constraints=rules_of(c['constraints']))


def recipe(**kw):
    base = dict(prep_time_mins=15, cleanup_factor=1, spice_level=0, difficulty='Simplistic', lines=[])
    return SimpleNamespace(**{**base, **kw})


def line(name, main='vegetables', pantry_name=None):
    return SimpleNamespace(name=name, ingredient=SimpleNamespace(name=pantry_name or name, main_category=main))


def test_three_philosophies_are_offered_and_the_six_retired():
    with open(os.path.join(ROOT, 'data', 'agents', 'chefs.json'), encoding='utf-8') as f:
        chefs = json.load(f)['chefs']
    active = [c['id'] for c in chefs if c.get('active', True)]
    assert active == ['the_classicist', 'the_smart_cook', 'the_minimalist']
    assert {c['id'] for c in chefs if c.get('active') is False} == {
        'french_classic', 'meta_learner', 'low_carb_chef', 'speezy_gonzales', 'family_cook', 'the_green_chef'}
    for c in chefs:
        assert set(c['constraints']) <= set(rules_of({})), c['id']
        assert os.path.exists(os.path.join(ROOT, 'static', 'chefs', c.get('image_filename') or 'missing')) or not c.get('active', True), c['id']
    for c in chefs[:3]:
        assert c['ingredient_logic']['strategy'], c['id']
    text = json.dumps(chefs)
    for gone in ('4-Hour', 'Slow-Carb', 'DiSSS', 'CaFE', 'Seed Oils', 'taste_range'):
        assert gone not in text


def tiered(name, tier):
    return SimpleNamespace(name=name, ingredient=SimpleNamespace(name=name, main_category='vegetables', tier=tier))


def test_the_minimalist_counts_ingredients_and_what_is_outside_the_foundation():
    p = seed('the_minimalist')
    lines = [tiered('salt', 'staple'), tiered('olive oil', 'staple'), tiered('onion', 'foundation'),
             tiered('chicken breast', 'foundation'), tiered('harissa', 'core'), tiered('preserved lemon', 'long_tail'),
             SimpleNamespace(name='saffron', ingredient=None)]
    notes = persona.check(recipe(lines=lines), p)
    assert any('outside the foundation pantry (harissa, preserved lemon, saffron)' in n and 'allows 1' in n for n in notes)
    assert not any('besides the staples' in n for n in notes)  # 5 ingredients, the staples not counted
    many = lines + [tiered(f'veg {k}', 'foundation') for k in range(3)]
    assert any('Uses 8 ingredients besides the staples' in n for n in persona.check(recipe(lines=many), p))


def test_the_philosophy_goes_into_the_prompt():
    p = dict(seed('the_minimalist'), foundation=['chicken breast', 'onion'])
    text = persona.prompt_block(p)
    for part in ('The Minimalist', 'at most 6 ingredients besides salt, pepper', 'at most 1 ingredients that are not in the FOUNDATION',
                 'Approach: Strip the dish', 'from a jar or tube', 'Ready-made sauces', 'FOUNDATION (', 'chicken breast, onion'):
        assert part in text, part
    assert 'Use fresh herbs' in persona.prompt_block(seed('the_classicist'))


def test_settings_go_on_top_of_any_chef():
    p = persona.with_settings(seed('the_smart_cook'), ['low_carb', 'kid_friendly', 'vegetarian', 'unknown'])
    rules = p['constraints']
    assert (rules['max_carbs_per_serving'], rules['max_spice'], rules['diet']) == (20, 1, 'vegetarian')
    assert rules['max_total_minutes'] == 45  # the chef's own rules stay
    assert p['settings'] == ['low_carb', 'kid_friendly', 'vegetarian']
    text = persona.prompt_block(p)
    assert 'The Smart Cook' in text and 'Low carb:' in text and 'For children:' in text and 'Vegetarian:' in text
    assert seed('the_smart_cook')['constraints']['diet'] is None  # the chef itself is not changed
    # Without a chef the settings alone
    alone = persona.with_settings(None, ['vegetarian'])
    assert persona.prompt_block(alone).startswith('Rules: no meat or fish')
    assert any('Not vegetarian' in n for n in persona.check(recipe(lines=[line('bacon', 'meat')]), alone))
    assert persona.with_settings(None, []) is None


def test_prompt_block_turns_the_rules_into_instructions():
    text = persona.prompt_block(seed('speezy_gonzales'))
    assert text.startswith('Write it as Speezy Gonzales (The Shortcut King)')
    assert 'at most 20 minutes' in text and 'as few pots, pans and bowls' in text
    assert 'Difficulty: easy for a home cook.' in text
    assert 'Toss it in the air fryer' in text
    green = persona.prompt_block(seed('the_green_chef'))
    assert 'no meat or fish (dairy and eggs are fine)' in green
    assert 'at most mildly hot' in persona.prompt_block(seed('family_cook'))
    assert persona.prompt_block(None) == ''


def test_check_lists_every_broken_rule():
    speezy = seed('speezy_gonzales')
    assert persona.check(recipe(), speezy) == []
    notes = persona.check(recipe(prep_time_mins=35, cleanup_factor=3, difficulty='Moderate'), speezy)
    assert len(notes) == 3
    assert notes[0] == 'Takes 35 minutes; Speezy Gonzales allows 20.'
    assert persona.check(recipe(spice_level=2), seed('family_cook')) == ['Spice level is 2; The Family Cook allows 1.']


def test_vegetarian_and_banned_ingredients():
    green = seed('the_green_chef')
    lines = [line('kikerter'), line('halloumi', 'dairy and egg'), line('bacon', 'meat')]
    assert persona.check(recipe(lines=lines), green) == ['Not vegetarian: bacon.']
    low = seed('low_carb_chef')
    notes = persona.check(recipe(lines=[line('spaghetti', 'cereal grains and pasta', 'pasta')]), low)
    assert notes == ['Uses ingredients The Low Carb Chef never uses: spaghetti.']


def test_old_slider_chefs_keep_what_maps():
    old = {'taste_range': {'min': 3, 'max': 5}, 'complexity_range': {'min': 1, 'max': 2}, 'cleanup_range': {'min': 1, 'max': 2}}
    rules = rules_of(old)
    assert rules['difficulties'] == ['Simplistic', 'Moderate']
    assert rules['max_cleanup'] == 2
    assert rules['max_total_minutes'] is None
    assert 'taste_range' not in rules
