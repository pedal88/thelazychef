"""Translate a recipe's words and the pantry's names into Norwegian with Claude. services/recipe_v2/translation.py keeps
and shows what comes back; this only asks. tasks.run_translation runs it when a recipe is approved, and
scripts/translate.py for saved recipes.

The answer is checked with translation.problems: a field missing or a step with other {iN} than the original goes back
for at most MAX_RETRIES new attempts, and a recipe still wrong is left in English. Every function takes `call` so tests
can stand in for Claude.
"""
import json
import os

from jinja2 import Environment, FileSystemLoader

from services.ai_models import TRANSLATE_EFFORT, TRANSLATE_MODEL
from services.recipe_v2 import claude, translation

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
env = Environment(loader=FileSystemLoader(os.path.join(ROOT, 'data', 'prompts')))
MAX_RETRIES = 2
PANTRY_BATCH = 150  # items in one call

_TEXT = {'anyOf': [{'type': 'string'}, {'type': 'null'}]}


def _closed(**fields):
    return {'type': 'object', 'additionalProperties': False, 'properties': fields, 'required': list(fields)}


def _rows(**fields):
    return {'type': 'array', 'items': _closed(id={'type': 'string'}, **fields)}


RECIPE_SCHEMA = _closed(
    title={'type': 'string'}, chef_note=_TEXT, yield_text=_TEXT,
    components=_rows(name=_TEXT),
    lines=_rows(**{f: _TEXT for f in translation.LINE_FIELDS}),
    steps=_rows(**{f: _TEXT for f in translation.STEP_FIELDS}),
)
PANTRY_SCHEMA = _closed(items={'type': 'array', 'items': _closed(id={'type': 'integer'}, name_nb={'type': 'string'})})


def glossary():
    with open(os.path.join(ROOT, 'data', 'constraints', 'glossary_nb.json'), encoding='utf-8') as f:
        return json.load(f)


def _system():
    return env.get_template('recipe_v2/translate.jinja2').render(glossary=glossary())


def _as_rows(words, pantry_names, amounts):
    """source()'s text as what Claude reads: each table as a list of rows with their ids, and on a line what it needs
    to get the number right."""
    def rows(key):
        return [{'id': lid, **fields} for lid, fields in words[key].items()]
    lines = [{**row, **amounts.get(row['id'], {}), **({'pantry_name_nb': pantry_names[row['id']]} if pantry_names.get(row['id']) else {})}
             for row in rows('lines')]
    return {k: words[k] for k in ('title', 'chef_note', 'yield_text') if k in words} | {
        'components': rows('components'), 'lines': lines, 'steps': rows('steps')}


def _from_rows(answer):
    """The answer in source()'s shape, without what it left empty."""
    def filled(row):
        return {k: v for k, v in row.items() if k != 'id' and v not in (None, '')}
    return {k: answer[k] for k in ('title', 'chef_note', 'yield_text') if answer.get(k)} | {
        key: {row['id']: filled(row) for row in answer.get(key) or []} for key in ('components', 'lines', 'steps')}


def name_items(recipe, call=None, model=TRANSLATE_MODEL):
    """Norwegian names for this recipe's pantry items that have none, before its words: they are what the lines use. The
    caller commits."""
    items = list({i.ingredient.id: i.ingredient for i in recipe.lines if i.ingredient is not None and not i.ingredient.name_nb}.values())
    if items:
        names, _ = translate_pantry(items, call=call, model=model)
        for item in items:
            item.name_nb = names.get(item.id) or item.name_nb


def translate_recipe(recipe, call=None, model=TRANSLATE_MODEL):
    """(words in source()'s shape, ready for translation.save, or None; the attempts with their cost and problems)."""
    call = call or claude.call
    original = translation.source(recipe)
    pantry_names = {i.local_id: i.ingredient.name_nb for i in recipe.lines if i.ingredient is not None and i.ingredient.name_nb}
    amounts = {i.local_id: {k: v for k, v in (('amount', i.amount), ('unit', i.unit)) if v is not None} for i in recipe.lines}
    messages = [{'role': 'user', 'content': json.dumps(_as_rows(original, pantry_names, amounts), ensure_ascii=False)}]
    system = _system()
    attempts = []
    for n in range(1 + MAX_RETRIES):
        msg, usage = call(model, TRANSLATE_EFFORT, messages, system=system, schema=RECIPE_SCHEMA)
        try:
            if msg.stop_reason in ('refusal', 'max_tokens'):
                raise ValueError(f'stop_reason {msg.stop_reason}')
            words = _from_rows(json.loads(claude.text_of(msg)))
            wrong = translation.problems(original, words)
        except (ValueError, KeyError, TypeError, AttributeError) as e:  # json.JSONDecodeError is a ValueError
            words, wrong = None, [f'The answer could not be read: {e}']
        attempts.append({'attempt': n + 1, 'problems': wrong, **usage})
        if not wrong:
            return words, attempts
        messages += [
            {'role': 'assistant', 'content': msg.content},
            {'role': 'user', 'content': 'This was wrong:\n' + '\n'.join(wrong) + '\n\nGive the whole translation again, with these put right.'},
        ]
    return None, attempts


def translate_pantry(items, call=None, model=TRANSLATE_MODEL):
    """({ingredient id: Norwegian name}, usages) for these Ingredients. What an answer leaves out stays without a name."""
    call = call or claude.call
    names, usages = {}, []
    system = _system()
    for start in range(0, len(items), PANTRY_BATCH):
        batch = items[start:start + PANTRY_BATCH]
        asked = {i.id for i in batch}
        content = json.dumps({'pantry': [{'id': i.id, 'name': i.name, 'category': i.sub_category or i.main_category} for i in batch]},
                             ensure_ascii=False)
        msg, usage = call(model, TRANSLATE_EFFORT, [{'role': 'user', 'content': content}], system=system, schema=PANTRY_SCHEMA)
        usages.append(usage)
        try:
            found = json.loads(claude.text_of(msg))['items']
        except (ValueError, KeyError, TypeError):
            continue
        names.update({row['id']: row['name_nb'].strip() for row in found if row.get('id') in asked and (row.get('name_nb') or '').strip()})
    return names, usages
