"""What the recipe page shows for a v2 recipe (schema_version 2).

Built from the stored graph, the planner and the shopping list. The page is
the overview and the step list from the phone prototype (docs/prototypes/
telefon.html, RECIPE_VISUALIZATIONS.md 9.15). Text is English, the app's first
language; unit, equipment and mode names come from data/constraints.
"""
import json
import os
import re
import time
from collections import OrderedDict
from functools import lru_cache

from markupsafe import Markup, escape

from database.models import Ingredient, Recipe, RecipeLine, RecipeStep, db
from services.recipe_v2 import delta, groups, mise, nutrition, states, whole
from services.recipe_v2.derive import HEAT_LABELS, heat_steps
from services.recipe_v2.persona import SETTINGS, age_label
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
        'equipment_items': {e['id']: e for e in eq['equipment']},
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


def unit_names():
    """{unit: [one, more]} as fmt_amount writes them, for static/js/servings.js."""
    names = {}
    for unit, u in _catalogs()['units'].items():
        one = u.get('name_en') or unit
        names[unit] = [one, UNIT_PLURALS.get(unit, one)]
    return names


def duration(minutes):
    return f'{minutes / 60:.1f} h'.replace('.0 h', ' h') if minutes >= 120 else f'{minutes} min'


def step_duration(s):
    parts = []
    if s.get('active_minutes'):
        parts.append(f"{s['active_minutes']} min")
    if s.get('passive_minutes'):
        parts.append(('+ ' if parts else '') + f"{duration(s['passive_minutes'])} standing")
    return ' '.join(parts)


def count_of(line, factor=1.0):
    """How many, for a line counted in pieces or cloves (3 cloves of garlic): a whole number from 1 to 12, else None.
    Prep shows it on the image, so the amount reads at a glance."""
    if line.get('unit') not in ('piece', 'clove') or line.get('amount') is None:
        return None
    n = line['amount'] * factor
    return int(round(n)) if abs(n - round(n)) < 0.01 and 1 <= round(n) <= 12 else None


def equipment_list(ids, cat=None):
    """The equipment the dish needs, in the order it is first used, as {id, name, image, special}: supplies
    (foil, plates) left out, and an item shown as another (same_as) listed once, as that one."""
    items = (cat or _catalogs())['equipment_items']
    out = {}
    for q in ids:
        e = items.get(q) or {'id': q, 'name': q}
        if e.get('kind') == 'supply':
            continue
        e = items.get(e.get('same_as')) or e
        out.setdefault(e['id'], {'id': e['id'], 'name': e.get('name_en') or e['name'], 'image': e.get('image'),
                                 'images': e.get('image_variants') or {}, 'special': e.get('level') == 'special'})
    return list(out.values())


def time_strip(steps, total):
    """The time from start to table in parts, for the strip on the overview of the one-page flow: getting ready until
    the heat goes on (see heat_on), cooking, and serving. Each part as {phase, label, minutes, text}; parts of no
    length are left out, so a dish that is never heated is one part."""
    marks = [('prep', 'Prep', 0)]
    heat = next((x['start'] for x in steps if x['heat']), None)
    serve = next((x['start'] for x in steps if x['phase'] == 'serve'), None)
    if heat is not None:
        marks.append(('cook', 'Cook', heat))
    if serve is not None and serve >= marks[-1][2]:
        marks.append(('serve', 'Serve', serve))
    parts = []
    for (phase, label, start), end in zip(marks, [m[2] for m in marks[1:]] + [total]):
        if end > start:
            parts.append({'phase': phase, 'label': label, 'minutes': end - start, 'text': duration(end - start)})
    return parts


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


def line_state(line, lang='en'):
    """What the cook has done to a line, in words, with its note: "finely chopped, for garnish"."""
    return ', '.join(x for x in (states.word(line.get('state') or line.get('cut'), line.get('grade'), lang), line.get('prep_style')) if x)


def step_html(s, lines, ingredients, factor, lang='en'):
    """Step text with each {iN} as a pill: symbol, amount and name. In cook and serve steps the state and note follow in brackets."""
    def pill(m):
        line = lines.get(m.group(1))
        if not line:
            return escape(m.group(0))
        amount = fmt_amount(line['amount'] * factor if line.get('amount') is not None else None, line.get('unit'))
        label = f"{amount} {line['name']}".strip()
        out = Markup('<span class="pill">{sym}{label}</span>').format(sym=symbol(ingredients.get(m.group(1)), line['name'], 24), label=label)
        said = line_state(line, lang) if s['phase'] != 'prep' else ''
        if said:
            out += Markup(' <span class="prep">({})</span>').format(said)
        return out

    text = str(escape(s.get('text') or ''))
    return Markup(PLACEHOLDER.sub(lambda m: str(pill(m)), text))


# The pages of a recipe (Overview, Prep, Cook, print) show the same built recipe: build it once and keep it
# for a while. The key holds every column of the recipe row (revision, status, images, nutrition, notes, …), so a
# change to the recipe makes a new entry; changes elsewhere (a new pantry symbol) show within CACHE_SECONDS.
CACHE_SIZE, CACHE_SECONDS = 128, 600
_cache = OrderedDict()


def clear_cache():
    _cache.clear()


def page(recipe, servings=None, plan='calm'):
    """build() for the recipe pages, from the cache when the recipe has not changed."""
    key = (recipe.id, repr(tuple(getattr(recipe, c.key) for c in Recipe.__table__.columns)), servings, plan)
    hit = _cache.get(key)
    if hit and time.monotonic() - hit[0] < CACHE_SECONDS:
        _cache.move_to_end(key)
        return hit[1]
    load_graph(recipe)
    view = build(recipe, servings=servings, plan=plan)
    _cache[key] = (time.monotonic(), view)
    while len(_cache) > CACHE_SIZE:
        _cache.popitem(last=False)
    return view


def load_graph(recipe):
    """Load the recipe's components, lines (with their pantry ingredient) and steps (with their lines and inputs)
    in a few queries, instead of one per step and per line when build() walks them."""
    from sqlalchemy.orm import selectinload

    db.session.execute(db.select(Recipe).where(Recipe.id == recipe.id).options(
        selectinload(Recipe.components),
        selectinload(Recipe.lines).selectinload(RecipeLine.ingredient),
        selectinload(Recipe.steps).selectinload(RecipeStep.lines),
        selectinload(Recipe.steps).selectinload(RecipeStep.after),
        selectinload(Recipe.meal_types),
    )).scalars().all()


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
        notes = list(e['varieties'])  # the kind to buy first: "poteter · melne"
        if len(e['parts']) > 1:
            notes.append(' and '.join(e['parts']))
        elif e['uses'] > 1:
            notes.append(f"used {e['uses']} times")
        if e['to_taste'] and not e['amounts']:
            notes.append('to taste')
        found = pantry.get(e.get('pantry_id'))
        group = groups.group_of(found, mise.staple({'name': e['name'], **({'pantry_tier': found.tier} if found else {})}))
        shop.append({'name': e['name'], 'amount': ' + '.join(fmt_amount(a['amount'], a['unit']) for a in e['amounts']),
                     # the amounts for these servings, so the page can scale them at once (static/js/servings.js)
                     'raw': [[round(a['amount'], 4), a['unit']] for a in e['amounts']],
                     'note': ' · '.join(notes), 'symbol': symbol(found, e['name'], 36 if group == 'staples' else 56),
                     'missing': not e.get('pantry_id') or e['pantry_id'] not in pantry, 'group': group,
                     'img': found.image_url if found is not None else None})

    heated = {x['local_id'] for x in heat_steps(v2)}
    steps = []
    for n, sid in enumerate(sch['order'], 1):
        s = steps_by[sid]
        p = sch['plan'][sid]
        during = steps_by.get(p.get('during')) if p.get('during') else None
        steps.append({
            'n': n, 'id': sid, 'phase': s['phase'], 'short': s['short'], 'component': comps.get(s['component_id'], ''),
            'duration': step_duration(s), 'equipment': equipment_text(s), 'start': p['start'],
            'while': f"While: {during['short'].lower()}" if during else '',
            'html': step_html(s, lines, ingredients, factor, recipe.language), 'done_when': s.get('done_when'),
            'setup': bool(s.get('setup')), 'heat': sid in heated,
        })
    # Where the heat goes on, for the step list of the one-page flow: the first step that heats the food (not
    # preheating the oven or bringing water to the boil), and the time from there to the table
    heat_on = next(({'id': x['id'], 'left': duration(sch['T'] - x['start'])} for x in steps if x['heat']), None)

    for i in v2['ingredients']:
        if ingredients.get(i['local_id']) is not None:
            i['pantry_name'] = ingredients[i['local_id']].name
            i['pantry_tier'] = ingredients[i['local_id']].tier
    # A line's state, from its prep step when the line has none of its own (a recipe made before the state catalog:
    # "Cut the ham" with method slice): the state then shows on Prep, in Cook and in the delta all the same
    state_from_step = {}
    for st in v2['steps']:
        if st.get('phase') == 'prep' and states.state_of_method(st.get('method')):
            for u in st.get('uses') or []:
                state_from_step.setdefault(u, states.state_of_method(st['method']))
    lang = recipe.language or 'en'

    def state_of(lid, i):
        return i.get('state') or i.get('cut') or state_from_step.get(lid)
    # The river delta: every line as the drawing shows it, with the amount for these servings
    pictured = {lid: {'name': i['name'], 'img': (ingredients.get(lid).image_url if ingredients.get(lid) is not None else None),
                      'amount': fmt_amount(i['amount'] * factor, i.get('unit')) if i.get('amount') is not None else '',
                      'prep': i.get('prep_style') or '', 'cut': state_of(lid, i), 'count': count_of(i, factor),
                      'state': line_state({**i, 'state': state_of(lid, i)}, lang),
                      # the state alone in words, for its sign in the delta (the note may say something else: "melne")
                      'cut_word': states.word(state_of(lid, i), i.get('grade'), lang),
                      'group': groups.group_of(ingredients.get(lid), mise.staple(i))} for lid, i in lines.items()}

    # Prep: the lines in bowls, and the rest to take out, drawn like in the delta
    ready = mise.build(v2, sch, recipe.language) if v2['steps'] else None
    if ready:
        def tile(i):
            return {**pictured[i['local_id']], 'mark': states.mark(pictured[i['local_id']]['cut'])}
        for b in ready['bowls'] + [b for g in ready['later'] for b in g['bowls']]:
            b['lines'] = [tile(i) for i in b['lines']]
        for f in ready['fetch'] + ready['bench'] + [f for g in ready['later'] for f in g['fetch']]:
            f['line'] = tile(f['line'])
        ready['takeout'] = take_out(ready['fetch'] + ready['bench'])

    if ready:
        cook_needs(steps, steps_by, ready, sch, {lid: tile(i) for lid, i in lines.items()})

    first_use = {}
    for sid in sch['order']:
        for q in steps_by[sid].get('equipment') or []:
            first_use.setdefault(q, len(first_use))
    cat = _catalogs()
    return {
        'title': recipe.title, 'servings': servings, 'scalable': scalable, 'yield_text': recipe.yield_text,
        'unit_names': unit_names(),
        'total': duration(sch['T']), 'total_min': sch['T'], 'active': duration(sch['A']), 'plan': plan, 'plans': PLAN_NAMES,
        'plan_hint': PLAN_HINTS[plan], 'parts': [c['name'] for c in v2['components']],
        'shopping': shop, 'shop_groups': groups.grouped(shop), 'equipment': equipment_list(first_use, cat), 'steps': steps,
        'heat_on': heat_on, 'time_strip': time_strip(steps, sch['T']),
        'chef_note': recipe.chef_note, 'missing': sum(1 for s in shop if s['missing']),
        'errors': [e for e in recipe.validation_errors or [] if e.get('rule') not in ('persona', 'image')],
        'image_notes': [e['message'] for e in recipe.validation_errors or [] if e.get('rule') == 'image'],
        'persona_notes': [e['message'] for e in recipe.validation_errors or [] if e.get('rule') == 'persona'],
        'about': about(recipe),
        'delta': delta.build(v2, sch['order'], pictured),
        # The whole dish beside cooking mode (services/recipe_v2/whole.py)
        'timeline': whole.timeline(v2, sch, comps) if v2['steps'] else None,
        'metro': whole.metro(v2, sch, comps) if v2['steps'] else None,
        # The one-page flow's map: a transit map with time down the page
        'metro_map': whole.metro_map(v2, sch, comps) if v2['steps'] else None,
        'ready': ready,
        'nutrition': nutrition.per_serving(recipe),
        # Why there is no nutrition, for the admin: lines without grams, and lines without pantry nutrition
        'nutrition_gap': None if recipe.total_calories is not None else nutrition.compute(recipe.lines),
    }


def take_out(loose):
    """Prep's one list of what is not in a bowl: what to take out and what stays on the counter, in kitchen groups.

    An ingredient used in several steps is one tile, with its amounts and steps; the staples are one row
    of names, since you have them and the steps give the amounts (RECIPE_VISUALIZATIONS.md 9.16)."""
    items = {}
    for f in loose:
        line = f['line']
        item = items.setdefault(line['name'].strip().lower(), {'key': f['key'], 'line': line, 'group': line['group'],
                                                               'amounts': [], 'steps': []})
        amount = line['amount'] or 'to taste'
        if amount not in item['amounts']:
            item['amounts'].append(amount)
        if f['used']['no'] not in item['steps']:
            item['steps'].append(f['used']['no'])
    for item in items.values():
        item['amount'] = ' + '.join(item['amounts'])
        item['steps'].sort()
    return groups.grouped(items.values())


def cook_needs(steps, steps_by, ready, sch, tiles):
    """What cooking mode needs per step: the bowls and lines from Prep that go in here, the results of
    earlier steps, the step standing while this one is done, and whether Prep already did it."""
    plan, number = sch['plan'], {s['id']: s['n'] for s in steps}
    done_here = set(ready['done_here'])
    bowls = ready['bowls'] + [b for g in ready['later'] for b in g['bowls']]
    loose = ready['fetch'] + ready['bench'] + [f for g in ready['later'] for f in g['fetch']]
    for s in steps:
        raw = steps_by[s['id']]
        here_bowls = [b for b in bowls if b['used']['id'] == s['id']]
        here_tiles = [f['line'] for f in loose if f['used']['id'] == s['id']]
        # A prep step that is part of a bowl, cooked here instead of in Prep: its own lines
        if s['id'] in done_here:
            here_tiles += [tiles[u] for u in raw.get('uses') or [] if u in tiles]
        after = [a for a in raw.get('after') or [] if a in steps_by]
        results = [{'no': number[a], 'short': steps_by[a]['short'], 'ready': a in done_here} for a in after
                   if steps_by[a].get('uses') or not steps_by[a].get('setup')]
        start = plan[s['id']]['start']
        standing = [x for x in steps if x['id'] != s['id'] and (steps_by[x['id']].get('passive_minutes') or 0) >= 3
                    and plan[x['id']]['a_end'] <= start < plan[x['id']]['end']]
        standing.sort(key=lambda x: -plan[x['id']]['a_end'])
        s.update({
            'bowls': here_bowls, 'tiles': here_tiles, 'results': [r for r in results if not r['ready']],
            'after': after, 'ahead': s['id'] in done_here, 'standing': standing[0] if standing else None,
            'active_min': raw.get('active_minutes') or 0, 'passive_min': raw.get('passive_minutes') or 0,
            # Jobs Prep lists first ("take the butter out") are not cooking steps
            'task': not raw.get('uses') and not raw.get('after') and not raw.get('equipment'),
        })


SPICE = ('Mild', 'A little hot', 'Hot', 'Very hot')


def about(recipe):
    """Short facts about the dish for the overview: (label, value), only those that are set. Difficulty is
    left to the template, which has the reader-facing names."""
    leftovers = None
    if recipe.keeps_days is not None:
        leftovers = 'Eat at once' if recipe.keeps_days == 0 else f'{recipe.keeps_days} day{"s" if recipe.keeps_days > 1 else ""} in the fridge'
        if recipe.freezes:
            leftovers += ', freezes'
    facts = [('Cuisine', recipe.cuisine), ('Cooked in', HEAT_LABELS.get(recipe.heat_source)),
             ('Spice', SPICE[recipe.spice_level] if recipe.spice_level in range(4) else None),
             ('Leftovers', leftovers), ('Protein', recipe.protein_type),
             ('Made as', ' · '.join(age_label(recipe) if k == 'baby' else SETTINGS[k][0]
                                    for k in recipe.settings or [] if k in SETTINGS))]
    return [(k, v) for k, v in facts if v]


def as_text(recipe):
    """The saved recipe as plain text, in the shape round 1 writes: title, servings, ingredients per part and
    numbered steps in the planned order. Used to make a version of it (services/recipe_v2/generate.py)."""
    return v2_text(to_v2(recipe), recipe.yield_text, recipe.chef_note)


def v2_text(v2, yield_text=None, chef_note=None):
    """as_text for a recipe in v2 JSON that is not saved, such as the fasit recipes."""
    lines = {i['local_id']: i for i in v2['ingredients']}

    def line_text(i, prep=True):
        amount = fmt_amount(i.get('amount'), i.get('unit'))
        text = ' '.join(x for x in (amount, i['name']) if x) + (f" ({i['variety']})" if i.get('variety') else '')
        said = line_state(i) if prep else ''
        return text + (f', {said}' if said else '')

    out = [v2['title'], '', f"Servings: {yield_text or v2['servings']}", '', 'Ingredients']
    for c in v2['components']:
        part = [i for i in v2['ingredients'] if i['component_id'] == c['local_id']]
        if part:
            out += ([c['name']] if len(v2['components']) > 1 else []) + [f'- {line_text(i)}' for i in part]
    out += ['', 'Method']
    order = plan_v2(v2)['order']
    by = {s['local_id']: s for s in v2['steps']}
    for n, sid in enumerate(order, 1):
        text = PLACEHOLDER.sub(lambda m: line_text(lines[m.group(1)], prep=False) if m.group(1) in lines else m.group(0),
                               by[sid]['text'])
        out.append(f'{n}. {text}')
    chef_note = chef_note or v2.get('chef_note')
    if chef_note:
        out += ['', f'Tip: {chef_note}']
    return '\n'.join(out)
