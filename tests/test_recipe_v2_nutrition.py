"""Nutrition for v2 recipes (services/recipe_v2/nutrition.py)."""
import json
import os
import sys
from types import SimpleNamespace

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault('DB_BACKEND', 'local')
os.environ.setdefault('DATABASE_URL', 'sqlite://')
os.environ.setdefault('GOOGLE_API_KEY', 'test-key')

from services.recipe_v2 import nutrition, persona  # noqa: E402


def ing(kcal=100, carbs=10, sodium=0, default_unit='g', density=None):
    return SimpleNamespace(calories_per_100g=kcal, protein_per_100g=5, carbs_per_100g=carbs, fat_per_100g=2,
                           fat_saturated_per_100g=1, fiber_per_100g=1, sugar_per_100g=1, cholesterol_mg_per_100g=0,
                           sodium_mg_per_100g=sodium, calcium_mg_per_100g=0, potassium_mg_per_100g=0,
                           default_unit=default_unit, average_g_per_unit=density, name='x')


def line(name, amount, unit, gram_weight=None, ingredient=None):
    return SimpleNamespace(name=name, amount=amount, unit=unit, gram_weight=gram_weight, ingredient=ingredient)


def test_grams_prefers_the_estimate_then_weight_units_then_liquid_density():
    assert nutrition.grams(line('pasta water', 3, 'l', gram_weight=0)) == 0
    assert nutrition.grams(line('flour', 0.5, 'kg')) == 500
    assert nutrition.grams(line('milk', 2, 'dl', ingredient=ing(default_unit='ml', density=1.03))) == 206
    assert nutrition.grams(line('onion', 1, 'piece', ingredient=ing())) is None
    assert nutrition.grams(line('salt', None, None)) is None


def test_compute_needs_grams_for_every_measured_line_and_enough_nutrition():
    lines = [line('pasta', 400, 'g', ingredient=ing(kcal=350)), line('salt', None, None)]
    r = nutrition.compute(lines)
    assert r['totals']['calories'] == 1400 and r['coverage'] == 1
    r = nutrition.compute(lines + [line('onion', 1, 'piece', ingredient=ing())])
    assert r['totals']['calories'] is None and r['no_grams'] == ['onion']
    # Unknown to the pantry: fine below 5 % of the weight, not above
    r = nutrition.compute(lines + [line('mystery spice', 5, 'g')])
    assert r['totals']['calories'] == 1400 and r['no_nutrition'] == ['mystery spice']
    r = nutrition.compute(lines + [line('mystery cheese', 100, 'g')])
    assert r['totals']['calories'] is None


def test_per_serving_rounds_and_turns_sodium_into_salt():
    recipe = SimpleNamespace(base_servings=4, **{'total_' + f: v for f, v in dict(
        calories=2000, protein=100, carbs=200, fat=80, saturated_fat=20, fiber=12, sugar=30, cholesterol_mg=0,
        sodium_mg=4000, calcium_mg=0, potassium_mg=0).items()})
    s = nutrition.per_serving(recipe)
    assert (s['kcal'], s['carbs'], s['salt']) == (500, 50, 2.5)
    recipe.total_calories = None
    assert nutrition.per_serving(recipe) is None


def test_low_carb_rule_is_checked_once_there_is_nutrition():
    with open(os.path.join(ROOT, 'data', 'agents', 'chefs.json'), encoding='utf-8') as f:
        low = next(c for c in json.load(f)['chefs'] if c['id'] == 'low_carb_chef')
    base = dict(prep_time_mins=20, cleanup_factor=2, spice_level=0, difficulty='Moderate', lines=[], base_servings=4)
    assert persona.check(SimpleNamespace(total_carbs=None, **base), low) == []
    assert persona.check(SimpleNamespace(total_carbs=60, **base), low) == []
    assert persona.check(SimpleNamespace(total_carbs=200, **base), low) == ['About 50 g carbs a serving; The Low Carb Chef allows 20.']


def test_a_saved_carbonara_gets_its_nutrition():
    from app import app
    from database.models import Ingredient, Recipe, db
    from services.recipe_v2 import derive
    from services.recipe_v2.store import save_v2, to_v2

    with open(os.path.join(ROOT, 'data', 'pilot_v2', 'fasit', 'carbonara.json'), encoding='utf-8') as f:
        data = json.load(f)
    with app.app_context():
        db.drop_all()
        db.create_all()
        ids, expected = {}, 0
        for n, i in enumerate(data['ingredients']):
            kcal = 0 if i['name'] in ('vann', 'salt') else 300
            row = Ingredient(food_id=f'T{n}', name=i['name'] + str(n), status='active', default_unit='g', main_category='other',
                             calories_per_100g=kcal, protein_per_100g=10, carbs_per_100g=20, fat_per_100g=10)
            db.session.add(row)
            db.session.flush()
            ids[i['local_id']] = row.id
            expected += i['gram_weight_estimate'] * kcal / 100
        recipe = Recipe(title='x', cuisine='', difficulty='')
        db.session.add(recipe)
        save_v2(recipe, data, ids)
        db.session.flush()
        derive.apply(recipe, to_v2(recipe))
        assert round(recipe.total_calories) == round(expected)
        assert nutrition.per_serving(recipe)['kcal'] == round(expected / 4)
        db.session.rollback()
        db.drop_all()
