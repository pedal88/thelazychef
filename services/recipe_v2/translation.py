"""A recipe's text in another language: one RecipeTranslation row per recipe and language, over the text in
recipe.language. The graph, amounts and times are shared, so only the words are here, by local_id, because save_v2
writes the components, lines and steps anew and their ids do not last.

source(recipe) is the text to translate, and save() takes the same shape back in the other language, refusing one with
a field missing or with other {iN} than the original: a step is a template, and its pills come from those. The row knows
the text it was made from (source_hash), so when a recipe's words change the page shows the original until it has been
translated again, never words that no longer match the recipe. Saving the same words again changes nothing.

A list shows many recipes and has not read their steps, so titles() takes one query and asks only whether the title
itself is the one that was translated (source_title).

English stays the base: an English reader always gets the text as written, without a query, and so does a reader whose
language the recipe is written in.
"""
import datetime
import hashlib
import json

from database.models import RecipeTranslation, db
from services import language
from services.recipe_v2.language import DEFAULT
from services.recipe_v2_validator import PLACEHOLDER

LINE_FIELDS = ('name', 'prep_style', 'variety')
STEP_FIELDS = ('short', 'verb', 'text', 'done_when')


def _filled(row, fields):
    return {f: getattr(row, f) for f in fields if getattr(row, f)}


def source(recipe):
    """The words of the recipe as written: what is translated, and what source_hash is taken of."""
    return {
        'title': recipe.title,
        **_filled(recipe, ('chef_note', 'yield_text')),
        'components': {c.local_id: {'name': c.name} for c in recipe.components},
        'lines': {i.local_id: _filled(i, LINE_FIELDS) for i in recipe.lines},
        'steps': {s.local_id: _filled(s, STEP_FIELDS) for s in recipe.steps},
    }


def source_hash(text):
    """The same words give the same hash, whatever order they were read in."""
    return hashlib.sha256(json.dumps(text, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def problems(original, translated, where=''):
    """What is wrong with a translation of source()'s text, one line each; empty when it can be saved."""
    if isinstance(original, dict):
        if not isinstance(translated, dict):
            return [f'{where or "text"}: missing']
        found = [p for key, value in original.items()
                 for p in problems(value, translated.get(key), f'{where}.{key}' if where else key)]
        return found + [f'{where}.{key}: not in the recipe' if where else f'{key}: not in the recipe'
                        for key in translated.keys() - original.keys()]
    if not isinstance(translated, str) or not translated.strip():
        return [f'{where}: missing']
    if set(PLACEHOLDER.findall(original)) != set(PLACEHOLDER.findall(translated)):
        return [f'{where}: other placeholders than the original']
    return []


def _translates(recipe, code):
    """Whether a reader of this language gets a translation of this recipe at all."""
    return code != DEFAULT and code != (recipe.language or DEFAULT)


def save(recipe, code, translated):
    """Keep a translation of source(recipe) for this language, in place of an earlier one. Raises ValueError on one
    that cannot be shown. The caller commits."""
    code = language.recipe_code(code)
    if not _translates(recipe, code):
        raise ValueError(f'recipe {recipe.id} does not take a translation to {code}')
    original = source(recipe)
    wrong = problems(original, translated)
    if wrong:
        raise ValueError(f'recipe {recipe.id} in {code}: ' + '; '.join(wrong))
    row = db.session.get(RecipeTranslation, (recipe.id, code))
    if row is None:
        row = RecipeTranslation(recipe_id=recipe.id, language=code)
        db.session.add(row)
    row.title, row.source_title = translated['title'], recipe.title
    row.texts = {k: v for k, v in translated.items() if k != 'title'}
    row.source_hash = source_hash(original)
    row.created_at = datetime.datetime.now(datetime.UTC).replace(tzinfo=None)
    return row


def of(recipe, code=None):
    """The translation to show this reader, {'language', 'title', 'chef_note', 'components', …}, or None for the text
    as written. Reads the recipe's graph."""
    code = language.recipe_code(code)
    if not _translates(recipe, code):
        return None
    row = db.session.get(RecipeTranslation, (recipe.id, code))
    if row is None or row.source_hash != source_hash(source(recipe)):
        return None
    return {**row.texts, 'title': row.title, 'language': code}


def apply(v2, text):
    """Lay of()'s text over to_v2()'s JSON, field by field: what it does not have stays as written."""
    if not text:
        return v2
    v2['title'] = text['title']
    for rows, key in ((v2['components'], 'components'), (v2['ingredients'], 'lines'), (v2['steps'], 'steps')):
        words = text.get(key) or {}
        for row in rows:
            row.update(words.get(row['local_id']) or {})
    return v2


def titles(recipes, code=None):
    """{recipe id: translated title} for the recipes that have one, in one query. None when the language needs none."""
    code = language.recipe_code(code)
    wanted = {r.id: r.title for r in recipes if _translates(r, code)}
    if not wanted:
        return {}
    rows = db.session.execute(db.select(RecipeTranslation.recipe_id, RecipeTranslation.title, RecipeTranslation.source_title)
                              .where(RecipeTranslation.language == code, RecipeTranslation.recipe_id.in_(wanted)))
    return {rid: title for rid, title, written in rows if wanted[rid] == written}


def dress(recipes):
    """Give each recipe its shown_title for this reader, which components/cards.html shows."""
    found = titles(recipes)
    for r in recipes:
        r.shown_title = found.get(r.id, r.title)
    return recipes


def title_of(recipe):
    return titles([recipe]).get(recipe.id, recipe.title)


def ingredient_name(ingredient):
    """A pantry item's name for this reader: anything with name and name_nb, an Ingredient or a row of them."""
    return (language.recipe_code() == 'nb' and ingredient.name_nb) or ingredient.name
