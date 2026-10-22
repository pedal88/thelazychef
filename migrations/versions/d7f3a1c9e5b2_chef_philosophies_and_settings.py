"""chefs: three philosophies, and settings on the recipe

The six chef personas mixed a philosophy (classic, shortcuts), an audience (families) and a diet (low carb,
vegetarian), which left gaps (a quick low-carb dinner) and overlaps. Decided 22.10.2026: a chef is a
philosophy, a rule for how to choose when quality, time and effort pull apart, and diet and audience are
settings that go on top of any chef (RECIPE_MODEL_V2.md, "Kokker og innstillinger"):

- The Classicist: the original, in any cuisine; never swaps what defines the dish.
- The Smart Cook: a shortcut only when you would hardly taste it; 45 minutes, 10 ingredients, 3 outside the
  foundation pantry.
- The Minimalist: as little as possible, fast; 25 minutes, 6 ingredients, 1 outside the foundation pantry.

Settings: vegetarian, kid_friendly and low_carb, stored on the recipe (recipe.settings).

The three chefs are added (data/agents/chefs.json). The six are kept, with their recipes, but set inactive, so
they are no longer offered: chef.active. Nothing is deleted.

Downgrade removes the three again when no recipe uses them, and drops chef.active and recipe.settings.

Revision ID: d7f3a1c9e5b2
Revises: c6e1a4d8b2f7
Create Date: 2026-10-22

"""
import json

from alembic import op
import sqlalchemy as sa


revision = 'd7f3a1c9e5b2'
down_revision = 'c6e1a4d8b2f7'
branch_labels = None
depends_on = None

JSON_FIELDS = ('constraints', 'diet_preferences', 'cooking_style', 'ingredient_logic', 'instruction_style')
NEW = [{'id': 'the_classicist',
  'image_filename': 'french_classic.jpg',
  'name': 'The Classicist',
  'archetype': 'The Original',
  'description': 'Cooks the dish the way it is meant to be, in any cuisine: the classic ingredients and the classic '
                 'method. Never swaps what makes the dish itself, and takes the time it takes.',
  'constraints': {'max_total_minutes': None,
                  'max_cleanup': None,
                  'max_spice': None,
                  'difficulties': ['Simplistic', 'Moderate', 'Elevated'],
                  'diet': None,
                  'max_carbs_per_serving': None,
                  'max_ingredients': None,
                  'max_extra': None,
                  'forms': 'fresh',
                  'ready_made': None},
  'diet_preferences': [],
  'cooking_style': {'preferred_tools': [],
                    'avoid_tools': [],
                    'preferred_methods': [],
                    'avoid_methods': ['microwave']},
  'ingredient_logic': {'staples': [],
                       'banned_ingredients': [],
                       'strategy': 'Make the original. Use the ingredients and techniques the dish is known for '
                                   'where it comes from, and never replace what defines it. A shortcut only where '
                                   'cooks there take it themselves, like good tinned tomatoes in a ragù.'},
  'instruction_style': {'tone': 'Calm and sure, like a cook who has made it a hundred times; points out the one step '
                                'that makes the dish.',
                        'example_phrase': 'Let the onions take their time; this is where the sauce gets its depth.'}},
 {'id': 'the_smart_cook',
  'image_filename': 'meta_learner.png',
  'name': 'The Smart Cook',
  'archetype': 'The Optimizer',
  'description': 'Gets nearly all of the classic result for far less work. Takes a shortcut only when you would '
                 'hardly taste the difference, and puts the effort where it shows on the plate.',
  'constraints': {'max_total_minutes': 45,
                  'max_cleanup': 3,
                  'max_spice': None,
                  'difficulties': ['Simplistic', 'Moderate'],
                  'diet': None,
                  'max_carbs_per_serving': None,
                  'max_ingredients': 10,
                  'max_extra': 3,
                  'forms': 'balanced',
                  'ready_made': 'good'},
  'diet_preferences': [],
  'cooking_style': {'preferred_tools': [],
                    'avoid_tools': [],
                    'preferred_methods': ['sear', 'roast', 'pan_fry', 'simmer'],
                    'avoid_methods': ['deep_fry']},
  'ingredient_logic': {'staples': [],
                       'banned_ingredients': [],
                       'strategy': 'Start from the classic and ask of every ingredient and step: would you taste it '
                                   'if it were simpler or gone? Keep what you would, simplify the rest. A shortcut '
                                   'is fine only when the dish is hardly worse for it.'},
  'instruction_style': {'tone': 'Practical and friendly; says why a shortcut is fine, and where not to cut corners.',
                        'example_phrase': 'Tinned tomatoes are as good here as fresh; save your effort for browning '
                                          'the meat well.'}},
 {'id': 'the_minimalist',
  'image_filename': 'speezy_gonzales.jpg',
  'name': 'The Minimalist',
  'archetype': 'The Essentialist',
  'description': 'As few ingredients, steps and pots as possible, and done fast. Happy to trade a little of the '
                 'result for a lot less work.',
  'constraints': {'max_total_minutes': 25,
                  'max_cleanup': 2,
                  'max_spice': None,
                  'difficulties': ['Simplistic'],
                  'diet': None,
                  'max_carbs_per_serving': None,
                  'max_ingredients': 6,
                  'max_extra': 1,
                  'forms': 'shortcut',
                  'ready_made': 'welcome'},
  'diet_preferences': [],
  'cooking_style': {'preferred_tools': [],
                    'avoid_tools': [],
                    'preferred_methods': ['pan_fry', 'stir_fry', 'roast', 'airfry'],
                    'avoid_methods': ['braise', 'slow_cook', 'deep_fry']},
  'ingredient_logic': {'staples': [],
                       'banned_ingredients': [],
                       'strategy': 'Strip the dish to what carries it: one main ingredient, one flavour base, one '
                                   'pot or one tray. Fewer steps beat a slightly better result.'},
  'instruction_style': {'tone': 'Short and relaxed; no step that is not needed.',
                        'example_phrase': 'Everything on one tray, into the oven, done.'}}]


def upgrade():
    with op.batch_alter_table('chef') as batch_op:
        batch_op.add_column(sa.Column('active', sa.Boolean(), server_default=sa.true(), nullable=False))
    with op.batch_alter_table('recipe') as batch_op:
        batch_op.add_column(sa.Column('settings', sa.JSON(), nullable=True))
    conn = op.get_bind()
    conn.execute(sa.text('UPDATE chef SET active = false'))
    for c in NEW:
        if conn.execute(sa.text('SELECT 1 FROM chef WHERE id = :i'), {'i': c['id']}).first():
            conn.execute(sa.text('UPDATE chef SET active = true WHERE id = :i'), {'i': c['id']})
            continue
        row = {k: c[k] for k in ('id', 'name', 'archetype', 'description', 'image_filename')}
        row.update({f: json.dumps(c[f]) for f in JSON_FIELDS})
        conn.execute(sa.text('INSERT INTO chef (id, name, archetype, description, image_filename, constraints, diet_preferences, '
                             'cooking_style, ingredient_logic, instruction_style, active) VALUES (:id, :name, :archetype, '
                             ':description, :image_filename, :constraints, :diet_preferences, :cooking_style, :ingredient_logic, '
                             ':instruction_style, true)'), row)


def downgrade():
    conn = op.get_bind()
    for c in NEW:
        if not conn.execute(sa.text('SELECT 1 FROM recipe WHERE chef_id = :i'), {'i': c['id']}).first():
            conn.execute(sa.text('DELETE FROM chef WHERE id = :i'), {'i': c['id']})
    with op.batch_alter_table('recipe') as batch_op:
        batch_op.drop_column('settings')
    with op.batch_alter_table('chef') as batch_op:
        batch_op.drop_column('active')
