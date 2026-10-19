"""Deterministic validator for recipe model v2 (docs/RECIPE_MODEL_V2.md, section 5).

Rules 1-8 from the decision note. Rule 9 (mise elements) belongs to phase 3 and
is not checked here. The reference implementation is `validate()` in
docs/prototypes/fem-retter.html.

Errors are returned as dicts with the rule number, so the pilot can count which
rules fail most often, and with an English message that is sent back to Gemini
on retry.
"""
import json
import os
import re
from functools import lru_cache

CONSTRAINTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'constraints')

PHASES = ('prep', 'cook', 'serve')
ID_PATTERNS = {'component': r'c\d+', 'ingredient': r'i\d+', 'step': r's\d+'}
PLACEHOLDER = re.compile(r'\{([^{}]*)\}')
TO_TASTE = re.compile(r'etter smak|to taste|as needed|etter behov', re.IGNORECASE)
# "spe med melk mens du visper" is technique inside one step and allowed.
# {iN} is always the total amount, so "{i4} på hver burger" is wrong (warning each_total).
EACH = re.compile(r'\{i\d+\}[^.{}]{0,40}\b(each|apiece|hver|hvert|på hver|i hver)\b'
                  r'|\b(each|hver|på hver|i hver)\b[^.{}]{0,20}\{i\d+\}', re.IGNORECASE)
# Equipment that must be heated before food goes in (warning no_preheat).
PREHEATED = ('oven', 'airfryer')
TIME_WORDS = re.compile(r'\bi mellomtiden\b|\bmeanwhile\b|\bin the meantime\b|\bwhile the\b|\bmens (?!du\b)', re.IGNORECASE)

RULES = {
    1: 'Alle local_id er unike innenfor sin type',
    2: 'Alle referanser finnes',
    3: 'Hver {iN} i teksten står i stegets uses',
    4: 'Hver ingredienslinje brukes av nøyaktig ett steg',
    5: 'Ingen sykler, nøyaktig ett sluttsteg',
    6: 'Steg med varmemetode har phase = cook',
    7: 'equipment, method og unit finnes i katalogene',
    8: 'amount > 0, eller null med «etter smak»',
}


def _load(name):
    with open(os.path.join(CONSTRAINTS_DIR, name), encoding='utf-8') as f:
        return json.load(f)


@lru_cache(maxsize=1)
def load_catalogs():
    eq = _load('equipment.json')
    methods = _load('methods.json')['methods']
    units = _load('units.json')['units']
    return {
        'equipment': {e['id'] for e in eq['equipment']},
        'modes': {m['id'] for m in eq['modes']},
        'methods': {m['id'] for m in methods},
        'heat_methods': {m['id'] for m in methods if m['heat']},
        'units': {u['id'] for u in units},
    }


def is_to_taste(line):
    return bool(TO_TASTE.search(line.get('prep_style') or '') or TO_TASTE.search(line.get('name') or ''))


def is_equipment_only(step):
    """Steps that only prepare equipment (preheat the oven, line the tin) hang outside the graph.

    Ventetid på dem utledes fra setup-steg på samme kokekar, så de er ikke sluttsteg.
    """
    if step.get('uses') or step.get('after'):
        return False
    return True


def validate_recipe_v2(recipe, catalogs=None):
    cat = catalogs or load_catalogs()
    errors, warnings = [], []

    def err(rule, msg):
        errors.append({'rule': rule, 'message': msg})

    def warn(code, msg):
        warnings.append({'code': code, 'message': msg})

    comps = recipe.get('components') or []
    ings = recipe.get('ingredients') or []
    steps = recipe.get('steps') or []
    if not steps:
        err(5, 'The recipe has no steps.')
    if not comps:
        err(2, 'The recipe has no components.')

    # Rule 1: unique local_id within each type
    for kind, items in (('component', comps), ('ingredient', ings), ('step', steps)):
        seen = set()
        for x in items:
            lid = x.get('local_id')
            if not lid or not re.fullmatch(ID_PATTERNS[kind], str(lid)):
                err(1, f'{kind} local_id {lid!r} must look like {ID_PATTERNS[kind][0]}1, {ID_PATTERNS[kind][0]}2, ...')
            elif lid in seen:
                err(1, f'{kind} local_id {lid} is used more than once.')
            seen.add(lid)

    comp_ids = {c.get('local_id') for c in comps}
    ing_by = {i.get('local_id'): i for i in ings}
    step_by = {s.get('local_id'): s for s in steps}

    # Rule 2: references exist
    for i in ings:
        if i.get('component_id') not in comp_ids:
            err(2, f"{i.get('local_id')}.component_id {i.get('component_id')!r} is not a component.")
    for s in steps:
        sid = s.get('local_id')
        if s.get('component_id') not in comp_ids:
            err(2, f"{sid}.component_id {s.get('component_id')!r} is not a component.")
        for u in s.get('uses') or []:
            if u not in ing_by:
                err(2, f'{sid}.uses references {u}, which is not an ingredient line.')
        for a in s.get('after') or []:
            if a not in step_by:
                err(2, f'{sid}.after references {a}, which is not a step.')
        for ph in PLACEHOLDER.findall(s.get('text') or ''):
            if re.fullmatch(r'i\d+', ph):
                if ph not in ing_by:
                    err(2, f'{sid}.text contains {{{ph}}}, which is not an ingredient line.')
            else:
                err(2, f'{sid}.text contains {{{ph}}}. Only ingredient placeholders like {{i3}} are allowed; '
                       f'refer to earlier results in plain words ("the sauce").')

    # Rule 3: every {iN} in the text is in the step's uses
    for s in steps:
        uses = set(s.get('uses') or [])
        for ph in PLACEHOLDER.findall(s.get('text') or ''):
            if ph in ing_by and ph not in uses:
                owner = next((o.get('local_id') for o in steps if ph in (o.get('uses') or [])), None)
                hint = f' It is in the uses of {owner}; refer to it in plain words here instead.' if owner else ''
                err(3, f"{s.get('local_id')}.text mentions {{{ph}}} but {ph} is not in {s.get('local_id')}.uses.{hint}")
        mentioned = set(PLACEHOLDER.findall(s.get('text') or ''))
        for u in uses - mentioned:
            if u in ing_by:
                warn('uses_not_in_text', f"{s.get('local_id')} uses {u} but the text does not mention {{{u}}}.")

    # Rule 4: every ingredient line is used by exactly one step
    users = {}
    for s in steps:
        for u in s.get('uses') or []:
            users.setdefault(u, []).append(s.get('local_id'))
    for i in ings:
        lid = i.get('local_id')
        n = users.get(lid, [])
        if not n:
            err(4, f'{lid} ({i.get("name")}) is not used by any step.')
        elif len(n) > 1:
            err(4, f'{lid} ({i.get("name")}) is used by {len(n)} steps ({", ".join(n)}). '
                   f'Split it into one ingredient line per step, each with its own amount.')

    # Rule 5: no cycles, exactly one final step
    color = {}
    cycle = []

    def visit(sid, path):
        color[sid] = 1
        for a in step_by.get(sid, {}).get('after') or []:
            if a not in step_by:
                continue
            if color.get(a) == 1:
                cycle.append(path[path.index(a):] + [a] if a in path else [sid, a])
                continue
            if not color.get(a):
                visit(a, path + [a])
        color[sid] = 2

    for sid in step_by:
        if not color.get(sid):
            visit(sid, [sid])
    for c in cycle[:3]:
        err(5, f'Cycle in after: {" -> ".join(c)}.')
    referenced = {a for s in steps for a in (s.get('after') or [])}
    graph_steps = [s for s in steps if not is_equipment_only(s) and not (s.get('setup') and not s.get('uses'))]
    sinks = [s.get('local_id') for s in graph_steps if s.get('local_id') not in referenced]
    if len(sinks) != 1 and steps:
        if not sinks:
            err(5, 'There is no final step (every step is referenced by another).')
        else:
            err(5, f'Expected exactly one final step, found {len(sinks)}: {", ".join(sinks)}. '
                   f'Every step except pure equipment steps (preheat, line the tin) must lead to the final '
                   f'serving step through after.')

    # Rule 6: heat methods are cook
    for s in steps:
        sid, ph, m = s.get('local_id'), s.get('phase'), s.get('method')
        if ph not in PHASES:
            err(6, f'{sid}.phase is {ph!r}, must be one of prep, cook, serve.')
        elif m in cat['heat_methods'] and ph != 'cook':
            err(6, f'{sid} uses heat method {m!r} so phase must be cook, not {ph}.')

    # Rule 7: catalogs
    for s in steps:
        sid = s.get('local_id')
        if s.get('method') not in cat['methods']:
            err(7, f'{sid}.method {s.get("method")!r} is not in the method catalog.')
        for e in s.get('equipment') or []:
            if e not in cat['equipment']:
                err(7, f'{sid}.equipment {e!r} is not in the equipment catalog.')
        if s.get('mode') and s.get('mode') not in cat['modes']:
            err(7, f'{sid}.mode {s.get("mode")!r} is not a valid mode.')
    for i in ings:
        u = i.get('unit')
        if i.get('amount') is not None:
            if not u:
                err(7, f'{i.get("local_id")} has an amount but no unit. Use "piece" for countable items.')
            elif u not in cat['units']:
                err(7, f'{i.get("local_id")}.unit {u!r} is not in the unit catalog.')
        elif u and u not in cat['units']:
            err(7, f'{i.get("local_id")}.unit {u!r} is not in the unit catalog.')

    # Rule 8: amount > 0, or null with "etter smak"
    for i in ings:
        a = i.get('amount')
        if a is None:
            if not is_to_taste(i):
                err(8, f'{i.get("local_id")} ({i.get("name")}) has no amount. Only "etter smak"/"to taste" lines '
                       f'may omit amount, and then prep_style must say so.')
        elif not isinstance(a, (int, float)) or a <= 0:
            err(8, f'{i.get("local_id")}.amount is {a!r}, must be greater than 0.')

    # Warnings (stored, flagged, not rejected)
    for s in steps:
        sid = s.get('local_id')
        if EACH.search(s.get('text') or ''):
            warn('each_total', f'{sid}.text puts "each"/"hver" next to an amount, but {{iN}} is the total. '
                               f'Write "divide {{i4}} between the burgers" instead.')
        if TIME_WORDS.search(s.get('text') or ''):
            warn('time_words', f'{sid}.text contains time words ("mens", "meanwhile"). Say what to do, not when.')
        if (s.get('active_minutes') or 0) + (s.get('passive_minutes') or 0) <= 0:
            warn('zero_time', f'{sid} has no active or passive time.')
        eq0 = (s.get('equipment') or [None])[0]
        if eq0 in PREHEATED and s.get('temp_c') and not s.get('setup') and not any(
                o.get('setup') and (o.get('equipment') or [None])[0] == eq0 and o.get('temp_c') == s.get('temp_c')
                for o in steps):
            warn('no_preheat', f'{sid} uses the {eq0} at {s.get("temp_c")} °C, but no setup step heats the {eq0} '
                               f'to {s.get("temp_c")} °C.')
        if s.get('method') in cat['heat_methods'] and not s.get('equipment'):
            warn('heat_without_equipment', f'{sid} uses heat but has no equipment.')
        if len((s.get('short') or '').split()) > 5:
            warn('long_short', f'{sid}.short has more than 5 words.')

    return {
        'valid': not errors,
        'errors': errors,
        'warnings': warnings,
        'failed_rules': sorted({e['rule'] for e in errors}),
    }


def format_errors_for_retry(result):
    lines = [f"- [rule {e['rule']}] {e['message']}" for e in result['errors']]
    return '\n'.join(lines)
