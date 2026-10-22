"""pantry: how long an ingredient keeps (ingredient.keeps)

How long an ingredient keeps the way it is normally stored at home: 'days' (fresh herbs, salad, meat and fish
in the fridge), 'weeks' (most vegetables, dairy, eggs), 'months' (root vegetables, onions, hard cheese, sauces)
or 'years' (dry goods, tins, spices, oils). It weighs in when choosing the foundation pantry: something that
keeps for years is cheap to have even if it is used now and then, fresh coriander has to be used often
(RECIPE_MODEL_V2.md, "Basisvarer og grunnlager"). Later: the shopping list, leftovers and week plans.

Filled from the sub-category, then the main category, with exceptions by name (onions and garlic keep for
months, soy sauce for years, tinned coconut milk for years). A new column, nullable; nothing else changes.

Downgrade drops the column.

Revision ID: b8d2e5f1a9c3
Revises: a3d7f2c9e1b6
Create Date: 2026-10-22

"""
from alembic import op
import sqlalchemy as sa


revision = 'b8d2e5f1a9c3'
down_revision = 'a3d7f2c9e1b6'
branch_labels = None
depends_on = None

MAIN = {
    'baking ingredients': 'years', 'canned and preserved': 'years', 'cereal grains and pasta': 'years',
    'alcoholic beverages': 'years', 'spices and herbs': 'years', 'nuts and seeds': 'months',
    'sauces and condiments': 'months', 'fats and oils': 'months', 'dairy and egg': 'weeks', 'vegetables': 'weeks',
    'fruit and fruit products': 'days', 'non-alcoholic beverages': 'weeks', 'meat': 'days', 'fish and seafood': 'days',
    'bakery and bread': 'days',
}
SUB = {
    'fresh herbs': 'days', 'leafy greens': 'days', 'mushrooms': 'days', 'berries': 'days', 'stone fruits': 'days',
    'tropical fruits': 'days', 'grapes': 'weeks', 'melons': 'weeks', 'citrus fruits': 'weeks', 'pome fruits': 'weeks',
    'dried fruits': 'months', 'juices': 'weeks', 'root vegetables': 'months', 'bulb vegetables': 'months',
    'legumes & pulses': 'years', 'cooking oils': 'years', 'butter and spreads': 'months', 'cheese': 'weeks',
    'coffee and coffee drinks': 'years', 'tea': 'years', 'water': 'years', 'flatbreads': 'weeks',
    'breakfast cereals': 'months',
}
NAMES = {
    'spring onions': 'weeks', 'leeks': 'weeks', 'fennel bulbs': 'weeks', 'fresh ginger': 'weeks', 'galangal': 'weeks',
    'radishes': 'weeks', 'cabbage': 'months', 'red cabbage': 'months', 'pumpkin': 'months', 'butternut squash': 'months',
    'acorn squash': 'months', 'spaghetti squash': 'months', 'bean sprouts': 'days', 'tofu': 'weeks', 'edamame': 'months',
    'green peas': 'months', 'parmesan': 'months', 'pecorino romano': 'months', 'lemon juice': 'months', 'lime juice': 'months',
    'soy sauce': 'years', 'dark soy sauce': 'years', 'fish sauce': 'years', 'mirin': 'years', 'kimchi': 'months',
    'sun-dried tomato': 'months', 'balsamic vinegar': 'years', 'red wine vinegar': 'years', 'rice vinegar': 'years',
    'white vinegar': 'years', 'white wine vinegar': 'years', 'beef stock cube': 'years', 'chicken bouillon cube': 'years',
    'honey': 'years', 'coconut milk': 'years', 'coconut cream': 'years', 'ground beef': 'days', 'bacon': 'weeks',
    'eggs': 'weeks', 'avocado': 'days', 'banana': 'days', 'potatoes': 'months', 'sweet potatoes': 'weeks',
    'fresh yeast': 'weeks', 'tortilla chips': 'years',
}


def keeps_of(name, main, sub):
    n = (name or '').strip().lower()
    if n in NAMES:
        return NAMES[n]
    if 'frozen' in n:
        return 'months'
    return SUB.get((sub or '').strip().lower()) or MAIN.get((main or '').strip().lower())


def upgrade():
    with op.batch_alter_table('ingredient') as batch_op:
        batch_op.add_column(sa.Column('keeps', sa.String(length=8), nullable=True))
    conn = op.get_bind()
    rows = conn.execute(sa.text('SELECT id, name, main_category, sub_category FROM ingredient')).all()
    for iid, name, main, sub in rows:
        keeps = keeps_of(name, main, sub)
        if keeps:
            conn.execute(sa.text('UPDATE ingredient SET keeps = :k WHERE id = :i'), {'k': keeps, 'i': iid})


def downgrade():
    with op.batch_alter_table('ingredient') as batch_op:
        batch_op.drop_column('keeps')
