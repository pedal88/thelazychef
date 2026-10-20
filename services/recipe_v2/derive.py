"""Metadata derived from a saved v2 recipe, so the model is not asked for it.

heat source, main protein, clean-up, one-pot and total time follow from the
steps, their equipment and the pantry. They are set after save_v2() and fill
the same Recipe fields the old recipes use (protein_type, cleanup_factor,
prep_time_mins), so the list cards and filters work for both.
"""
from database.models import RecipeMealType
from services.recipe_v2.planner import plan_v2

# Heat source -> equipment ids whose heat counts for it. A step counts by its first equipment (where it happens).
HEAT_SOURCES = {
    'pan': ('frying_pan', 'wok', 'grill_pan'),
    'pot': ('saucepan', 'large_pot', 'wide_pot', 'dutch_oven', 'steamer', 'deep_fryer'),
    'oven': ('oven', 'baking_tray', 'roasting_pan', 'ovenproof_dish', 'form_20x20', 'form_20x30', 'springform_24',
             'loaf_tin', 'muffin_tin', 'pie_dish'),
    'grill': ('grill', 'skewers'),
    'airfryer': ('airfryer',),
    'slow_cooker': ('slow_cooker',),
    'microwave': ('microwave',),
    'sous_vide': ('sous_vide',),
}
HEAT_LABELS = {'pan': 'Frying pan or wok', 'pot': 'Pot', 'oven': 'Oven', 'grill': 'Grill', 'airfryer': 'Air fryer',
               'slow_cooker': 'Slow cooker', 'microwave': 'Microwave', 'sous_vide': 'Sous vide', 'none': 'No heat'}
_SOURCE_OF = {eq: source for source, eqs in HEAT_SOURCES.items() for eq in eqs}

# Clean-up counts vessels to wash: pots, pans, forms, bowls and machine parts. Small tools (whisk, grater, ladle)
# and appliances that are not washed (oven, microwave, grill) do not count.
VESSELS = {'airfryer', 'grill_pan', 'saucepan', 'large_pot', 'wide_pot', 'dutch_oven', 'frying_pan', 'wok', 'steamer',
           'deep_fryer', 'slow_cooker', 'baking_tray', 'roasting_pan', 'ovenproof_dish', 'form_20x20', 'form_20x30',
           'springform_24', 'loaf_tin', 'muffin_tin', 'pie_dish', 'bowl', 'small_bowl', 'large_bowl', 'sieve', 'colander',
           'mortar', 'blender', 'food_processor', 'stand_mixer', 'salad_spinner', 'jar', 'measuring_jug'}

# Main protein: pantry sub_category -> the label the protein filter uses (data/constraints/main_protein.json).
MEAT_LABELS = {'beef': 'Beef', 'chicken': 'Chicken', 'poultry': 'Chicken', 'lamb': 'Lamb', 'goat': 'Lamb', 'pork': 'Pork',
               'sausages': 'Pork', 'reindeer': 'Game', 'game': 'Game', 'salmon': 'Salmon', 'fish': 'White Fish',
               'shrimps': 'Shrimp', 'scampi': 'Shrimp', 'lobster': 'Shellfish', 'shellfish': 'Shellfish'}
# Plant and egg proteins, by name. Only used when there is no meat or fish.
OTHER_PROTEINS = (('tofu', 'Tofu'), ('tempeh', 'Tempeh'), ('seitan', 'Seitan'), ('halloumi', 'Halloumi'),
                  ('lentil', 'Lentils'), ('chickpea', 'Legumes'), ('bean', 'Beans'), ('egg', 'Eggs'))
ANIMAL = ('meat', 'fish and seafood')

# Tags in data/constraints/meal_types.json that the app sets, never the model.
DERIVED_TAGS = ('One-Pot', 'Freezer Friendly', 'Slow Cooker')


def heat_steps(v2):
    return [s for s in v2['steps'] if not s.get('setup') and s.get('method') != 'preheat'
            and (s.get('equipment') or [None])[0] in _SOURCE_OF]


def main_line(v2):
    """Steps on the path to the final step with the most active time, from the start to the dish."""
    by = {s['local_id']: s for s in v2['steps']}
    used = {a for s in v2['steps'] for a in s.get('after') or []}
    final = next((s for s in reversed(v2['steps']) if s['local_id'] not in used and (s.get('uses') or s.get('after'))), None)
    best = {}

    def path(sid):
        if sid not in best:
            s = by[sid]
            prev = max((path(a) for a in s.get('after') or [] if a in by),
                       key=lambda p: sum(by[x].get('active_minutes') or 0 for x in p), default=[])
            best[sid] = prev + [sid]
        return best[sid]
    return [by[x] for x in path(final['local_id'])] if final else []


def heat_source(v2):
    """What the dish is finished in: the heat source of the last heat step on the main line.

    A lasagne is an oven dish even if the meat sauce simmers longer than it bakes. Falls back to the heat
    source with the most minutes when the main line has no heat, and 'none' for a dish without heat."""
    heated = {s['local_id'] for s in heat_steps(v2)}
    last = next((s for s in reversed(main_line(v2)) if s['local_id'] in heated), None)
    if last:
        return _SOURCE_OF[last['equipment'][0]]
    minutes = {}
    for s in heat_steps(v2):
        source = _SOURCE_OF[s['equipment'][0]]
        minutes[source] = minutes.get(source, 0) + (s.get('active_minutes') or 0) + (s.get('passive_minutes') or 0)
    return max(minutes, key=minutes.get) if minutes else 'none'


def one_pot(v2):
    """Everything with heat happens in one vessel."""
    return len({s['equipment'][0] for s in heat_steps(v2)}) == 1


def cleanup_factor(v2):
    """1 (one or two vessels) to 5 (eight or more), from the vessels to wash."""
    n = len({e for s in v2['steps'] for e in s.get('equipment') or []} & VESSELS)
    return 1 if n <= 2 else 2 if n == 3 else 3 if n <= 5 else 4 if n <= 7 else 5


def main_protein(lines):
    """Label of the heaviest meat or fish line, else of the heaviest plant or egg protein, else None."""
    best = {}  # kind -> (grams, label)
    for line in lines:
        ing = line.ingredient
        if ing is None:
            continue
        grams = line.gram_weight or 0
        if ing.main_category in ANIMAL:
            label = MEAT_LABELS.get((ing.sub_category or '').lower(), 'Other')
            kind = 'animal'
        else:
            label = next((lab for word, lab in OTHER_PROTEINS if word in ing.name.lower()), None)
            kind = 'other'
        if label and grams >= best.get(kind, (-1, None))[0]:
            best[kind] = (grams, label)
    return (best.get('animal') or best.get('other') or (0, None))[1]


def apply(recipe, v2):
    """Set the derived fields on recipe. v2 is the recipe as saved (store.to_v2)."""
    recipe.heat_source = heat_source(v2)
    recipe.protein_type = main_protein(recipe.lines)
    recipe.cleanup_factor = cleanup_factor(v2)
    recipe.prep_time_mins = plan_v2(v2)['T']
    tags = [m.meal_type for m in recipe.meal_types if m.meal_type not in DERIVED_TAGS]
    tags += [tag for tag, yes in (('One-Pot', one_pot(v2)), ('Freezer Friendly', bool(recipe.freezes)),
                                  ('Slow Cooker', recipe.heat_source == 'slow_cooker')) if yes]
    set_meal_types(recipe, tags)
    return recipe


def set_meal_types(recipe, tags):
    """Replace the tags, keeping the rows that stay (meal_type is part of the primary key)."""
    existing = {m.meal_type: m for m in recipe.meal_types}
    recipe.meal_types = [existing.get(t) or RecipeMealType(meal_type=t) for t in dict.fromkeys(tags)]
