"""Fill the pantry for a made recipe: the lines the matcher could not link (services/recipe_service.py).

Recipes choose from the pantry first, and only Pål lets new items in. One Claude call sees those lines, the recipe and
the whole pantry, and decides for each line, in this dish:

- alias: the same food under another name ("scallion" is spring onion). The name becomes an alias of that item, so
  the next recipe with it is linked by the matcher straight away. It holds for every recipe, so never a swap.
- substitute: another pantry item does the job so well that swapping hardly matters here ("yogurt butter" to butter in
  a sauce). This recipe's lines and text change, in this recipe only: the same swap can ruin another dish. Noted with
  rule SWAP, which does not flag the recipe; recipe.source_text keeps what the source said.
- ask: the line matters to the dish and nothing in the pantry does its job. A pending item is made with its nutrition,
  the lines are linked to it, and Claude's best swap waits with it in a note on the recipe (rule ASK, which flags it).
  Pål answers on /admin/pantry-questions (add_item, swap); a recipe with an open question cannot be approved. A second
  Claude call shares 100 points across adding the item and up to five swaps (weigh), his advice on that page.
- skip: water, not a food, or a pinch that would not change the dish.

Pål's answers are kept on the recipes (rule ASKED) and shown to Claude the next time (earlier), so it learns where he
draws the line. Then the recipe is recalculated (generate.recalculate). Each decision is noted on the recipe. Runs in
the queue after a recipe is made (tasks.run_pantry), and from scripts/fill_pantry.py for recipes made before; a
published recipe is only linked by alias, never changed or held back.

Every step takes `call` so tests can stand in for Claude.
"""
import datetime
import json
import logging
import re
import time
import uuid

from database.models import Ingredient, Recipe, RecipeLine, db
from services.ai_models import RECIPE_V2_EFFORT, RECIPE_V2_MODEL
from services.recipe_v2 import claude
from services.recipe_v2.generate import ASK, ASKED, ROOT, SWAP, env

log = logging.getLogger(__name__)
RULE = 'pantry'  # the recipe note; information only, never a reason to flag the recipe
AUTO = 'claude_auto'  # Ingredient.data_source of the items added here
NUTRIENTS = ('calories', 'protein', 'carbs', 'fat', 'fat_saturated', 'sugar', 'fiber', 'sodium_mg')
FACTOR_RANGE = (0.1, 5)  # outside it an amount_factor is a mistake, and the amount stays
EARLIER_MAX = 30  # Pål's answers Claude is shown
SWAPS_MAX = 5  # swaps Claude weighs against adding an item


def _categories():
    with open(f'{ROOT}/data/constraints/categories.json', encoding='utf-8') as f:
        return json.load(f)


def schema():
    """The answer: one decision per line, in the order given."""
    num = {'type': 'number'}
    new = {'type': 'object', 'additionalProperties': False,
           'required': ['name', 'main_category', 'sub_category', 'default_unit', 'average_g_per_unit', 'looks', *NUTRIENTS],
           'properties': {'name': {'type': 'string'}, 'main_category': {'type': 'string'}, 'looks': {'type': 'string'},
                          'sub_category': {'type': 'string'}, 'default_unit': {'type': 'string', 'enum': ['g', 'ml']},
                          'average_g_per_unit': num, **{n: num for n in NUTRIENTS}}}
    replacement = {'type': 'object', 'additionalProperties': False, 'required': ['find', 'replace'],
                   'properties': {'find': {'type': 'string'}, 'replace': {'type': 'string'}}}
    line = {'type': 'object', 'additionalProperties': False,
            'required': ['line', 'action', 'food_id', 'name', 'amount_factor', 'unit', 'replacements', 'new', 'reason'],
            'properties': {'line': {'type': 'string'},
                           'action': {'type': 'string', 'enum': ['alias', 'substitute', 'ask', 'skip']},
                           'food_id': {'type': 'string'}, 'name': {'type': 'string'}, 'amount_factor': num, 'unit': {'type': 'string'},
                           'replacements': {'type': 'array', 'items': replacement},
                           'new': {'anyOf': [new, {'type': 'null'}]}, 'reason': {'type': 'string'}}}
    return {'type': 'object', 'additionalProperties': False, 'required': ['lines'],
            'properties': {'lines': {'type': 'array', 'items': line}}}


def unlinked(recipe):
    """The recipe's lines without a pantry item, one per name (the same name twice is one decision)."""
    seen, out = set(), []
    for line in recipe.lines:
        key = line.name.strip().lower()
        if line.ingredient is None and key not in seen:
            seen.add(key)
            out.append(line)
    return out


def _pantry():
    """Active and pending items as "food_id name" lines; pending ones are marked, they can take aliases too."""
    rows = db.session.execute(db.select(Ingredient.food_id, Ingredient.name, Ingredient.status)
                              .where(Ingredient.status.in_(('active', 'pending'))).order_by(Ingredient.name)).all()
    return '\n'.join(f'{fid} {name}' + (' (pending)' if status == 'pending' else '') for fid, name, status in rows)


def _answered():
    """Pål's answers, newest first, as the notes on the recipes (rule ASKED) with the recipe's title."""
    rows = db.session.execute(db.select(Recipe.id, Recipe.title, Recipe.validation_errors).where(Recipe.schema_version == 2)).all()
    found = [dict(e, recipe_id=rid, title=title) for rid, title, notes in rows for e in notes or [] if e.get('rule') == ASKED]
    return sorted(found, key=lambda e: e.get('at') or '', reverse=True)


def earlier():
    """Pål's answers for the prompt, one a line."""
    return '\n'.join(f'- "{e["line"]}" in {e["title"]}: {e["answer"]}' for e in _answered()[:EARLIER_MAX])


def decide(recipe, lines, call=None):
    """Claude's decision per line: [{'line', 'action', 'food_id', 'name', 'amount_factor', 'unit', 'replacements', 'new',
    'reason'}] and the usage."""
    from services.recipe_v2.view import as_text

    call = call or claude.call
    cats = _categories()
    system = env.get_template('recipe_v2/pantry_fill.jinja2').render(
        pantry=_pantry(), earlier=earlier(), main_categories=', '.join(cats['main_categories']),
        sub_categories='\n'.join(f'{k}: {", ".join(v)}' for k, v in cats['sub_categories'].items()))
    asked = '\n'.join(f'- {line.name}: {line.amount or ""} {line.unit or ""}'.rstrip()
                      + (f' ({line.state})' if line.state else '') + (f' [kind: {line.variety}]' if line.variety else '') for line in lines)
    user = f'RECIPE\n{as_text(recipe)}\n\nLINES NOT IN THE PANTRY\n{asked}'
    msg, usage = call(RECIPE_V2_MODEL, RECIPE_V2_EFFORT, [{'role': 'user', 'content': user}], system=system,
                      schema=schema())
    return json.loads(claude.text_of(msg))['lines'], usage


def _by_food_id(food_id):
    return db.session.execute(db.select(Ingredient).where(Ingredient.food_id == food_id)).scalars().first()


def _by_name(name):
    from services.ingredient_service import normalize_alias
    return db.session.execute(db.select(Ingredient).where(
        db.func.lower(Ingredient.name) == normalize_alias(name), Ingredient.status.in_(('active', 'pending')))
    ).scalars().first()


def _propose(new):
    """The item Claude asks about: one that already has the name, or a new pending one (data_source AUTO). An item Pål
    said no to before is asked about again: a swap in one dish says nothing about the next."""
    found = _by_name(new['name'])
    if found:
        return found
    refused = db.session.execute(db.select(Ingredient).where(
        db.func.lower(Ingredient.name) == new['name'].strip().lower(), Ingredient.status == 'inactive', Ingredient.data_source == AUTO)).scalars().first()
    if refused:
        refused.status = 'pending'
        return refused
    cats = _categories()
    main = new['main_category'] if new['main_category'] in cats['main_categories'] else 'other'
    sub = new['sub_category'] if new['sub_category'] in cats['sub_categories'].get(main, []) else None
    kcal = new['calories']
    ing = Ingredient(
        food_id=f'auto-{uuid.uuid4().hex[:8]}', name=new['name'].strip().lower(), main_category=main, sub_category=sub,
        default_unit=new['default_unit'], average_g_per_unit=new['average_g_per_unit'] or None, status='pending',
        data_source=AUTO, created_at=datetime.datetime.now().isoformat(), calories_per_100g=kcal,
        kj_per_100g=round(kcal * 4.184, 1), protein_per_100g=new['protein'], carbs_per_100g=new['carbs'],
        fat_per_100g=new['fat'], fat_saturated_per_100g=new['fat_saturated'], sugar_per_100g=new['sugar'],
        fiber_per_100g=new['fiber'], sodium_mg_per_100g=new['sodium_mg'],
        image_notes=(new.get('looks') or '').strip() or None)  # the symbol prompt adds it (ingredient_symbols)
    db.session.add(ing)
    db.session.flush()
    return ing


def _note(recipe, rule, message, **extra):
    recipe.validation_errors = list(recipe.validation_errors or []) + [{'rule': rule, 'message': message, **extra}]
    return message


def _rewrite(recipe, replacements):
    """Change the words that name a swapped ingredient, in whatever the recipe says besides its lines. {iN} in a step
    is the line itself. The first letter stays as it was, so a sentence still starts with a capital."""
    def sub(text):
        for r in replacements:
            find, new = r.get('find') or '', r.get('replace') or ''
            if text and find:
                text = re.sub(rf'\b{re.escape(find)}\b', lambda m: new[:1].upper() + new[1:] if m.group(0)[0].isupper() else new,
                              text, flags=re.IGNORECASE)
        return text

    for step in recipe.steps:
        step.text, step.short, step.done_when = sub(step.text), sub(step.short), sub(step.done_when)
    for component in recipe.components:
        component.name = sub(component.name)
    recipe.chef_note = sub(recipe.chef_note)


def _swap(recipe, lines, item, name='', factor=1, replacements=(), reason='', unit=''):
    """Make the lines use another pantry item, in this recipe only: name, amount, unit and the words around them. A unit
    not in the catalog is a mistake, and the unit stays."""
    from services.measures import units

    was, now = lines[0].name, (name or item.name).strip()
    factor = factor if isinstance(factor, (int, float)) and FACTOR_RANGE[0] <= factor <= FACTOR_RANGE[1] else 1
    for line in lines:
        line.ingredient, line.name = item, now
        if factor != 1:
            line.amount = round(line.amount * factor, 2) if line.amount else line.amount
            line.gram_weight = round(line.gram_weight * factor, 1) if line.gram_weight else line.gram_weight
        if line.amount and unit in units():
            line.unit = unit
    _rewrite(recipe, sorted([{'find': was, 'replace': now}, *replacements], key=lambda r: -len(r.get('find') or '')))
    recipe.revision = (recipe.revision or 1) + 1
    recipe.revised_at = datetime.datetime.now(datetime.UTC).replace(tzinfo=None)
    return _note(recipe, SWAP, f'"{was}" is now {now}' + (f' (amount x {factor:g})' if factor != 1 else '') + (f': {reason}' if reason else ''))


def _ask(recipe, lines, item, reason, swap=None):
    """Link the lines to the pending item and leave the question on the recipe."""
    for line in lines:
        line.ingredient = item
    return _note(recipe, ASK, f'"{lines[0].name}": is it worth adding {item.name} to the pantry? {reason}', line=lines[0].name,
                 item=item.food_id, reason=reason, swap=swap)


def _swap_of(d):
    """Claude's swap in a question, what the note keeps."""
    if not d.get('food_id'):
        return None
    return {'food_id': d['food_id'], 'name': d.get('name') or '', 'amount_factor': d.get('amount_factor') or 1, 'unit': d.get('unit') or '',
            'replacements': d.get('replacements') or []}


def apply(recipe, decisions):
    """Carry out the decisions on the pantry and the recipe's lines. Returns the notes, one per decision, which are
    also on the recipe. The caller recalculates and commits."""
    from services.ingredient_service import add_alias

    lines = {}
    for line in recipe.lines:
        if line.ingredient is None:
            lines.setdefault(line.name.strip().lower(), []).append(line)
    published = recipe.status == 'approved'
    notes = []
    for d in decisions:
        key = (d.get('line') or '').strip().lower()
        if key not in lines:
            continue  # not one of the lines asked about
        action, reason = d.get('action'), d.get('reason') or ''
        item = _by_food_id(d.get('food_id') or '')
        if action in ('substitute', 'ask') and published:
            notes.append(_note(recipe, RULE, f'"{d["line"]}" left unlinked, the recipe is published ({reason})'))
        elif action == 'alias' and item is not None and item.status == 'pending':
            notes.append(_ask(recipe, lines[key], item, reason))
        elif action == 'alias' and item is not None:
            add_alias(item, d['line'])
            for line in lines[key]:
                line.ingredient = item
            notes.append(_note(recipe, RULE, f'"{d["line"]}" is now an alias of {item.name} ({reason})'))
        elif action == 'substitute' and item is not None and item.status == 'active':
            notes.append(_swap(recipe, lines[key], item, d.get('name'), d.get('amount_factor'), d.get('replacements') or [], reason, d.get('unit') or ''))
        elif action == 'ask' and d.get('new'):
            asked = _propose(d['new'])
            if asked.status == 'active':  # it was in the pantry after all
                add_alias(asked, d['line'])
                for line in lines[key]:
                    line.ingredient = asked
                notes.append(_note(recipe, RULE, f'"{d["line"]}" is now an alias of {asked.name} ({reason})'))
            else:
                notes.append(_ask(recipe, lines[key], asked, reason, _swap_of(d)))
        elif action in ('alias', 'substitute'):
            notes.append(_note(recipe, RULE, f'"{d["line"]}": no pantry item {d.get("food_id")!r}, left unlinked'))
        else:
            notes.append(_note(recipe, RULE, f'"{d["line"]}" left unlinked ({reason})'))
    db.session.flush()  # the links are what recalculate looks at
    return notes


def odds_schema():
    """The answer: 100 points shared across adding the item and up to five swaps."""
    swap = {'type': 'object', 'additionalProperties': False, 'required': ['food_id', 'share', 'why'],
            'properties': {'food_id': {'type': 'string'}, 'share': {'type': 'integer'}, 'why': {'type': 'string'}}}
    return {'type': 'object', 'additionalProperties': False, 'required': ['add', 'add_why', 'swaps'],
            'properties': {'add': {'type': 'integer'}, 'add_why': {'type': 'string'}, 'swaps': {'type': 'array', 'items': swap}}}


def _to_100(shares):
    """Whole numbers that add up to 100, in proportion: the rest goes to those that lost the most by rounding."""
    total = sum(shares)
    exact = [s * 100 / total for s in shares]
    whole = [int(x) for x in exact]
    for i in sorted(range(len(exact)), key=lambda i: whole[i] - exact[i])[:100 - sum(whole)]:
        whole[i] += 1
    return whole


def _clean_odds(answer, item):
    """What the note keeps: {'add', 'add_why', 'swaps': [{'food_id', 'name', 'share', 'why'}]}, best first, adding up to
    100. Only active pantry items, each once, and at most five. None when the answer gives nothing to go on."""
    swaps, seen = [], {item.food_id}
    for s in answer.get('swaps') or []:
        found = _by_food_id(s.get('food_id') or '') if s.get('food_id') not in seen else None
        if found is not None and found.status == 'active' and (s.get('share') or 0) > 0:
            seen.add(found.food_id)
            swaps.append({'food_id': found.food_id, 'name': found.name, 'share': s['share'], 'why': s.get('why') or ''})
    swaps = sorted(swaps, key=lambda s: -s['share'])[:SWAPS_MAX]
    add = max(answer.get('add') or 0, 0)
    if not add + sum(s['share'] for s in swaps):
        return None
    add, *shares = _to_100([add, *(s['share'] for s in swaps)])
    for s, share in zip(swaps, shares):
        s['share'] = share
    return {'add': add, 'add_why': answer.get('add_why') or '', 'swaps': sorted(swaps, key=lambda s: -s['share'])}


def weigh(recipe, item, call=None):
    """Claude's advice on one open question, kept on its note on the recipe (odds), in place of any before. Returns the
    cost in USD. The caller commits."""
    from services.recipe_v2.view import as_text

    note = _question_on(recipe, item)
    if note is None:
        return 0.0
    call = call or claude.call
    system = env.get_template('recipe_v2/pantry_odds.jinja2').render(pantry=_pantry(), earlier=earlier())
    user = (f'RECIPE\n{as_text(recipe)}\n\nTHE INGREDIENT\n{item.name}, in the recipe as "{note.get("line") or item.name}"'
            f'\nWhy it matters here: {note.get("reason") or "not given"}')
    msg, usage = call(RECIPE_V2_MODEL, RECIPE_V2_EFFORT, [{'role': 'user', 'content': user}], system=system, schema=odds_schema())
    odds = _clean_odds(json.loads(claude.text_of(msg)), item)
    recipe.validation_errors = [dict(e, odds=odds) if e is note else e for e in recipe.validation_errors]
    return usage['cost_usd']


def _weigh_open(recipe, call=None):
    """Weigh the recipe's questions that have no advice yet. It is only advice: one that fails is logged and left without,
    and the question can still be answered. Returns the cost in USD."""
    cost = 0.0
    for note in [e for e in recipe.validation_errors or [] if e.get('rule') == ASK and not e.get('odds')]:
        try:
            cost += weigh(recipe, _by_food_id(note.get('item') or ''), call=call)
        except Exception:
            log.exception('Recipe %s: no advice on %s', recipe.id, note.get('item'))
    return cost


def fill(recipe, call=None):
    """Decide and apply for one recipe, then recalculate it and weigh its questions. Returns {'notes', 'cost_usd'}; nothing
    to do when every line is linked. The caller commits."""
    from services.recipe_v2.generate import recalculate

    lines = unlinked(recipe)
    if not lines:
        return {'notes': [], 'cost_usd': 0.0}
    decisions, usage = decide(recipe, lines, call=call)
    recipe.validation_errors = [e for e in recipe.validation_errors or [] if e.get('rule') != RULE]
    notes = apply(recipe, decisions)
    recalculate(recipe)
    return {'notes': notes, 'cost_usd': usage['cost_usd'] + _weigh_open(recipe, call=call)}


def _waiting(item):
    """{recipe: its lines} using an item that waits for an answer."""
    lines = db.session.execute(db.select(RecipeLine).where(RecipeLine.ingredient_id == item.id).order_by(RecipeLine.recipe_id, RecipeLine.sort_order)).scalars()
    found = {}
    for line in lines:
        found.setdefault(line.recipe, []).append(line)
    return found


def _question_on(recipe, item):
    return next((e for e in recipe.validation_errors or [] if e.get('rule') == ASK and e.get('item') == item.food_id), None)


def _waiting_for_answer():
    """The condition on Ingredient: a pending item recipes use."""
    used = db.select(RecipeLine.ingredient_id).where(RecipeLine.ingredient_id.isnot(None))
    return (Ingredient.status == 'pending', Ingredient.id.in_(used))


def open_questions():
    """How many items wait for Pål, for the mark in the admin menu."""
    return db.session.scalar(db.select(db.func.count(Ingredient.id)).where(*_waiting_for_answer()))


def questions():
    """What waits for Pål: each pending item recipes use, with the recipes, why Claude asks and the swap it suggests."""
    items = db.session.execute(db.select(Ingredient).where(*_waiting_for_answer()).order_by(Ingredient.id)).scalars().all()
    out = []
    for item in items:
        rows = []
        for recipe, lines in _waiting(item).items():
            note = _question_on(recipe, item) or {}
            swap = note.get('swap') or None
            suggested = _by_food_id(swap['food_id']) if swap else None
            rows.append({'recipe': recipe, 'lines': lines, 'reason': note.get('reason'), 'swap': swap, 'odds': note.get('odds'),
                         'swap_item': suggested if suggested is not None and suggested.status == 'active' else None})
        out.append({'item': item, 'rows': rows, 'can_swap': all(r['swap_item'] for r in rows)})
    return out


def answered(limit=20):
    """Pål's latest answers, for the page."""
    return _answered()[:limit]


def _answer(recipe, item, answer):
    """The question on the recipe becomes the answer, then the recipe is worked out again."""
    from services.recipe_v2.generate import recalculate

    note = _question_on(recipe, item) or {}
    recipe.validation_errors = [e for e in recipe.validation_errors or [] if not (e.get('rule') == ASK and e.get('item') == item.food_id)]
    _note(recipe, ASKED, f'{item.name}: {answer}', line=note.get('line') or item.name, answer=answer, reason=note.get('reason'),
          at=datetime.datetime.now(datetime.UTC).isoformat())
    recalculate(recipe)


def add_item(item):
    """Pål's yes: the item joins the pantry as long tail, and what the recipes call it become its aliases. Its symbol is
    made after (make_symbols). The caller commits."""
    from services.ingredient_service import add_alias

    item.status, item.tier = 'active', item.tier or 'long_tail'
    for recipe, lines in _waiting(item).items():
        for name in {line.name for line in lines}:
            add_alias(item, name)
        _answer(recipe, item, f'added {item.name} to the pantry')


def swap(item, other=None):
    """Pål's no: each recipe takes the swap Claude suggested for it, or the pantry item he chose (other), and the item
    leaves the pantry. A recipe without a swap keeps its question. Returns the recipes changed. The caller commits."""
    changed = []
    for recipe, lines in _waiting(item).items():
        s = (_question_on(recipe, item) or {}).get('swap') or {}
        target = other or _by_food_id(s.get('food_id') or '')
        if target is None or target.status != 'active':
            continue
        name = '' if other else s.get('name')
        replacements = [] if other else s.get('replacements') or []
        _swap(recipe, lines, target, name, 1 if other else s.get('amount_factor'), replacements, unit='' if other else s.get('unit') or '')
        _answer(recipe, item, f'not added, swapped to {target.name}')
        changed.append(recipe)
    if not _waiting(item):
        item.status = 'inactive'
    return changed


def open_question(recipe):
    """The first ingredient in the recipe that waits for an answer, or None. Such a recipe cannot be approved."""
    return next((line.ingredient for line in recipe.lines if line.ingredient is not None and line.ingredient.status == 'pending'), None)


def without_symbol(recipe=None):
    """The items added here and let in that have no symbol image yet: the recipe's, or all of them."""
    stmt = db.select(Ingredient).where(Ingredient.data_source == AUTO, Ingredient.status == 'active', Ingredient.image_url.is_(None))
    if recipe is not None:
        ids = {line.ingredient_id for line in recipe.lines if line.ingredient_id}
        stmt = stmt.where(Ingredient.id.in_(ids or {0}))
    return db.session.execute(stmt.order_by(Ingredient.id)).scalars().all()


def make_symbols(items, storage, draw=None):
    """Make the symbol image of each item (services/ingredient_symbols.py), as the ingredient page's "regenerate"
    does. One that fails is logged and left without; it can be made from the ingredient page. Returns the names
    made. The caller commits."""
    from services.ingredient_symbols import generate_symbol, web_image

    draw = draw or generate_symbol
    made = []
    for ing in items:
        try:
            png, prompt, _meta = draw(ing)
            ing.image_url = storage.save(web_image(png), f'{ing.food_id}_{int(time.time())}.webp', 'pantry/symbols')
            ing.image_prompt, ing.has_transparent_image = prompt, False
            made.append(ing.name)
        except Exception:
            log.exception('Pantry item %s: no symbol image', ing.name)
    return made


def needs_filling(recipe_id):
    recipe = db.session.get(Recipe, recipe_id)
    return recipe is not None and any(line.ingredient is None for line in recipe.lines)
