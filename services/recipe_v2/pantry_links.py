"""What links recipe lines to pantry items without Pål having seen it (04.11.2026). Until #292 the pantry job could alias
a line to "what a shopper would buy in its place", and an alias holds for every recipe. Until the fix after it, the
structuring model could link a line to the nearest item by itself. Both leave a line with one food's name and another's
nutrition and symbol.

The report has two parts, and costs nothing (no AI): the aliases the pantry job made, with its reason and how many lines
use them, and the lines linked to an item their name does not match. It only reads. It is here rather than in
scripts/pantry_links.py because scripts/ is not in the production image, and /api/review/pantry-report needs it.
"""
import re

NOTE = re.compile(r'^"(?P<line>.+)" is now an alias of (?P<item>.+) \((?P<reason>.*)\)$')


def job_aliases(recipes):
    """{alias name: (item, reason)} from the pantry job's notes on the recipes."""
    found = {}
    for recipe in recipes:
        for note in recipe.validation_errors or []:
            m = NOTE.match(note.get('message') or '') if note.get('rule') == 'pantry' else None
            if m:
                found.setdefault(m['line'].strip().lower(), (m['item'], m['reason']))
    return found


def report(recipes, aliases):
    """The report as lines of text. aliases is every IngredientAlias row. The matcher prints every miss."""
    import ai_engine
    from services.pantry_service import get_slim_pantry_context
    from services.recipe_v2.generate import match_pantry

    # A running app fills the matcher's map once; the report is about the pantry of now
    ai_engine.set_pantry_memory(get_slim_pantry_context())
    lines = [line for recipe in recipes for line in recipe.lines]
    uses = {}
    for line in lines:
        key = line.name.strip().lower()
        uses.setdefault(key, []).append(line)
    made = job_aliases(recipes)
    out = [f'{len(recipes)} recipes, {len(lines)} lines, {len(aliases)} aliases, {len(made)} of them noted as made by the pantry job.', '']
    out.append('ALIASES THE PANTRY JOB MADE (name -> item: lines, reason)')
    for alias in sorted(aliases, key=lambda a: a.name):
        if alias.name in made:
            out.append(f'- {alias.name} -> {alias.ingredient.name}: {len(uses.get(alias.name, []))} lines, {made[alias.name][1]}')

    names = {key: group[0].name for key, group in uses.items()}
    by_name, _ = match_pantry({'ingredients': [{'local_id': key, 'name': name} for key, name in names.items()]})
    silent = {}
    for key, group in uses.items():
        for line in group:
            if line.ingredient_id and by_name.get(key) != line.ingredient_id:
                silent.setdefault((key, line.ingredient.name), []).append(line.recipe_id)
    out += ['', 'LINES LINKED TO AN ITEM THEIR NAME DOES NOT MATCH (name -> item: recipes)']
    for (key, item), ids in sorted(silent.items()):
        out.append(f'- {key} -> {item}: {", ".join(map(str, sorted(set(ids))))}')
    return out
