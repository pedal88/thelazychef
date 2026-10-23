"""Chef personas in v2 generation: the spec in the prompt, and the hard rules checked afterwards.

A persona (the chef table, seeded from data/agents/chefs.json) is a spec for a
user segment. Its soft side (description, methods, staples, tone) goes into the
round 1 prompt. Its hard side, `constraints`, is checked on the saved recipe:

    max_total_minutes   planned total time (recipe.prep_time_mins)
    max_active_minutes  planned hands-on time (the planner's A)
    max_cleanup         derived clean-up, 1-5
    max_spice           spice_level from the model, 0-3
    difficulties        allowed difficulty values
    diet                "vegetarian" or "vegan": no meat or fish lines (vegan: no dairy or egg either)
    max_carbs_per_serving   carbohydrate per serving, when the recipe has nutrition (services/recipe_v2/nutrition.py)
    max_ingredients     ingredients besides the staples (pantry tier 'staple')
    max_extra           ingredients outside the foundation pantry and the staples

and two that only steer the writing: forms (fresh or shortcut herbs, garlic and ginger) and ready_made.

A chef is a philosophy; settings go on top of any chef and are stored on the recipe (SETTINGS, with_settings):
vegetarian, kid_friendly, low_carb and baby (RECIPE_MODEL_V2.md, "Kokker og innstillinger"). Baby has age stages
(data/constraints/age_stages.json): the recipe stores the stage's age in recipe.age_from_months, and the stage
sets the texture and what to leave out.

A broken rule does not stop the recipe; it is noted and the recipe flagged for review.
"""
import copy
import json
import os
from functools import lru_cache

from services.chef_service import chef_to_dict

ANIMAL = {'meat', 'fish and seafood'}
NOT_VEGAN = ANIMAL | {'dairy and egg'}
STAPLE_WORDS = 'salt, pepper, oil, water, sugar and flour'
# setting: (label, what it adds to the rules, what it asks of the writing)
SETTINGS = {
    'vegetarian': ('Vegetarian', {'diet': 'vegetarian'}, 'Vegetarian: no meat or fish; build the dish on vegetables, '
                   'beans, lentils, eggs or cheese so it is a full meal.'),
    'kid_friendly': ('Kid-friendly', {'max_spice': 1}, 'For children: mild, familiar flavours; vegetables in pieces '
                     'they recognise or hidden in the sauce; chili and strong herbs go on the table, not in the pot.'),
    'low_carb': ('Low carb', {'max_carbs_per_serving': 20}, 'Low carb: about 20 g of carbohydrate a serving at most. '
                 'Swap the starch (cauliflower rice, courgette noodles, lettuce wraps); keep protein, vegetables and good fats.'),
    # The writing and the rules beyond max_spice come from the age stage (stage_for)
    'baby': ('Baby', {'max_spice': 0}, ''),
}
FORMS = {
    'fresh': 'Use fresh herbs, fresh garlic and fresh ginger.',
    'balanced': 'Fresh herbs, garlic and ginger where they are eaten raw or as a garnish; dried, jarred or frozen is fine where they are cooked in.',
    'shortcut': 'Dried herbs, garlic and ginger from a jar or tube, and frozen herbs and vegetables are fine, except where they are eaten raw or as a garnish.',
}
READY_MADE = {
    'good': 'Use a ready-made product when it is as good as homemade (tinned tomatoes, stock cubes, curry paste).',
    'welcome': 'Ready-made sauces, spice mixes and pre-cut or frozen vegetables are welcome.',
}


@lru_cache(maxsize=1)
def age_stages():
    path = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'constraints', 'age_stages.json')
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def stage_for(months):
    """The baby age stage for a recipe's age_from_months: the oldest stage that is not older than it. Without an
    age, the youngest stage, the strictest."""
    stages = sorted(age_stages()['stages'], key=lambda s: s['from_months'])
    fits = [s for s in stages if months is not None and s['from_months'] <= months]
    return fits[-1] if fits else stages[0]


def age_label(recipe):
    """'Baby, 8 months+' for a recipe made with the Baby setting; None otherwise."""
    if 'baby' not in (recipe.settings or []):
        return None
    return f"Baby, {stage_for(recipe.age_from_months)['label']}"


def spec(chef, settings=None, age_from_months=None):
    """The chef row as a dict (constraints and the rest parsed), with the settings on top; None when there is neither.
    Carries the foundation pantry when a rule needs it. age_from_months picks the stage of the Baby setting."""
    p = with_settings(chef_to_dict(chef) if chef is not None else None, settings, age_from_months)
    if p and (p.get('constraints') or {}).get('max_extra') is not None:
        p['foundation'] = foundation_names()
    return p


def spec_for(recipe):
    """The persona a saved recipe was written with: its chef when the chef wrote it, and its settings."""
    from services.recipe_v2.generate import PERSONA_KINDS
    from database.models import Chef, db

    chef = db.session.get(Chef, recipe.chef_id) if recipe.chef_id and recipe.source_type in PERSONA_KINDS else None
    settings = recipe.settings if recipe.source_type in PERSONA_KINDS else None
    return spec(chef, settings, getattr(recipe, 'age_from_months', None))


def with_settings(p, settings, age_from_months=None):
    """The persona with the settings added: their rules tighten the chef's, their notes go into the prompt.
    Without a chef, the settings alone. Unknown settings are ignored. Baby adds its age stage as p['baby']."""
    settings = [k for k in settings or [] if k in SETTINGS]
    if not settings:
        return p
    p = copy.deepcopy(p) if p else {'name': '', 'constraints': {}}
    rules = p.setdefault('constraints', {})
    for key in settings:
        for rule, value in SETTINGS[key][1].items():
            if rule == 'diet':
                rules['diet'] = 'vegan' if rules.get('diet') == 'vegan' else value
            else:
                rules[rule] = value if rules.get(rule) is None else min(rules[rule], value)
    p['settings'] = settings
    if 'baby' in settings:
        p['baby'] = stage_for(age_from_months)
    return p


def foundation_names():
    """The foundation pantry and the staples, by name."""
    from database.models import Ingredient, db

    return sorted(n for (n,) in db.session.execute(db.select(Ingredient.name).where(
        Ingredient.tier.in_(('foundation', 'staple')), Ingredient.status == 'active')).all())


def prompt_block(p):
    """The persona as text for the round 1 prompt. Empty without a persona."""
    if not p:
        return ''
    rules = p.get('constraints') or {}
    style = p.get('cooking_style') or {}
    logic = p.get('ingredient_logic') or {}
    voice = p.get('instruction_style') or {}
    lines = [f"Write it as {p['name']} ({p.get('archetype') or 'chef'}): {p.get('description') or ''}".strip()] if p.get('name') else []
    hard = []
    if rules.get('max_total_minutes'):
        hard.append(f"the whole recipe takes at most {rules['max_total_minutes']} minutes from start to table for one cook"
                    ", counting all the chopping and preparation, preheating the oven and bringing water to the boil; "
                    "plan the dish so that this holds")
    if rules.get('max_active_minutes'):
        hard.append(f"at most {rules['max_active_minutes']} minutes of hands-on work; the rest is time the food cooks by itself")
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
    if rules.get('max_ingredients'):
        hard.append(f"at most {rules['max_ingredients']} ingredients besides {STAPLE_WORDS}")
    if rules.get('max_extra') is not None:
        hard.append(f"at most {rules['max_extra']} ingredients that are not in the FOUNDATION list below; "
                    "use the foundation ingredient whenever it does the job")
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
    if logic.get('strategy') or logic.get('low_carb_strategy'):
        lines.append('Approach: ' + (logic.get('strategy') or logic['low_carb_strategy']))
    if rules.get('forms') in FORMS:
        lines.append(FORMS[rules['forms']])
    if rules.get('ready_made') in READY_MADE:
        lines.append(READY_MADE[rules['ready_made']])
    for key in p.get('settings') or []:
        if SETTINGS[key][2]:
            lines.append(SETTINGS[key][2])
    if p.get('baby'):
        lines.append(f"{age_stages()['common']['writing']} {p['baby']['writing']}")
    if voice.get('tone'):
        tip = f" Example: \"{voice['example_phrase']}\"" if voice.get('example_phrase') else ''
        lines.append(f"Write the tip from the cook in this voice: {voice['tone']}{tip}")
    if p.get('foundation'):
        lines.append('FOUNDATION (what the cook is assumed to have or buy anyway): ' + ', '.join(p['foundation']))
    return '\n'.join(lines)


def check(recipe, p):
    """Hard rules the saved recipe breaks, as messages. [] when it keeps them all or has no persona."""
    if not p:
        return []
    rules = p.get('constraints') or {}
    who = p.get('name') or 'The settings'
    p = dict(p, name=who)
    notes = []
    if rules.get('max_ingredients') or rules.get('max_extra') is not None:
        used, extra = ingredients_of(recipe)
        if rules.get('max_ingredients') and len(used) > rules['max_ingredients']:
            notes.append(f"Uses {len(used)} ingredients besides the staples; {who} uses at most {rules['max_ingredients']}.")
        if rules.get('max_extra') is not None and len(extra) > rules['max_extra']:
            notes.append(f"Needs {len(extra)} ingredients outside the foundation pantry ({', '.join(extra)}); "
                         f"{who} allows {rules['max_extra']}.")
    if rules.get('max_active_minutes'):
        active = active_minutes(recipe)
        if active is not None and active > rules['max_active_minutes']:
            notes.append(f"Takes {active} minutes of hands-on work; {who} allows {rules['max_active_minutes']}.")
    if rules.get('max_total_minutes') and (recipe.prep_time_mins or 0) > rules['max_total_minutes']:
        notes.append(f"Takes {recipe.prep_time_mins} minutes; {p['name']} allows {rules['max_total_minutes']}.")
    if rules.get('max_cleanup') and (recipe.cleanup_factor or 0) > rules['max_cleanup']:
        notes.append(f"Clean-up is {recipe.cleanup_factor} of 5; {p['name']} allows {rules['max_cleanup']}.")
    if rules.get('max_spice') is not None and (recipe.spice_level or 0) > rules['max_spice']:
        notes.append(f"Spice level is {recipe.spice_level}; {p['name']} allows {rules['max_spice']}.")
    carbs = getattr(recipe, 'total_carbs', None)
    if rules.get('max_carbs_per_serving') and carbs is not None:
        per = carbs / (getattr(recipe, 'base_servings', None) or 1)
        if per > rules['max_carbs_per_serving']:
            notes.append(f"About {per:.0f} g carbs a serving; {p['name']} allows {rules['max_carbs_per_serving']}.")
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
    if p.get('baby'):
        notes += baby_notes(recipe, p['baby'])
    return notes


def _has(names, rule):
    return any(w in n for n in names for w in rule['words']) and not any(w in n for n in names for w in rule.get('except', []))


def baby_notes(recipe, stage):
    """What the recipe has that a baby of the stage's age should not get, line by line (age_stages.json)."""
    cat = age_stages()
    rules = [cat['avoid'][key] for key in stage['avoid']] + ([cat['salty']] if stage.get('no_salt') else [])
    out = []
    for rule in rules:
        hits = []
        for line in recipe.lines:
            names = [line.name.lower()] + ([line.ingredient.name.lower()] if line.ingredient is not None else [])
            if _has(names, rule) and line.name not in hits:
                hits.append(line.name)
        if hits:
            out.append(f"For a baby {stage['label']}: {', '.join(hits)}; {rule['why']}.")
    return out


def active_minutes(recipe):
    """Planned hands-on minutes: given on the recipe (tests), or from the planner. None when it cannot be planned."""
    if getattr(recipe, 'active_mins', None) is not None:
        return recipe.active_mins
    try:
        from services.recipe_v2.planner import plan_v2
        from services.recipe_v2.store import to_v2

        return plan_v2(to_v2(recipe))['A']
    except Exception:
        return None


def ingredients_of(recipe):
    """(ingredients besides the staples, those of them outside the foundation pantry), by name, each once.
    A line not in the pantry counts as outside; a staple is known by its tier, or by name when not in the pantry."""
    from services.recipe_v2.mise import STAPLES

    used, extra = {}, {}
    for line in recipe.lines:
        ing = line.ingredient
        tier = getattr(ing, 'tier', None)
        name = (ing.name if ing is not None else line.name).strip().lower()
        if tier == 'staple' or (ing is None and name in STAPLES):
            continue
        used[name] = True
        if tier != 'foundation':
            extra[name] = True
    return list(used), list(extra)


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
    if rules.get('max_ingredients'):
        out.append(f"{rules['max_ingredients']} ingredients or fewer")
    levels = rules.get('difficulties') or []
    if 0 < len(levels) < 3:
        out.append(' or '.join({'Simplistic': 'Easy', 'Moderate': 'Medium', 'Elevated': 'Challenging'}.get(d, d) for d in levels))
    return out
