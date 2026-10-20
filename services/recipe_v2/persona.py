"""Chef personas in v2 generation: the spec in the prompt, and the hard rules checked afterwards.

A persona (the chef table, seeded from data/agents/chefs.json) is a spec for a
user segment. Its soft side (description, methods, staples, tone) goes into the
round 1 prompt. Its hard side, `constraints`, is checked on the saved recipe:

    max_total_minutes   planned total time (recipe.prep_time_mins)
    max_cleanup         derived clean-up, 1-5
    max_spice           spice_level from the model, 0-3
    difficulties        allowed difficulty values
    diet                "vegetarian" or "vegan": no meat or fish lines (vegan: no dairy or egg either)
    max_carbs_per_serving   not checked until v2 has nutrition

A broken rule does not stop the recipe; it is noted and the recipe flagged for review.
"""
from services.chef_service import chef_to_dict

ANIMAL = {'meat', 'fish and seafood'}
NOT_VEGAN = ANIMAL | {'dairy and egg'}


def spec(chef):
    """The chef row as a dict (constraints and the rest parsed), or None."""
    return chef_to_dict(chef) if chef is not None else None


def prompt_block(p):
    """The persona as text for the round 1 prompt. Empty without a persona."""
    if not p:
        return ''
    rules = p.get('constraints') or {}
    style = p.get('cooking_style') or {}
    logic = p.get('ingredient_logic') or {}
    voice = p.get('instruction_style') or {}
    lines = [f"Write it as {p['name']} ({p.get('archetype') or 'chef'}): {p.get('description') or ''}".strip()]
    hard = []
    if rules.get('max_total_minutes'):
        hard.append(f"the whole recipe takes at most {rules['max_total_minutes']} minutes from start to table")
    if rules.get('diet') == 'vegan':
        hard.append('no meat, fish, dairy or eggs')
    elif rules.get('diet') == 'vegetarian':
        hard.append('no meat or fish (dairy and eggs are fine)')
    if rules.get('max_spice') is not None and rules['max_spice'] < 3:
        hard.append(('no chili heat' if rules['max_spice'] == 0 else 'at most mildly hot') + '; chili can be served on the side')
    if rules.get('max_cleanup') and rules['max_cleanup'] <= 2:
        hard.append('as few pots, pans and bowls as possible')
    if rules.get('max_carbs_per_serving'):
        hard.append(f"at most about {rules['max_carbs_per_serving']} g of carbohydrate per serving")
    if logic.get('banned_ingredients'):
        hard.append('never use ' + ', '.join(logic['banned_ingredients']))
    if hard:
        lines.append('Rules: ' + '; '.join(hard) + '.')
    if rules.get('difficulties') and len(rules['difficulties']) < 3:
        level = {'Simplistic': 'easy', 'Moderate': 'medium', 'Elevated': 'demanding'}
        lines.append('Difficulty: ' + ' or '.join(level.get(d, d) for d in rules['difficulties']) + ' for a home cook.')
    if style.get('preferred_methods'):
        lines.append('Prefer these techniques when they suit the dish: ' + ', '.join(style['preferred_methods']).replace('_', ' ') + '.')
    if style.get('avoid_methods'):
        lines.append('Avoid: ' + ', '.join(style['avoid_methods']).replace('_', ' ') + '.')
    if logic.get('staples'):
        lines.append('Typical ingredients: ' + ', '.join(logic['staples']) + '.')
    if logic.get('low_carb_strategy'):
        lines.append('Approach: ' + logic['low_carb_strategy'])
    if voice.get('tone'):
        tip = f" Example: \"{voice['example_phrase']}\"" if voice.get('example_phrase') else ''
        lines.append(f"Write the tip from the cook in this voice: {voice['tone']}{tip}")
    return '\n'.join(lines)


def check(recipe, p):
    """Hard rules the saved recipe breaks, as messages. [] when it keeps them all or has no persona."""
    if not p:
        return []
    rules = p.get('constraints') or {}
    notes = []
    if rules.get('max_total_minutes') and (recipe.prep_time_mins or 0) > rules['max_total_minutes']:
        notes.append(f"Takes {recipe.prep_time_mins} minutes; {p['name']} allows {rules['max_total_minutes']}.")
    if rules.get('max_cleanup') and (recipe.cleanup_factor or 0) > rules['max_cleanup']:
        notes.append(f"Clean-up is {recipe.cleanup_factor} of 5; {p['name']} allows {rules['max_cleanup']}.")
    if rules.get('max_spice') is not None and (recipe.spice_level or 0) > rules['max_spice']:
        notes.append(f"Spice level is {recipe.spice_level}; {p['name']} allows {rules['max_spice']}.")
    if rules.get('difficulties') and recipe.difficulty and recipe.difficulty not in rules['difficulties']:
        notes.append(f"Difficulty is {recipe.difficulty}; {p['name']} makes {', '.join(rules['difficulties'])}.")
    if rules.get('diet') in ('vegetarian', 'vegan'):
        banned = NOT_VEGAN if rules['diet'] == 'vegan' else ANIMAL
        found = [line.name for line in recipe.lines if line.ingredient is not None and line.ingredient.main_category in banned]
        if found:
            notes.append(f"Not {rules['diet']}: {', '.join(found)}.")
    words = [w.lower() for w in (p.get('ingredient_logic') or {}).get('banned_ingredients') or []]
    hits = [line.name for line in recipe.lines
            if any(w in line.name.lower() or (line.ingredient is not None and w in line.ingredient.name.lower()) for w in words)]
    if hits:
        notes.append(f"Uses ingredients {p['name']} never uses: {', '.join(hits)}.")
    return notes


def badges(p):
    """The hard rules in a few reader-facing words, for the persona pages."""
    rules = p.get('constraints') or {}
    out = []
    if rules.get('max_total_minutes'):
        out.append(f"Under {rules['max_total_minutes']} minutes")
    if rules.get('diet'):
        out.append(rules['diet'].capitalize())
    if rules.get('max_carbs_per_serving'):
        out.append(f"About {rules['max_carbs_per_serving']} g carbs a serving")
    if rules.get('max_spice') is not None and rules['max_spice'] <= 1:
        out.append('Mild')
    if rules.get('max_cleanup') and rules['max_cleanup'] <= 3:
        out.append('Little washing-up')
    levels = rules.get('difficulties') or []
    if 0 < len(levels) < 3:
        out.append(' or '.join({'Simplistic': 'Easy', 'Moderate': 'Medium', 'Elevated': 'Challenging'}.get(d, d) for d in levels))
    return out
