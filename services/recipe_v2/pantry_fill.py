"""Fill the pantry for a made recipe: the lines the matcher could not link (services/recipe_service.py).

One Claude call sees those lines and the whole pantry, and decides for each line:

- alias: the line is a food the pantry has under another name ("neutral oil" is canola oil). The name becomes an
  alias of that item, so the next recipe with it is linked by the matcher straight away.
- new: a real product a shopper in Norway buys that the pantry lacks ("lingonberries"). It is added as active, so
  the matcher and the next recipes use it, marked data_source "claude_auto" so it can be found and checked, with its
  nutrition per 100 g as sold; the symbol image can be made from the ingredient page.
- skip: a pinch of something rare that would not change the nutrition and will not come back, or not a food.

Then the recipe is recalculated (generate.recalculate). Each decision is noted on the recipe (rule "pantry",
which does not flag it), so the review report and the admin chip show what was done. Runs in the queue after a
recipe is made (tasks.run_pantry), and from scripts/fill_pantry.py for recipes made before.

Every step takes `call` so tests can stand in for Claude.
"""
import json
import uuid
from datetime import datetime

from database.models import Ingredient, Recipe, db
from services.ai_models import RECIPE_V2_EFFORT, RECIPE_V2_MODEL
from services.recipe_v2 import claude
from services.recipe_v2.generate import ROOT, env

RULE = 'pantry'  # the recipe note; information only, never a reason to flag the recipe
AUTO = 'claude_auto'  # Ingredient.data_source of the items added here
NUTRIENTS = ('calories', 'protein', 'carbs', 'fat', 'fat_saturated', 'sugar', 'fiber', 'sodium_mg')


def _categories():
    with open(f'{ROOT}/data/constraints/categories.json', encoding='utf-8') as f:
        return json.load(f)


def schema():
    """The answer: one decision per line, in the order given."""
    num = {'type': 'number'}
    new = {'type': 'object', 'additionalProperties': False,
           'required': ['name', 'main_category', 'sub_category', 'default_unit', 'average_g_per_unit', *NUTRIENTS],
           'properties': {'name': {'type': 'string'}, 'main_category': {'type': 'string'},
                          'sub_category': {'type': 'string'}, 'default_unit': {'type': 'string', 'enum': ['g', 'ml']},
                          'average_g_per_unit': num, **{n: num for n in NUTRIENTS}}}
    line = {'type': 'object', 'additionalProperties': False,
            'required': ['line', 'action', 'food_id', 'new', 'reason'],
            'properties': {'line': {'type': 'string'}, 'action': {'type': 'string', 'enum': ['alias', 'new', 'skip']},
                           'food_id': {'type': 'string'}, 'new': {'anyOf': [new, {'type': 'null'}]},
                           'reason': {'type': 'string'}}}
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


def decide(recipe, lines, call=None):
    """Claude's decision per line: [{'line', 'action', 'food_id', 'new', 'reason'}] and the usage."""
    call = call or claude.call
    cats = _categories()
    system = env.get_template('recipe_v2/pantry_fill.jinja2').render(
        pantry=_pantry(), main_categories=', '.join(cats['main_categories']),
        sub_categories='\n'.join(f'{k}: {", ".join(v)}' for k, v in cats['sub_categories'].items()))
    asked = '\n'.join(f'- {line.name}: {line.amount or ""} {line.unit or ""}'.rstrip()
                      + (f' ({line.state})' if line.state else '') for line in lines)
    user = f'RECIPE\n{recipe.title}\n\nLINES NOT IN THE PANTRY\n{asked}'
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


def _create(new):
    """A new pantry item from Claude's description (active, data_source AUTO), or the item that has that name."""
    found = _by_name(new['name'])
    if found:
        return found
    cats = _categories()
    main = new['main_category'] if new['main_category'] in cats['main_categories'] else 'other'
    sub = new['sub_category'] if new['sub_category'] in cats['sub_categories'].get(main, []) else None
    kcal = new['calories']
    ing = Ingredient(
        food_id=f'auto-{uuid.uuid4().hex[:8]}', name=new['name'].strip().lower(), main_category=main, sub_category=sub,
        default_unit=new['default_unit'], average_g_per_unit=new['average_g_per_unit'] or None, status='active',
        data_source=AUTO, created_at=datetime.now().isoformat(), calories_per_100g=kcal,
        kj_per_100g=round(kcal * 4.184, 1), protein_per_100g=new['protein'], carbs_per_100g=new['carbs'],
        fat_per_100g=new['fat'], fat_saturated_per_100g=new['fat_saturated'], sugar_per_100g=new['sugar'],
        fiber_per_100g=new['fiber'], sodium_mg_per_100g=new['sodium_mg'])
    db.session.add(ing)
    db.session.flush()
    return ing


def apply(recipe, decisions):
    """Carry out the decisions on the pantry and the recipe's lines. Returns the notes, one per decision.
    The caller recalculates and commits."""
    from services.ingredient_service import add_alias

    lines = {}
    for line in recipe.lines:
        if line.ingredient is None:
            lines.setdefault(line.name.strip().lower(), []).append(line)
    notes = []
    for d in decisions:
        key = (d.get('line') or '').strip().lower()
        if key not in lines:
            continue  # not one of the lines asked about
        ing = None
        if d['action'] == 'alias':
            ing = _by_food_id(d.get('food_id') or '')
            if ing is None:
                notes.append(f'"{d["line"]}": no pantry item {d.get("food_id")!r}, left unlinked')
                continue
            add_alias(ing, d['line'])
            notes.append(f'"{d["line"]}" is now an alias of {ing.name} ({d["reason"]})')
        elif d['action'] == 'new' and d.get('new'):
            ing = _create(d['new'])
            add_alias(ing, d['line'])  # skipped when it is the item's own name
            notes.append(f'"{d["line"]}": new pantry item {ing.name} ({d["reason"]})')
        else:
            notes.append(f'"{d["line"]}" left unlinked ({d["reason"]})')
        if ing is not None:
            for line in lines[key]:
                line.ingredient = ing
    db.session.flush()  # the links are what recalculate looks at
    return notes


def fill(recipe, call=None):
    """Decide and apply for one recipe, then recalculate it. Returns {'notes', 'cost_usd'}; nothing to do when every
    line is linked. The caller commits."""
    from services.recipe_v2.generate import recalculate

    lines = unlinked(recipe)
    if not lines:
        return {'notes': [], 'cost_usd': 0.0}
    decisions, usage = decide(recipe, lines, call=call)
    notes = apply(recipe, decisions)
    kept = [e for e in recipe.validation_errors or [] if e.get('rule') != RULE]
    recipe.validation_errors = kept + [{'rule': RULE, 'message': n} for n in notes]
    recalculate(recipe)
    return {'notes': notes, 'cost_usd': usage['cost_usd']}


def needs_filling(recipe_id):
    recipe = db.session.get(Recipe, recipe_id)
    return recipe is not None and any(line.ingredient is None for line in recipe.lines)
