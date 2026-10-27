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

from database.models import Chef, Ingredient, Recipe, db
from schemas.recipe_v2 import CUISINE_NOTES, CUISINES, DIFFICULTIES, MEAL_TYPES
from services.ai_models import RECIPE_V2_EFFORT, RECIPE_V2_MODEL
from services.recipe_v2 import claude, derive, persona, states
from services.recipe_v2.language import prompt_name
from services.recipe_v2.store import save_v2, to_v2
from services.recipe_v2_validator import format_errors_for_retry, validate_recipe_v2

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MAX_RETRIES = 2
# Hand-made reference recipes shown to the model as examples of correct output.
EXAMPLES = ('carbonara', 'lasagne')
SOURCE_TYPES = {'idea': 'description', 'text': 'text', 'web': 'web', 'video': 'video', 'version': 'version'}  # recipe.source_type

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
        'states': '; '.join(f"{x['id']} ({x['en']} / {x['nb']}" + (f"; grades: {', '.join(x['grades'])}" if x['grades'] else '') + ')'
                            for x in _load(*c, 'states.json')['states']),
        'notes': ', '.join(_load(*c, 'states.json')['notes']['en'] + _load(*c, 'states.json')['notes']['nb']),
        'cuisines': ', '.join(f'{c} ({CUISINE_NOTES[c]})' if c in CUISINE_NOTES else c for c in CUISINES),
        'difficulties': ', '.join(DIFFICULTIES),
        'meal_types': ', '.join(MEAL_TYPES),
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


def write_text(kind, source, language=None, call=None, chef=None):
    """Round 1. kind 'idea' writes a recipe from a short idea, as the chef persona if there is one; 'text'
    tidies a pasted recipe; 'web' reads the recipe at the link
    (services/recipe_v2/sources.py) and tidies it; 'video' has the video watched and written down, then tidies that. A pasted or linked recipe is kept as it is, whatever the persona.
    'version' rewrites a saved recipe, given as text (view.as_text), as the chef persona.
    language is a code from services/recipe_v2/language.py. None writes in the language of the idea or the source;
    a version keeps the base recipe's language."""
    language = prompt_name(language)
    if kind == 'web':
        from services.recipe_v2.sources import fetch_recipe_text

        page, _ = fetch_recipe_text(source)
        prompt = env.get_template('recipe_v2/normalize.jinja2').render(kind='a web page', source=page, language=language)
    elif kind == 'video':
        from services.recipe_v2.sources import fetch_video_text

        prompt = env.get_template('recipe_v2/normalize.jinja2').render(kind='what a cooking video shows, written down',
                                                                       source=fetch_video_text(source), language=language)
    elif kind == 'idea':
        prompt = env.get_template('recipe_v2/idea.jinja2').render(idea=source, language=language,
                                                                  persona=persona.prompt_block(chef))
    elif kind == 'version':
        if not chef:
            raise ValueError('A version needs a chef persona')
        prompt = env.get_template('recipe_v2/version.jinja2').render(source=source, persona=persona.prompt_block(chef))
    elif kind == 'text':
        prompt = env.get_template('recipe_v2/normalize.jinja2').render(kind='text pasted by the user', source=source,
                                                                       language=language)
    else:
        raise ValueError(f'Unknown source kind {kind!r}')
    msg, usage = (call or claude.call)(RECIPE_V2_MODEL, RECIPE_V2_EFFORT, [{'role': 'user', 'content': prompt}])
    return claude.text_of(msg), usage


def structure(text, call=None):
    """Round 2 with the validator in a loop. Returns (recipe dict or None, attempts)."""
    call = call or claude.call
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
            states.fill(recipe)  # the states the prep steps give, where the model left them out
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
    import ai_engine
    from services.pantry_service import get_slim_pantry_context
    from services.recipe_service import _resolve_ingredient

    # The fuzzy matcher's pantry map is only filled by the old generation; fill it here too.
    if not ai_engine.pantry_map:
        ai_engine.set_pantry_memory(get_slim_pantry_context())
    ids, missing = {}, []
    for line in data['ingredients']:
        record = _resolve_ingredient(line)
        if record:
            ids[line['local_id']] = record.id
        else:
            missing.append(line['name'])
    return ids, missing


PERSONA_KINDS = ('description', 'version')  # recipe.source_type of recipes the chef persona wrote


def refresh(recipe, chef=None):
    """Derive the metadata and nutrition again and check the persona's hard rules, without asking Claude.

    Run after saving, and again when the pantry or the rules have changed (the Recalculate button). Only the
    persona notes in validation_errors are replaced. The caller commits."""
    derive.apply(recipe, to_v2(recipe))
    # The persona's hard rules: noted and flagged, never a reason to throw the recipe away
    notes = persona.check(recipe, chef) if chef else []
    kept = [e for e in recipe.validation_errors or [] if e.get('rule') != 'persona']
    recipe.validation_errors = kept + [{'rule': 'persona', 'message': n} for n in notes]
    return notes


def recalculate(recipe):
    """Refresh a saved v2 recipe in place (services/recipe_v2/derive.py, nutrition.py, persona.py). Lines not in the
    pantry are matched again first: an ingredient or alias added since ("frozen chopped spinach") links them."""
    unlinked = [line for line in recipe.lines if line.ingredient_id is None]
    if unlinked:
        found, _ = match_pantry({'ingredients': [{'local_id': line.local_id, 'name': line.name} for line in unlinked]})
        for line in unlinked:
            if line.local_id in found:
                line.ingredient = db.session.get(Ingredient, found[line.local_id])
    refresh(recipe, persona.spec_for(recipe))
    missing = any(line.ingredient_id is None for line in recipe.lines)
    recipe.is_flagged_for_review = bool(recipe.validation_errors) or missing
    return recipe


def create_recipe(kind, source, chef_id=None, language=None, call=None, recipe=None, settings=None, age_from_months=None):
    """Run both rounds and save the result as a draft. Returns (recipe, report).

    recipe is the placeholder made when the job was queued; without it a new recipe is made. settings
    (persona.SETTINGS) and the baby's age come from the placeholder, or are given for a new recipe.

    The recipe is flagged for review when it is still invalid after the retries,
    when some lines are not in the pantry, or when it breaks a hard rule of its chef persona."""
    chef_id = recipe.chef_id if recipe is not None else chef_id
    settings = recipe.settings if recipe is not None else settings
    age_from_months = recipe.age_from_months if recipe is not None else age_from_months
    chef = persona.spec(db.session.get(Chef, chef_id) if chef_id else None, settings, age_from_months)
    text, round1 = write_text(kind, source, language, call=call, chef=chef)
    data, attempts = structure(text, call=call)
    calls = [round1] + attempts

    # The model's title, else the first line of the round 1 text, which is the title there.
    first_line = next((line.strip() for line in text.splitlines() if line.strip()), '')
    title = ((data or {}).get('title') or '').strip() or first_line[:200] or source[:120]
    if recipe is None:
        recipe = Recipe(cuisine='', difficulty='', chef_id=chef_id, settings=settings or None,
                        age_from_months=age_from_months if 'baby' in (settings or []) else None)
        db.session.add(recipe)
    recipe.title, recipe.status, recipe.source_type = title, 'draft', SOURCE_TYPES[kind]
    # A version keeps the note on what it is a version of; the base recipe's text is not an input worth storing
    if not (kind == 'version' and recipe.source_input):
        recipe.source_input = source[:500]
    recipe.source_text, recipe.schema_version = text, 2
    if language:  # a version has its base recipe's language from when it was queued
        recipe.language = language
    missing = []
    if data:
        ids, missing = match_pantry(data)
        save_v2(recipe, dict(data, title=title), ids)
        db.session.flush()
        recipe.validation_errors = []
        refresh(recipe, chef if kind in ('idea', 'version') else None)
    else:
        recipe.validation_errors = attempts[-1]['errors']
    recipe.is_flagged_for_review = not data or bool(missing) or bool(data and recipe.validation_errors)
    db.session.commit()

    report = {
        'recipe_id': recipe.id, 'valid': bool(data), 'attempts': len(attempts), 'missing_in_pantry': missing,
        'persona_notes': [e['message'] for e in recipe.validation_errors if e.get('rule') == 'persona'],
        'warnings': attempts[-1]['warnings'], 'cost_usd': round(sum(c['cost_usd'] for c in calls), 4),
        'seconds': round(sum(c['seconds'] for c in calls), 1),
    }
    return recipe, report
