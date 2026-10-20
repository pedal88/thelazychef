"""chef personas for v2

The four chef personas get hard rules instead of the old 1-5 sliders, and two
new ones are added: The Family Cook and The Green Chef (data/agents/chefs.json,
services/recipe_v2/persona.py). The Meta-Learner no longer builds on a real
person's books and trademarks, the Low Carb Chef drops the seed-oil claim, and
The French Classic prefers braising and searing over blending and sous vide.

A persona is only updated when it is exactly as it was seeded, so edits made in
/admin/chefs are kept; those chefs are printed and left alone. The two new
chefs are inserted when missing. Downgrade puts the updated chefs back as they
were seeded and deletes the two new ones when no recipe uses them.

Revision ID: a4d9c2f7e61b
Revises: 3b8f2d61a7c5
Create Date: 2026-10-20

"""
import json

from alembic import op
import sqlalchemy as sa


revision = 'a4d9c2f7e61b'
down_revision = '3b8f2d61a7c5'
branch_labels = None
depends_on = None

JSON_FIELDS = ('constraints', 'diet_preferences', 'cooking_style', 'ingredient_logic', 'instruction_style')
ADDED = ('family_cook', 'the_green_chef')

OLD = {'french_classic': {'name': 'The French Classic',
                    'archetype': 'The Old School',
                    'description': 'A disciplined, technique-driven chef who believes shortcuts are insults to the '
                                   'ingredients. Obsessed with butter, reduction, and proper searing.',
                    'image_filename': 'french_classic.jpg',
                    'constraints': {'taste_range': {'min': 5, 'max': 5},
                                    'speed_range': {'min': 1, 'max': 5},
                                    'complexity_range': {'min': 2,
                                                         'max': 3,
                                                         'note': '1=Simplistic, 2=Moderate, 3=Elevated'},
                                    'richness_range': {'min': 4, 'max': 5},
                                    'cleanup_range': {'min': 1, 'max': 5}},
                    'diet_preferences': [],
                    'cooking_style': {'preferred_tools': [],
                                      'avoid_tools': [],
                                      'preferred_methods': ['Blending', 'Sous Vide'],
                                      'avoid_methods': ['Braising',
                                                        'Slow-Cooked',
                                                        'Air-Fried',
                                                        'Deep-Fried',
                                                        'Microwaving']},
                    'ingredient_logic': {'staples': ['Butter',
                                                     'Heavy Cream',
                                                     'Shallots',
                                                     'White Wine',
                                                     'Thyme',
                                                     'Stock'],
                                         'banned_ingredients': ['Margarine', 'Cooking Spray', 'Garlic Powder'],
                                         'low_carb_strategy': 'Focus on rich proteins and butter-basted vegetables. '
                                                              'No artificial thickeners; use reduction.'},
                    'instruction_style': {'tone': 'Authoritative, strict, uncompromising.',
                                          'example_phrase': 'Do not rush the fond. Respect the process.'}},
 'meta_learner': {'name': 'The Meta-Learner',
                  'archetype': 'The 4-Hour Chef',
                  'description': "A 'human guinea pig' and obsessive optimizer who believes you can become "
                                 'world-class in months, not years. Treats the kitchen as a lab for rapid skill '
                                 'acquisition using the DiSSS and CaFE frameworks.',
                  'image_filename': 'meta_learner.png',
                  'constraints': {'taste_range': {'min': 4, 'max': 5},
                                  'speed_range': {'min': 5, 'max': 5},
                                  'complexity_range': {'min': 1,
                                                       'max': 3,
                                                       'note': '1=Simplistic, 2=Moderate, 3=Elevated'},
                                  'richness_range': {'min': 2, 'max': 4},
                                  'cleanup_range': {'min': 1, 'max': 1}},
                  'diet_preferences': [{'diet_id': 'slow_carb', 'action': 'prioritize'}],
                  'cooking_style': {'preferred_tools': [],
                                    'avoid_tools': [],
                                    'preferred_methods': ['Searing', 'One-Pot', 'Batch Cooking'],
                                    'avoid_methods': ['Braising', 'Deep-Fried']},
                  'ingredient_logic': {'staples': ['Lean Beef',
                                                   'Lentils',
                                                   'Black Beans',
                                                   'Spinach',
                                                   'Eggs',
                                                   'Kimchi'],
                                       'banned_ingredients': ['White Bread', 'Pasta', 'Potatoes', 'Sugar', 'Fruit'],
                                       'low_carb_strategy': "The Slow-Carb Diet®: Avoid 'white' carbohydrates, eat "
                                                            'the same few meals over and over, and save the junk for '
                                                            'Cheat Day.'},
                  'instruction_style': {'tone': "Scientific, adventurous, focused on 'Minimal Effective Dose'.",
                                        'example_phrase': 'Apply 80/20 rule: this technique gives 80% of the flavor '
                                                          'with 20% of the effort.'}},
 'low_carb_chef': {'name': 'The Low Carb Chef',
                   'archetype': 'The Bio-Hacker',
                   'description': 'A health-focused chef who prioritizes nutrient density and stable blood sugar. '
                                  'Views food primarily as high-quality fuel.',
                   'image_filename': 'low_carb_chef.jpg',
                   'constraints': {'taste_range': {'min': 3, 'max': 5},
                                   'speed_range': {'min': 2, 'max': 4},
                                   'complexity_range': {'min': 2,
                                                        'max': 3,
                                                        'note': '1=Simplistic, 2=Moderate, 3=Elevated'},
                                   'richness_range': {'min': 1, 'max': 4},
                                   'cleanup_range': {'min': 2, 'max': 4}},
                   'diet_preferences': [],
                   'cooking_style': {'preferred_tools': [],
                                     'avoid_tools': [],
                                     'preferred_methods': ['Air-Fried', 'Blending', 'Microwaving'],
                                     'avoid_methods': ['Braising', 'Slow-Cooked', 'Deep-Fried']},
                   'ingredient_logic': {'staples': ['Almond Flour',
                                                    'Cauliflower',
                                                    'Zucchini',
                                                    'Avocado',
                                                    'Coconut Oil'],
                                        'banned_ingredients': ['Sugar', 'White Flour', 'Seed Oils'],
                                        'low_carb_strategy': 'Substitution experts (Almond flour, cauliflower rice, '
                                                             'zucchini noodles).'},
                   'instruction_style': {'tone': 'Encouraging, informative, focuses on macros.',
                                         'example_phrase': 'This swap saves you 40g of carbs while keeping you in '
                                                           'ketosis.'}},
 'speezy_gonzales': {'name': 'Speezy Gonzales',
                     'archetype': 'The Shortcut King',
                     'description': 'Efficiency over everything. If it can be done in 15 minutes with 90% of the '
                                    "taste, that's a win. Embraces technology to save time.",
                     'image_filename': 'speezy_gonzales.jpg',
                     'constraints': {'taste_range': {'min': 3, 'max': 5},
                                     'speed_range': {'min': 4, 'max': 5},
                                     'complexity_range': {'min': 1,
                                                          'max': 2,
                                                          'note': '1=Simplistic, 2=Moderate, 3=Elevated'},
                                     'richness_range': {'min': 1, 'max': 5},
                                     'cleanup_range': {'min': 1, 'max': 2}},
                     'diet_preferences': [],
                     'cooking_style': {'preferred_tools': [],
                                       'avoid_tools': [],
                                       'preferred_methods': ['Air-Fried', 'Microwaving'],
                                       'avoid_methods': ['Braising', 'Slow-Cooked']},
                     'ingredient_logic': {'staples': ['Pre-cut Veggies',
                                                      'Rotisserie Chicken',
                                                      'Jarred Salsa',
                                                      'Cheese slices'],
                                          'banned_ingredients': ['Anything requiring marinating'],
                                          'low_carb_strategy': "Simplicity. Don't bake fake bread; just use a "
                                                               'lettuce wrap or eat from a bowl.'},
                     'instruction_style': {'tone': 'Casual, urgent, brotherly, slangy.',
                                           'example_phrase': 'Toss it in the air fryer, 10 mins, boom. Dinner '
                                                             'served.'}}}

NEW = {'french_classic': {'name': 'The French Classic',
                    'archetype': 'The Old School',
                    'description': 'A disciplined, technique-driven chef who believes shortcuts are insults to the '
                                   'ingredients. Obsessed with butter, reduction, proper searing and slow braises.',
                    'image_filename': 'french_classic.jpg',
                    'constraints': {'max_total_minutes': None,
                                    'max_cleanup': None,
                                    'max_spice': 1,
                                    'difficulties': ['Moderate', 'Elevated'],
                                    'diet': None,
                                    'max_carbs_per_serving': None},
                    'diet_preferences': [],
                    'cooking_style': {'preferred_tools': [],
                                      'avoid_tools': [],
                                      'preferred_methods': ['sear', 'braise', 'reduce', 'saute', 'roast', 'poach'],
                                      'avoid_methods': ['microwave', 'airfry', 'deep_fry']},
                    'ingredient_logic': {'staples': ['Butter',
                                                     'Heavy cream',
                                                     'Shallots',
                                                     'White wine',
                                                     'Thyme',
                                                     'Stock'],
                                         'banned_ingredients': ['Margarine', 'Cooking spray', 'Garlic powder'],
                                         'low_carb_strategy': 'Build flavour in layers: a proper fond, a reduction, '
                                                              'butter at the end.'},
                    'instruction_style': {'tone': 'Authoritative, strict, uncompromising.',
                                          'example_phrase': 'Do not rush the fond. Respect the process.'}},
 'meta_learner': {'name': 'The Meta-Learner',
                  'archetype': 'The Optimizer',
                  'description': 'Learns fast by doing. Picks the few techniques that matter most, repeats them '
                                 'until they stick, and explains why each step works.',
                  'image_filename': 'meta_learner.jpg',
                  'constraints': {'max_total_minutes': 45,
                                  'max_cleanup': 3,
                                  'max_spice': None,
                                  'difficulties': ['Simplistic', 'Moderate'],
                                  'diet': None,
                                  'max_carbs_per_serving': None},
                  'diet_preferences': [],
                  'cooking_style': {'preferred_tools': [],
                                    'avoid_tools': [],
                                    'preferred_methods': ['sear', 'pan_fry', 'roast', 'simmer'],
                                    'avoid_methods': ['deep_fry']},
                  'ingredient_logic': {'staples': ['Eggs', 'Lentils', 'Beans', 'Spinach', 'Lean beef'],
                                       'banned_ingredients': [],
                                       'low_carb_strategy': 'The minimum effective dose: the one or two details that '
                                                            'give most of the result.'},
                  'instruction_style': {'tone': 'Curious, analytical, explains the why.',
                                        'example_phrase': 'Get the pan properly hot; that one detail does most of '
                                                          'the work.'}},
 'low_carb_chef': {'name': 'The Low Carb Chef',
                   'archetype': 'The Bio-Hacker',
                   'description': 'A health-focused chef who prioritises protein, vegetables and good fats, and '
                                  'keeps carbohydrates low without making food feel like a diet.',
                   'image_filename': 'low_carb_chef.jpg',
                   'constraints': {'max_total_minutes': None,
                                   'max_cleanup': None,
                                   'max_spice': None,
                                   'difficulties': ['Simplistic', 'Moderate', 'Elevated'],
                                   'diet': None,
                                   'max_carbs_per_serving': 20},
                   'diet_preferences': [{'diet_id': 'keto', 'action': 'prioritize'}],
                   'cooking_style': {'preferred_tools': [],
                                     'avoid_tools': [],
                                     'preferred_methods': ['airfry', 'roast', 'sear', 'pan_fry'],
                                     'avoid_methods': ['deep_fry']},
                   'ingredient_logic': {'staples': ['Cauliflower',
                                                    'Zucchini',
                                                    'Avocado',
                                                    'Eggs',
                                                    'Almond flour',
                                                    'Olive oil'],
                                        'banned_ingredients': ['Sugar', 'White flour', 'Pasta', 'Rice', 'Potatoes'],
                                        'low_carb_strategy': 'Swap the starch: cauliflower rice, zucchini noodles, '
                                                             'lettuce wraps.'},
                   'instruction_style': {'tone': 'Encouraging, informative, focuses on macros.',
                                         'example_phrase': 'This swap saves you about 40 g of carbs and you will not '
                                                           'miss it.'}},
 'speezy_gonzales': {'name': 'Speezy Gonzales',
                     'archetype': 'The Shortcut King',
                     'description': 'Efficiency over everything. If it can be done in 20 minutes with 90% of the '
                                    "taste, that's a win. Embraces shortcuts and gadgets.",
                     'image_filename': 'speezy_gonzales.jpg',
                     'constraints': {'max_total_minutes': 20,
                                     'max_cleanup': 2,
                                     'max_spice': None,
                                     'difficulties': ['Simplistic'],
                                     'diet': None,
                                     'max_carbs_per_serving': None},
                     'diet_preferences': [],
                     'cooking_style': {'preferred_tools': [],
                                       'avoid_tools': [],
                                       'preferred_methods': ['airfry', 'microwave', 'stir_fry', 'pan_fry'],
                                       'avoid_methods': ['braise', 'slow_cook']},
                     'ingredient_logic': {'staples': ['Pre-cut vegetables',
                                                      'Rotisserie chicken',
                                                      'Jarred salsa',
                                                      'Cheese slices'],
                                          'banned_ingredients': [],
                                          'low_carb_strategy': 'Shortcuts are allowed: ready-made sauces, pre-cut '
                                                               'vegetables, cooked chicken.'},
                     'instruction_style': {'tone': 'Casual, urgent, brotherly, slangy.',
                                           'example_phrase': 'Toss it in the air fryer, 10 minutes, boom. Dinner '
                                                             'served.'}},
 'family_cook': {'name': 'The Family Cook',
                 'archetype': 'The Weeknight Hero',
                 'description': 'Feeds a busy family on weeknights: familiar flavours with a small twist, mild '
                                'enough for children, extra vegetables where nobody notices, and leftovers that '
                                'freeze.',
                 'image_filename': '',
                 'constraints': {'max_total_minutes': 45,
                                 'max_cleanup': 3,
                                 'max_spice': 1,
                                 'difficulties': ['Simplistic', 'Moderate'],
                                 'diet': None,
                                 'max_carbs_per_serving': None},
                 'diet_preferences': [],
                 'cooking_style': {'preferred_tools': [],
                                   'avoid_tools': [],
                                   'preferred_methods': ['roast', 'simmer', 'bake', 'pan_fry'],
                                   'avoid_methods': ['deep_fry']},
                 'ingredient_logic': {'staples': ['Minced meat', 'Pasta', 'Rice', 'Carrots', 'Peas', 'Cheese'],
                                      'banned_ingredients': [],
                                      'low_carb_strategy': 'Make double and freeze half; keep the heat on the table, '
                                                           'not in the pot.'},
                 'instruction_style': {'tone': 'Warm, practical, reassuring.',
                                       'example_phrase': "Make double and freeze half: Thursday's dinner is "
                                                         'sorted.'}},
 'the_green_chef': {'name': 'The Green Chef',
                    'archetype': 'The Plant Lover',
                    'description': 'Cooks vegetarian food that meat eaters ask for again: seasonal vegetables, beans '
                                   'and lentils, whole grains and bold spices, with flavour first and no preaching.',
                    'image_filename': '',
                    'constraints': {'max_total_minutes': None,
                                    'max_cleanup': None,
                                    'max_spice': None,
                                    'difficulties': ['Simplistic', 'Moderate', 'Elevated'],
                                    'diet': 'vegetarian',
                                    'max_carbs_per_serving': None},
                    'diet_preferences': [{'diet_id': 'vegetarian', 'action': 'prioritize'},
                                         {'diet_id': 'vegan', 'action': 'prioritize'}],
                    'cooking_style': {'preferred_tools': [],
                                      'avoid_tools': [],
                                      'preferred_methods': ['roast', 'braise', 'simmer', 'sear'],
                                      'avoid_methods': ['deep_fry']},
                    'ingredient_logic': {'staples': ['Chickpeas',
                                                     'Lentils',
                                                     'Seasonal vegetables',
                                                     'Halloumi',
                                                     'Tahini',
                                                     'Whole grains'],
                                         'banned_ingredients': [],
                                         'low_carb_strategy': 'Roast or char the vegetables for depth, and add acid '
                                                              'and herbs at the end.'},
                    'instruction_style': {'tone': 'Enthusiastic, flavour-first, never preachy.',
                                          'example_phrase': "Roast the cauliflower until the edges char; that's "
                                                            'where the flavour is.'}}}

chef = sa.table('chef', *[sa.column(c) for c in ('id', 'name', 'archetype', 'description', 'image_filename') + JSON_FIELDS])


def _row(conn, chef_id):
    r = conn.execute(sa.select(chef).where(chef.c.id == chef_id)).mappings().first()
    if r is None:
        return None
    out = dict(r)
    for f in JSON_FIELDS:
        try:
            out[f] = json.loads(out[f]) if out[f] else None
        except ValueError:
            pass
    return out


def _same(row, seed):
    return all((row.get(k) or None) == (v or None) for k, v in seed.items())


def _values(seed):
    return {k: (json.dumps(v) if k in JSON_FIELDS else v) for k, v in seed.items()}


def _swap(conn, frm, to, label):
    for chef_id, seed in to.items():
        row = _row(conn, chef_id)
        if chef_id in frm:
            if row is None or _same(row, seed):
                continue  # missing, or already as it should be (a new database is seeded from chefs.json)
            if _same(row, frm[chef_id]):
                conn.execute(chef.update().where(chef.c.id == chef_id).values(**_values(seed)))
            else:
                print(f'chef {chef_id} was edited after it was {label}; left as it is')


def upgrade():
    conn = op.get_bind()
    _swap(conn, OLD, {k: v for k, v in NEW.items() if k in OLD}, 'seeded')
    for chef_id in ADDED:
        if _row(conn, chef_id) is None:
            conn.execute(chef.insert().values(id=chef_id, **_values(NEW[chef_id])))


def downgrade():
    conn = op.get_bind()
    _swap(conn, NEW, OLD, 'updated')
    for chef_id in ADDED:
        used = conn.execute(sa.text('SELECT 1 FROM recipe WHERE chef_id = :c LIMIT 1'), {'c': chef_id}).first()
        if not used:
            conn.execute(chef.delete().where(chef.c.id == chef_id))
