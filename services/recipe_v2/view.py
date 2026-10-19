"""What the recipe page shows for a v2 recipe (schema_version 2).

Built from the stored graph, the planner and the shopping list. The page is
the overview and the step list from the phone prototype (docs/prototypes/
telefon.html, RECIPE_VISUALIZATIONS.md 9.15). Text is English, the app's first
language; unit, equipment and mode names come from data/constraints.
"""
import json
import os
import re
from functools import lru_cache

from markupsafe import Markup, escape

from database.models import Ingredient, db
from services.recipe_v2.planner import MODES, plan_v2
from services.recipe_v2.read import shopping_list
from services.recipe_v2.store import to_v2

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PLACEHOLDER = re.compile(r'\{(i\d+)\}')
PLAN_NAMES = {'calm': 'Calm', 'prep': 'Prep first', 'jit': 'Just in time'}
PLAN_HINTS = {
    'calm': 'Prep before cooking, but what can wait is done while something stands.',
    'prep': 'Everything that needs no heat is done before the first cook step.',
    'jit': 'Every step as late as possible. Shortest, busiest.',
}
# English plurals for the countable units (units.json has Norwegian plurals only).
UNIT_PLURALS = {'clove': 'cloves', 'pinch': 'pinches', 'can': 'cans', 'handful': 'handfuls', 'slice': 'slices',
                'sprig': 'sprigs', 'leaf': 'leaves', 'bunch': 'bunches', 'package': 'packages', 'cup': 'cups',
                'stalk': 'stalks', 'sheet': 'sheets', 'dash': 'dashes', 'drop': 'drops'}


@lru_cache(maxsize=1)
def _catalogs():
    def load(name):
        with open(os.path.join(ROOT, 'data', 'constraints', name), encoding='utf-8') as f:
            return json.load(f)

    eq = load('equipment.json')
    return {
        'units': {u['id']: u for u in load('units.json')['units']},
        'equipment': {e['id']: e.get('name_en') or e['name'] for e in eq['equipment']},
        'modes': {m['id']: m.get('name_en') or m['name'] for m in eq['modes']},
    }


def frac(v):
    """1.5 -> "1½", 0.25 -> "¼". Kitchen amounts to the nearest quarter or third."""
    whole = int(v + 1e-9)
    rem = v - whole
    marks = [(0, ''), (0.25, '¼'), (1 / 3, '⅓'), (0.5, '½'), (2 / 3, '⅔'), (0.75, '¾'), (1, '')]
    best = min(marks, key=lambda m: abs(rem - m[0]))
    if best[0] == 1:
        whole, best = whole + 1, (0, '')
    return (str(whole) if whole else '') + best[1] or '0'


def fmt_amount(amount, unit):
    """"400 g", "1½ tbsp", "2 cloves", "3" (pieces have no unit)."""
    if amount is None:
        return ''
    if unit in ('g', 'ml'):
        n = round(amount / 10) * 10 if amount >= 100 else round(amount / 5) * 5 if amount >= 10 else round(amount, 1)
        return f'{n:g} {unit}'
    n = frac(amount)
    if not unit or unit == 'piece':
        return n
    name = (_catalogs()['units'].get(unit) or {}).get('name_en') or unit
    return f'{n} {UNIT_PLURALS.get(unit, name) if amount > 1 else name}'


def duration(minutes):
    return f'{minutes / 60:.1f} h'.replace('.0 h', ' h') if minutes >= 120 else f'{minutes} min'


def step_duration(s):
    parts = []
    if s.get('active_minutes'):
        parts.append(f"{s['active_minutes']} min")
    if s.get('passive_minutes'):
        parts.append(('+ ' if parts else '') + f"{duration(s['passive_minutes'])} standing")
    return ' '.join(parts)


def equipment_text(s):
    cat = _catalogs()
    q = (s.get('equipment') or [None])[0]
    if not q:
        return ''
    bits = [cat['equipment'].get(q, q)]
    if s.get('temp_c'):
        bits.append(f"{s['temp_c']} °C")
    if s.get('mode'):
        bits.append(cat['modes'].get(s['mode'], s['mode']))
    return ', '.join(bits)


def symbol(ingredient, name, size):
    """The pantry symbol, or the first letter when the ingredient has no image or is not in the pantry."""
    if ingredient is not None and ingredient.image_url:
        return Markup('<span class="sym" style="--s:{s}px"><img src="{u}" alt="" width="{s}" height="{s}" loading="lazy"></span>').format(
            s=size, u=ingredient.image_url)
    return Markup('<span class="sym sym-letter" style="--s:{s}px" aria-hidden="true">{c}</span>').format(s=size, c=(name or '?')[:1].upper())


def step_html(s, lines, ingredients, factor):
    """Step text with each {iN} as a pill: symbol, amount and name. In cook and serve steps the prep style follows in brackets."""
    def pill(m):
        line = lines.get(m.group(1))
        if not line:
            return escape(m.group(0))
        amount = fmt_amount(line['amount'] * factor if line.get('amount') is not None else None, line.get('unit'))
        label = f"{amount} {line['name']}".strip()
        out = Markup('<span class="pill">{sym}{label}</span>').format(sym=symbol(ingredients.get(m.group(1)), line['name'], 20), label=label)
        if s['phase'] != 'prep' and line.get('prep_style'):
            out += Markup(' <span class="prep">({})</span>').format(line['prep_style'])
        return out

    text = str(escape(s.get('text') or ''))
    return Markup(PLACEHOLDER.sub(lambda m: str(pill(m)), text))


def build(recipe, servings=None, plan='calm'):
    """Everything the v2 recipe template needs."""
    v2 = to_v2(recipe)
    plan = plan if plan in MODES else 'calm'
    base = recipe.base_servings or 4
    scalable = not recipe.yield_text
    servings = max(1, min(24, servings or base)) if scalable else base
    factor = servings / base
    # A draft that is still invalid has no steps; it shows its errors instead.
    sch = plan_v2(v2, plan) if v2['steps'] else {'order': [], 'plan': {}, 'T': 0, 'A': 0}

    by_line = {line.local_id: line for line in recipe.lines}
    ingredients = {lid: line.ingredient for lid, line in by_line.items()}
    lines = {i['local_id']: i for i in v2['ingredients']}
    comps = {c['local_id']: c['name'] for c in v2['components']}
    steps_by = {s['local_id']: s for s in v2['steps']}

    pantry = {}
    ids = [e['pantry_id'] for e in shopping_list(v2) if e.get('pantry_id')]
    if ids:
        pantry = {i.food_id: i for i in db.session.execute(db.select(Ingredient).where(Ingredient.food_id.in_(ids))).scalars()}

    shop = []
    for e in shopping_list(v2, factor):
        notes = []
        if len(e['parts']) > 1:
            notes.append(' and '.join(e['parts']))
        elif e['uses'] > 1:
            notes.append(f"used {e['uses']} times")
        if e['to_taste'] and not e['amounts']:
            notes.append('to taste')
        shop.append({'name': e['name'], 'amount': ' + '.join(fmt_amount(a['amount'], a['unit']) for a in e['amounts']),
                     'note': ' · '.join(notes), 'symbol': symbol(pantry.get(e.get('pantry_id')), e['name'], 36),
                     'missing': not e.get('pantry_id') or e['pantry_id'] not in pantry})

    steps = []
    for n, sid in enumerate(sch['order'], 1):
        s = steps_by[sid]
        p = sch['plan'][sid]
        during = steps_by.get(p.get('during')) if p.get('during') else None
        steps.append({
            'n': n, 'id': sid, 'phase': s['phase'], 'short': s['short'], 'component': comps.get(s['component_id'], ''),
            'duration': step_duration(s), 'equipment': equipment_text(s), 'start': p['start'],
            'while': f"While: {during['short'].lower()}" if during else '',
            'html': step_html(s, lines, ingredients, factor), 'done_when': s.get('done_when'),
        })

    first_use = {}
    for sid in sch['order']:
        for q in steps_by[sid].get('equipment') or []:
            first_use.setdefault(q, len(first_use))
    cat = _catalogs()
    return {
        'title': recipe.title, 'servings': servings, 'scalable': scalable, 'yield_text': recipe.yield_text,
        'total': duration(sch['T']), 'active': duration(sch['A']), 'plan': plan, 'plans': PLAN_NAMES,
        'plan_hint': PLAN_HINTS[plan], 'parts': [c['name'] for c in v2['components']],
        'shopping': shop, 'equipment': [cat['equipment'].get(q, q) for q in first_use], 'steps': steps,
        'chef_note': recipe.chef_note, 'missing': sum(1 for s in shop if s['missing']),
        'errors': recipe.validation_errors or [],
    }
