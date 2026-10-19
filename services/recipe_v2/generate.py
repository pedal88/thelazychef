"""Make a recipe in model v2 (docs/RECIPE_MODEL_V2.md, section 7).

Round 1 writes or tidies the recipe as plain text. Round 2 turns the text into
the graph with structured output, and the validator sends errors back for at
most two new attempts. The lines are matched to the pantry, and the recipe is
saved as a draft. A recipe that is still invalid is saved as a flagged draft
with its errors and the round 1 text, so it can be structured again later.

Every step takes `call` so tests can stand in for Claude.
"""
import json
import os

from jinja2 import Environment, FileSystemLoader

from database.models import Ingredient, Recipe, db
from services.ai_models import RECIPE_V2_EFFORT, RECIPE_V2_MODEL
from services.recipe_v2 import claude
from services.recipe_v2.store import save_v2
from services.recipe_v2_validator import format_errors_for_retry, validate_recipe_v2

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MAX_RETRIES = 2
# Hand-made reference recipes shown to the model as examples of correct output.
EXAMPLES = ('carbonara', 'lasagne')
SOURCE_TYPES = {'idea': 'description', 'text': 'text'}  # recipe.source_type, as the old generation uses it

env = Environment(loader=FileSystemLoader(os.path.join(ROOT, 'data', 'prompts')))


def _load(*parts):
    with open(os.path.join(ROOT, *parts), encoding='utf-8') as f:
        return json.load(f)


def catalogs():
    c = ('data', 'constraints')
    methods = _load(*c, 'methods.json')['methods']
    eq = _load(*c, 'equipment.json')['equipment']
    units = _load(*c, 'units.json')['units']
    return {
        'methods': ', '.join(m['id'] + (' [heat]' if m['heat'] else '') for m in methods),
        'equipment': ', '.join(f"{e['id']} ({e['name']})" for e in eq),
        'units': ', '.join(f"{u['id']} ({u['name']})" if u['name'] != u['id'] else u['id'] for u in units),
    }


def pantry_text():
    """Active pantry ingredients as "food_id name" lines, so the model can pick real ids."""
    rows = db.session.execute(
        db.select(Ingredient.food_id, Ingredient.name).where(Ingredient.status == 'active').order_by(Ingredient.name)
    ).all()
    return '\n'.join(f'{food_id} {name}' for food_id, name in rows)


def structure_prompt(source):
    """(system, user). The system part is the same for every recipe and is cached."""
    examples = []
    for name in EXAMPLES:
        r = _load('data', 'pilot_v2', 'fasit', name + '.json')
        examples.append({'title': r['title'], 'json': json.dumps(r, ensure_ascii=False, separators=(',', ':'))})
    prompt = env.get_template('recipe_v2/structure.jinja2').render(
        source=source, examples=examples, pantry=pantry_text(), **catalogs())
    head, sep, tail = prompt.rpartition('\nSOURCE RECIPE\n')
    if not sep:
        raise ValueError('structure.jinja2 must end with a "SOURCE RECIPE" section')
    return head, 'SOURCE RECIPE\n' + tail


def write_text(kind, source, language='English', call=claude.call):
    """Round 1. kind 'idea' writes a recipe from a short idea; 'text' tidies a pasted recipe and keeps its language."""
    if kind == 'idea':
        prompt = env.get_template('recipe_v2/idea.jinja2').render(idea=source, language=language)
    elif kind == 'text':
        prompt = env.get_template('recipe_v2/normalize.jinja2').render(kind='text pasted by the user', source=source)
    else:
        raise ValueError(f'Unknown source kind {kind!r}')
    msg, usage = call(RECIPE_V2_MODEL, RECIPE_V2_EFFORT, [{'role': 'user', 'content': prompt}])
    return claude.text_of(msg), usage


def structure(text, call=claude.call):
    """Round 2 with the validator in a loop. Returns (recipe dict or None, attempts)."""
    system, user = structure_prompt(text)
    schema = claude.recipe_json_schema()
    messages = [{'role': 'user', 'content': user}]
    attempts, recipe = [], None
    for n in range(1 + MAX_RETRIES):
        msg, usage = call(RECIPE_V2_MODEL, RECIPE_V2_EFFORT, messages, system=system, schema=schema)
        try:
            if msg.stop_reason in ('refusal', 'max_tokens'):
                raise ValueError(f'stop_reason {msg.stop_reason}')
            recipe = json.loads(claude.text_of(msg))
            result = validate_recipe_v2(recipe)
        except ValueError as e:  # json.JSONDecodeError is a ValueError
            recipe = None
            result = {'valid': False, 'failed_rules': ['json'], 'warnings': [],
                      'errors': [{'rule': 'json', 'message': f'The answer was not valid JSON: {e}'}]}
        attempts.append({'attempt': n + 1, 'valid': result['valid'], 'errors': result['errors'],
                         'warnings': result['warnings'], **usage})
        if result['valid']:
            return recipe, attempts
        messages += [
            {'role': 'assistant', 'content': msg.content},
            {'role': 'user', 'content': 'Your answer failed validation:\n' + format_errors_for_retry(result) +
                                        '\n\nReturn the complete corrected recipe as JSON. Keep everything that was already correct.'},
        ]
    return None, attempts


def match_pantry(data):
    """Pantry ingredient per line: the model's pantry_id if it exists, otherwise the name matcher.

    Returns (ingredient ids by line local_id, names of lines not in the pantry)."""
    from services.recipe_service import _resolve_ingredient

    ids, missing = {}, []
    for line in data['ingredients']:
        record = _resolve_ingredient(line)
        if record:
            ids[line['local_id']] = record.id
        else:
            missing.append(line['name'])
    return ids, missing


def create_recipe(kind, source, chef_id=None, language='English', call=claude.call):
    """Run both rounds and save the result as a draft. Returns (recipe, report).

    The recipe is flagged for review when it is still invalid after the retries,
    or when some lines are not in the pantry."""
    text, round1 = write_text(kind, source, language, call=call)
    data, attempts = structure(text, call=call)
    calls = [round1] + attempts

    recipe = Recipe(title=(data or {}).get('title') or source[:120], cuisine='', difficulty='', chef_id=chef_id,
                    status='draft', source_type=SOURCE_TYPES[kind], source_input=source[:500], source_text=text,
                    schema_version=2)
    db.session.add(recipe)
    missing = []
    if data:
        ids, missing = match_pantry(data)
        save_v2(recipe, data, ids)
        recipe.validation_errors = []
    else:
        recipe.validation_errors = attempts[-1]['errors']
    recipe.is_flagged_for_review = not data or bool(missing)
    db.session.commit()

    report = {
        'recipe_id': recipe.id, 'valid': bool(data), 'attempts': len(attempts), 'missing_in_pantry': missing,
        'warnings': attempts[-1]['warnings'], 'cost_usd': round(sum(c['cost_usd'] for c in calls), 4),
        'seconds': round(sum(c['seconds'] for c in calls), 1),
    }
    return recipe, report
