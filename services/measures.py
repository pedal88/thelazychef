"""Amounts and temperatures in the reader's measuring system: metric or US.

Recipes are stored as written (data/constraints/units.json) with temperatures in °C, and everything that counts
(gram_weight, nutrition, the planner, Prep's bowls) reads the stored values. The measuring system is only how
they are shown: metric shows the metric units as stored and converts US units (cup, oz, lb, fl oz) to ml and g;
US converts weights to oz and lb, volumes to tsp, tbsp and cups, and °C to °F. Spoons and the countable and
approximate units (clove, pinch) are the same in both, except a length of ginger or cinnamon in cm, which is
inches in US.
"""
import json
import os
from functools import lru_cache

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SYSTEMS = {'metric': 'Metric', 'us': 'US'}
DEFAULT = 'metric'
# English plurals for the countable units (units.json has Norwegian plurals only).
UNIT_PLURALS = {'clove': 'cloves', 'pinch': 'pinches', 'can': 'cans', 'handful': 'handfuls', 'slice': 'slices',
                'sprig': 'sprigs', 'leaf': 'leaves', 'bunch': 'bunches', 'package': 'packages', 'cup': 'cups',
                'stalk': 'stalks', 'sheet': 'sheets', 'dash': 'dashes', 'drop': 'drops'}
US_UNITS = {'cup', 'fl_oz', 'oz', 'lb'}
SPOONS = {'tsp', 'tbsp'}
OZ, TSP, TBSP, CUP = 28.35, 5, 15, 240  # g, ml, ml, ml (the catalog's values)
INCH = 2.54  # cm


@lru_cache(maxsize=1)
def units():
    with open(os.path.join(ROOT, 'data', 'constraints', 'units.json'), encoding='utf-8') as f:
        return {u['id']: u for u in json.load(f)['units']}


def system_of(value):
    """A measuring system from a cookie or a setting: 'metric' or 'us', the default for anything else."""
    return value if value in SYSTEMS else DEFAULT


def frac(v):
    """1.5 -> "1½", 0.25 -> "¼". Kitchen amounts to the nearest quarter or third."""
    whole = int(v + 1e-9)
    rem = v - whole
    marks = [(0, ''), (0.25, '¼'), (1 / 3, '⅓'), (0.5, '½'), (2 / 3, '⅔'), (0.75, '¾'), (1, '')]
    best = min(marks, key=lambda m: abs(rem - m[0]))
    if best[0] == 1:
        whole, best = whole + 1, (0, '')
    return (str(whole) if whole else '') + best[1] or '0'


def _quarters(v):
    """To the nearest quarter, in kitchen fractions: 0.6 -> "½" (never thirds, which oz and tsp do not use)."""
    return frac(round(v * 4) / 4)


def _named(n, unit, amount):
    """n (as written) and the unit, plural when there is more than one: "1½ cups", but "1 cup" for 1.02."""
    name = (units().get(unit) or {}).get('name_en') or unit
    return f'{n} {UNIT_PLURALS.get(unit, name) if amount > 1 and n != "1" else name}'


def _metric(amount, unit):
    if unit in ('g', 'ml'):
        n = round(amount / 10) * 10 if amount >= 100 else round(amount / 5) * 5 if amount >= 10 else round(amount, 1)
        return f'{n:g} {unit}'
    if not unit or unit == 'piece':
        return frac(amount)
    return _named(frac(amount), unit, amount)


def _grams_us(g):
    oz = g / OZ
    if oz < 0.25:
        return _metric(g, 'g')  # a few grams (yeast, saffron): no honest fraction of an ounce
    if oz < 16:
        return f'{_quarters(oz) if oz < 4 else round(oz)} oz'
    return f'{_quarters(oz / 16)} lb'


def _ml_us(ml):
    if ml < TBSP - 1:
        return _named(_quarters(ml / TSP), 'tsp', 1)
    if ml < CUP / 4 - 2:
        return _named(frac(round(ml / TBSP * 2) / 2), 'tbsp', 1)
    cups = ml / CUP
    return _named(frac(cups), 'cup', cups)


def fmt_amount(amount, unit, system=DEFAULT):
    """"400 g", "1½ tbsp", "2 cloves", "3" (pieces have no unit); in US "14 oz", "¾ cup", "1½ in"."""
    if amount is None:
        return ''
    u = units().get(unit) or {}
    if system == 'us' and unit not in SPOONS:
        if u.get('type') == 'weight' and u.get('g'):
            return _grams_us(amount * u['g'])
        if u.get('type') == 'volume' and u.get('ml'):
            return _ml_us(amount * u['ml'])
        if unit == 'cm':
            return f'{_quarters(max(amount / INCH, 0.25))} in'
    elif unit in US_UNITS:
        return _metric(amount * u['g'], 'g') if u.get('g') else _metric(amount * u['ml'], 'ml')
    return _metric(amount, unit)


def degrees(c, system=DEFAULT):
    """The number on the dial: °C as stored, or °F rounded as US recipes write it (to 25 for the oven, to 5 for
    a core temperature: 175 -> 350, 60 -> 140)."""
    if c is None or system != 'us':
        return c
    f = c * 9 / 5 + 32
    step = 25 if c >= 120 else 5
    return int(round(f / step) * step)


def temp(c, system=DEFAULT):
    """"220 °C" or "425 °F"."""
    if c is None:
        return ''
    return f"{degrees(c, system)} {'°F' if system == 'us' else '°C'}"
