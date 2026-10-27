"""Save a v2 recipe (validator JSON) to the database, and read it back.

The JSON uses local ids ("c1", "i3", "s2") for references. In the database
they become foreign keys; the local ids are kept, because step text refers to
lines as {i3}.
"""
import datetime

from database.models import Recipe, RecipeComponent, RecipeLine, RecipeMealType, RecipeStep, db

STEP_FIELDS = ('phase', 'short', 'verb', 'text', 'active_minutes', 'passive_minutes', 'holds_minutes', 'method',
               'temp_c', 'mode', 'done_when')
LINE_FIELDS = ('name', 'amount', 'unit', 'prep_style', 'state', 'grade', 'variety')


def save_v2(recipe: Recipe, data: dict, ingredient_ids: dict | None = None) -> Recipe:
    """Replace the recipe's v2 content with data and set schema_version 2.

    ingredient_ids maps line local_id to a pantry ingredient id. Lines without
    one are stored without a pantry link. The caller commits. data must already
    pass the validator: references are looked up, not checked.
    """
    ingredient_ids = ingredient_ids or {}
    had_content = bool(recipe.steps)
    # Lines point at steps, and steps at components: remove them in that order.
    for children in (recipe.lines, recipe.steps, recipe.components):
        children.clear()
        db.session.flush()

    comps = {}
    for n, c in enumerate(data['components']):
        comps[c['local_id']] = RecipeComponent(local_id=c['local_id'], name=c['name'], sort_order=n)
        recipe.components.append(comps[c['local_id']])

    steps = {}
    for n, s in enumerate(data['steps']):
        step = RecipeStep(local_id=s['local_id'], sort_order=n, component=comps[s['component_id']],
                          equipment=list(s.get('equipment') or []), setup=bool(s.get('setup')),
                          **{k: s.get(k) for k in STEP_FIELDS})
        steps[s['local_id']] = step
        recipe.steps.append(step)
    for s in data['steps']:
        steps[s['local_id']].after = [steps[a] for a in s.get('after') or []]

    used_by = {u: s['local_id'] for s in data['steps'] for u in s.get('uses') or []}
    for n, i in enumerate(data['ingredients']):
        recipe.lines.append(RecipeLine(
            local_id=i['local_id'], sort_order=n, component=comps[i['component_id']], step=steps[used_by[i['local_id']]],
            ingredient_id=ingredient_ids.get(i['local_id']), gram_weight=i.get('gram_weight_estimate'),
            **{k: i.get(k) for k in LINE_FIELDS}))

    recipe.title = data.get('title') or recipe.title
    recipe.base_servings = data.get('servings') or recipe.base_servings
    recipe.chef_note = data.get('chef_note')
    # Cuisine, difficulty and meal types fill the same fields as the old recipes, so lists and filters work for both.
    if data.get('cuisine'):
        recipe.cuisine = data['cuisine']
    if data.get('difficulty'):
        recipe.difficulty = data['difficulty']
    if 'meal_types' in data:
        existing = {m.meal_type: m for m in recipe.meal_types}
        recipe.meal_types = [existing.get(m) or RecipeMealType(meal_type=m) for m in dict.fromkeys(data['meal_types'] or [])]
    for key in ('spice_level', 'keeps_days', 'freezes'):
        if key in data:
            setattr(recipe, key, data[key])
    recipe.schema_version = 2
    if had_content:
        recipe.revision = (recipe.revision or 1) + 1
    recipe.revised_at = datetime.datetime.now(datetime.UTC).replace(tzinfo=None)
    return recipe


def to_v2(recipe: Recipe) -> dict:
    """The recipe as validator JSON. uses follows the order of the lines."""
    def drop_none(d):
        return {k: v for k, v in d.items() if v is not None}

    return {
        'title': recipe.title,
        'servings': recipe.base_servings,
        **({'chef_note': recipe.chef_note} if recipe.chef_note else {}),
        **({'cuisine': recipe.cuisine} if recipe.cuisine else {}),
        **({'difficulty': recipe.difficulty} if recipe.difficulty else {}),
        **({'meal_types': recipe.meal_types_list} if recipe.meal_types else {}),
        **{k: getattr(recipe, k) for k in ('spice_level', 'keeps_days', 'freezes') if getattr(recipe, k) is not None},
        'components': [{'local_id': c.local_id, 'name': c.name} for c in recipe.components],
        'ingredients': [drop_none({
            'local_id': i.local_id, 'component_id': i.component.local_id, 'name': i.name, 'amount': i.amount,
            'unit': i.unit, 'prep_style': i.prep_style, 'state': i.state, 'grade': i.grade,  # not the old cut: see below
            'variety': i.variety, 'gram_weight_estimate': i.gram_weight,
            'pantry_id': i.ingredient.food_id if i.ingredient else None,
        }) for i in recipe.lines],  # The state is the line's only state. The old cut column, from before the state
                                     # catalog, was converted where it was right (scripts/convert_states.py); where it
                                     # was not (salt "chopped" by its step), it must not show.
        'steps': [drop_none({
            'local_id': s.local_id, 'component_id': s.component.local_id,
            'uses': [i.local_id for i in sorted(s.lines, key=lambda i: i.sort_order)],
            'after': [a.local_id for a in s.after], 'equipment': list(s.equipment or []), 'setup': s.setup,
            **{k: getattr(s, k) for k in STEP_FIELDS},
        }) for s in recipe.steps],
    }
