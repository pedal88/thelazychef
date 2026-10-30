"""Amounts and temperatures in the reader's measuring system: metric or US.

Recipes are stored as written (data/constraints/units.json) with temperatures in °C, and everything that counts
(gram_weight, nutrition, the planner, Prep's bowls) reads the stored values. The measuring system is only how
they are shown: metric shows the metric units as stored and converts US units (cup, oz, lb, fl oz) to ml and g;
US converts weights to oz and lb, volumes to tsp, tbsp and cups, and °C to °F. Spoons and the countable and
approximate units (clove, pinch) are the same in both, except a length of ginger or cinnamon in cm, which is
inches in US.

A weight of flour, sugar, butter or a spice is a volume for a US reader (data/constraints/us_volume.json), and a
shopping list sums one item's amounts across units (fmt_total).

Free text (a step's text, done_when and short, the chef's note, the yield) is written metric, as number, space,
unit ("200 °C", "3 cm", "20 × 30 cm", "2 dl"; the structuring prompt asks for it), and localize_text converts those
measures for a US reader. unconverted() finds what it cannot convert (cups or °F in the text, degrees with no
scale), for the validator's warning us_measure and scripts/units_report.py.
"""
import json
import os
import re
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
    if ml < TSP / 8:
        return _named('1', 'pinch', 1)  # a few strands of saffron: no honest fraction of a teaspoon
    if ml < TBSP - 1:
        return _named(_quarters(ml / TSP), 'tsp', 1)
    if ml < CUP / 4 - 2:
        return _named(frac(round(ml / TBSP * 2) / 2), 'tbsp', 1)
    cups = ml / CUP
    return _named(frac(cups), 'cup', cups)


@lru_cache(maxsize=1)
def _us_volume():
    with open(os.path.join(ROOT, 'data', 'constraints', 'us_volume.json'), encoding='utf-8') as f:
        return [dict(r, name=re.compile(r['name'], re.I) if r.get('name') else None) for r in json.load(f)['rules']]


def density(ingredient):
    """Grams per ml for a pantry item US recipes measure by volume (flour, sugar, butter, spices:
    data/constraints/us_volume.json), else None. ingredient is a pantry Ingredient (or None)."""
    if ingredient is None:
        return None
    name, sub = (getattr(ingredient, 'name', '') or '').lower(), getattr(ingredient, 'sub_category', None)
    for rule in _us_volume():
        if (rule['name'] and rule['name'].search(name)) or (rule.get('sub_category') and rule['sub_category'] == sub):
            return rule['g_per_ml']
    return None


def fmt_amount(amount, unit, system=DEFAULT, g_per_ml=None):
    """"400 g", "1½ tbsp", "2 cloves", "3" (pieces have no unit); in US "14 oz", "¾ cup", "1½ in". g_per_ml (density())
    is for a weight US recipes measure by volume: 250 g flour is "2 cups" for a US reader."""
    if amount is None:
        return ''
    u = units().get(unit) or {}
    if system == 'us' and unit not in SPOONS:
        if u.get('type') == 'weight' and u.get('g'):
            return _ml_us(amount * u['g'] / g_per_ml) if g_per_ml else _grams_us(amount * u['g'])
        if u.get('type') == 'volume' and u.get('ml'):
            return _ml_us(amount * u['ml'])
        if unit == 'cm':
            return f'{_quarters(max(amount / INCH, 0.25))} in'
    elif unit in US_UNITS:
        return _metric(amount * u['g'], 'g') if u.get('g') else _metric(amount * u['ml'], 'ml')
    return _metric(amount, unit)


def _base(amount, unit, system, g_per_ml):
    """(kind, amount in the kind's base unit) for summing: weights in g, volumes in ml (a US weight measured by
    volume too), anything else by its own unit."""
    u = units().get(unit) or {}
    if u.get('type') == 'weight' and u.get('g'):
        if system == 'us' and g_per_ml:
            return 'volume', amount * u['g'] / g_per_ml
        return 'weight', amount * u['g']
    if u.get('type') == 'volume' and u.get('ml'):
        return 'volume', amount * u['ml']
    return unit or 'piece', amount


def fmt_total(amounts, system=DEFAULT, g_per_ml=None):
    """The amounts of one item in a shopping list ([{'amount', 'unit'}]) as one sum per kind: "1 dl + 2 tbsp" is
    "1⅓ dl", and for a US reader "½ cup". Metric writes a sum in the unit with the largest share (a US unit's sum in g
    or ml); US in its own units. Counts are summed by unit ("2 cloves")."""
    kinds = {}
    for a in amounts:
        kind, base = _base(a['amount'], a['unit'], system, g_per_ml)
        k = kinds.setdefault(kind, {'total': 0.0, 'shares': {}, 'items': []})
        k['total'] += base
        k['shares'][a['unit']] = k['shares'].get(a['unit'], 0) + base
        k['items'].append(a)
    out = []
    for kind, k in kinds.items():
        if len(k['items']) == 1:
            a = k['items'][0]
            out.append(fmt_amount(a['amount'], a['unit'], system, g_per_ml))
        elif kind not in ('weight', 'volume'):
            out.append(fmt_amount(k['total'], kind, system))
        elif system == 'us':
            out.append(_ml_us(k['total']) if kind == 'volume' else _grams_us(k['total']))
        else:
            unit = max(k['shares'], key=k['shares'].get)
            if unit in US_UNITS:
                unit = 'g' if kind == 'weight' else 'ml'
            per = units()[unit]['g' if kind == 'weight' else 'ml'] if unit in units() else 1
            out.append(_metric(k['total'] / per, unit))
    return ' + '.join(out)


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


def _num(text):
    return float(text.replace(',', '.'))


def inches(cm):
    """A length in inches as US recipes write it: quarters for a cut ("1¼"), whole inches for a tin ("9")."""
    i = cm / INCH
    return str(round(i)) if i >= 4 else _quarters(max(i, 0.25))


NUM = r'\d+(?:[.,]\d+)?'
DASH = r'\s*[–-]\s*'
TEMP = re.compile(rf'(?P<a>{NUM})(?:{DASH}(?P<b>{NUM}))?\s*°\s*(?P<u>[CF])\b')
LENGTH = re.compile(rf'(?P<a>{NUM})(?:{DASH}(?P<b>{NUM}))?(?:\s*[×x]\s*(?P<c>{NUM}))?\s*(?P<u>cm|mm)\b')
AMOUNT = re.compile(rf'(?P<a>{NUM})(?:{DASH}(?P<b>{NUM}))?\s*(?P<u>kg|grams?|gram|g|ml|cl|dl|liters?|litres?|l)\b')
WRITTEN = {'gram': 'g', 'grams': 'g', 'liter': 'l', 'liters': 'l', 'litre': 'l', 'litres': 'l'}
US_TEXT = re.compile(rf'{NUM}\s*(?:°\s*F\b|(?:cups?|oz|ounces?|lbs?|pounds?|inch(?:es)?|quarts?|pints?|sticks?)\b|["”])'
                     rf'|{NUM}\s*°(?!\s*[CF])', re.I)


def _temps(m, system):
    c_to_f = system == 'us' and m['u'] == 'C'
    if not c_to_f and not (system != 'us' and m['u'] == 'F'):
        return m[0]
    conv = (lambda v: degrees(v, 'us')) if c_to_f else (lambda v: int(round((v - 32) * 5 / 9 / 5) * 5))
    nums = [conv(_num(m[k])) for k in ('a', 'b') if m[k]]
    return '–'.join(map(str, nums)) + (' °F' if c_to_f else ' °C')


def _lengths(m):
    mm = m['u'] == 'mm'
    nums = [inches(_num(m[k]) / (10 if mm else 1)) for k in ('a', 'b', 'c') if m[k]]
    if m['c']:
        return f'{nums[0]} × {nums[-1]} in'
    return '–'.join(nums) + ' in'


def _amounts(m):
    unit = WRITTEN.get(m['u'].lower(), m['u'])
    if not m['b']:
        return fmt_amount(_num(m['a']), unit, 'us')
    low, high = fmt_amount(_num(m['a']), unit, 'us'), fmt_amount(_num(m['b']), unit, 'us')
    n_low, _, u_low = low.partition(' ')
    n_high, _, u_high = high.partition(' ')
    return f'{n_low}–{high}' if u_low.rstrip('s') == u_high.rstrip('s') else f'{low}–{high}'


def localize_text(text, system=DEFAULT):
    """Free text with its measures in the reader's system: "Sett ovnen på 200 °C" -> "Sett ovnen på 400 °F",
    "biter på 3 cm" -> "biter på 1¼ in", "2 dl" -> "¾ cup". Metric leaves the text as written, except °F, which
    becomes °C. Placeholders ({i3}) are left alone: their amounts come from fmt_amount."""
    if not text:
        return text
    text = TEMP.sub(lambda m: _temps(m, system), text)
    if system != 'us':
        return text
    text = LENGTH.sub(_lengths, text)
    return AMOUNT.sub(_amounts, text)


def unconverted(text):
    """The measures in free text that localize_text cannot convert: US units ("2 cups", "350°F", '9"') and degrees
    with no scale ("200°"). The text should be metric (the structuring prompt)."""
    return [m.group(0).strip() for m in US_TEXT.finditer(text or '')]
