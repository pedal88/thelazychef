"""Nutrition for a v2 recipe (docs/RECIPE_MODEL_V2.md, section 9): one calculation, shown as approximate.

Grams per line come from the structure prompt (gram_weight_estimate, the part
that ends up in the food: none of the pasta water, a little of its salt). When
the model gave none, weight units are converted, and volumes of liquids use the
pantry density (average_g_per_unit when default_unit is ml). Lines "to taste"
have no amount and are left out.

A line in the state "cooked" (day-old rice, leftover pasta) is weighed cooked, while the pantry has most grains,
pasta and dried pulses dry. Its grams are then turned into dry grams with COOKED_GAIN before the pantry's values
are used. A pantry item whose values are already those of the cooked food (under DRY_KCAL a 100 g) is left as it is.

The totals are only kept when every measured line has grams and the lines with
pantry nutrition make up at least COVERAGE of the weight. Otherwise the recipe
shows no nutrition rather than a wrong number.
"""
import json
import os
import re
from functools import lru_cache

COVERAGE = 0.95
# How many times heavier a dry food gets when cooked (cooked g / dry g), by a word of the pantry name or its plural
# (so not "oat" in goat or "pea" in peanuts); the first that matches counts. From USDA dry and cooked values, rounded.
COOKED_GAIN = (('noodle', 2.4), ('rice', 2.8), ('quinoa', 2.7), ('couscous', 2.5), ('bulgur', 2.5), ('barley', 2.7),
               ('oat', 2.5), ('lentil', 2.5), ('chickpea', 2.4), ('bean', 2.5), ('pea', 2.5), ('pasta', 2.3),
               ('spaghetti', 2.3), ('macaroni', 2.3), ('penne', 2.3), ('fusilli', 2.3), ('tagliatelle', 2.3))
DRY_KCAL = 250  # a pantry item above this a 100 g is the dry food
# Recipe field -> Ingredient field, per 100 g
NUTRIENTS = (('calories', 'calories_per_100g'), ('protein', 'protein_per_100g'), ('carbs', 'carbs_per_100g'),
             ('fat', 'fat_per_100g'), ('saturated_fat', 'fat_saturated_per_100g'), ('fiber', 'fiber_per_100g'),
             ('sugar', 'sugar_per_100g'), ('cholesterol_mg', 'cholesterol_mg_per_100g'), ('sodium_mg', 'sodium_mg_per_100g'),
             ('calcium_mg', 'calcium_mg_per_100g'), ('potassium_mg', 'potassium_mg_per_100g'))


@lru_cache(maxsize=1)
def _units():
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                        'data', 'constraints', 'units.json')
    with open(path, encoding='utf-8') as f:
        return {u['id']: u for u in json.load(f)['units']}


def grams(line):
    """Grams of the line that end up in the food, or None when they cannot be known."""
    if line.gram_weight is not None:
        return line.gram_weight
    if line.amount is None:
        return None
    unit = _units().get(line.unit or '')
    if unit and unit.get('g'):
        return line.amount * unit['g']
    ing = line.ingredient
    if unit and unit.get('ml') and ing is not None and ing.default_unit == 'ml' and ing.average_g_per_unit:
        return line.amount * unit['ml'] * ing.average_g_per_unit
    return None


def dry_grams(line, g):
    """The grams to count the pantry values for: the dry weight of a cooked grain, pasta or pulse, else g."""
    ing = line.ingredient
    if getattr(line, 'state', None) != 'cooked' or ing is None or (ing.calories_per_100g or 0) < DRY_KCAL:
        return g
    name = (ing.name or '').lower()
    gain = next((x for word, x in COOKED_GAIN if re.search(r'\b' + word + r's?\b', name)), None)
    return g / gain if gain else g


def compute(lines):
    """Totals for the whole recipe and what is missing. Returns a dict:
    totals (field -> amount, or None when not shown), grams, coverage, no_grams and no_nutrition (line names)."""
    total_g = covered_g = 0.0
    sums = {field: 0.0 for field, _ in NUTRIENTS}
    no_grams, no_nutrition = [], []
    for line in lines:
        if line.amount is None:
            continue  # "to taste"
        g = grams(line)
        if g is None:
            no_grams.append(line.name)
            continue
        total_g += g
        ing = line.ingredient
        if ing is None or ing.calories_per_100g is None:
            if g:
                no_nutrition.append(line.name)
            continue
        covered_g += g
        counted = dry_grams(line, g)
        for field, per_100g in NUTRIENTS:
            sums[field] += counted * (getattr(ing, per_100g) or 0) / 100
    coverage = covered_g / total_g if total_g else 0.0
    ok = not no_grams and total_g > 0 and coverage >= COVERAGE
    return {'totals': {f: (round(v, 1) if ok else None) for f, v in sums.items()}, 'grams': round(total_g),
            'coverage': round(coverage, 3), 'no_grams': no_grams, 'no_nutrition': no_nutrition}


def apply(recipe):
    """Set the recipe's total_* fields (whole recipe), or clear them when the nutrition is not complete enough."""
    result = compute(recipe.lines)
    for field, value in result['totals'].items():
        setattr(recipe, 'total_' + field, value)
    return result


def per_serving(recipe):
    """Rounded per-serving values for the recipe page, or None when the recipe has no nutrition."""
    if recipe.total_calories is None:
        return None
    n = recipe.base_servings or 1
    v = {f: getattr(recipe, 'total_' + f) / n if getattr(recipe, 'total_' + f) is not None else None for f, _ in NUTRIENTS}
    return {'kcal': round(v['calories']), 'protein': round(v['protein']), 'carbs': round(v['carbs']),
            'net_carbs': round(v['carbs'] - (v['fiber'] or 0)), 'fat': round(v['fat']),
            'saturated_fat': round(v['saturated_fat'] or 0, 1), 'fiber': round(v['fiber'] or 0, 1),
            'sugar': round(v['sugar'] or 0), 'salt': round((v['sodium_mg'] or 0) * 2.5 / 1000, 1)}
