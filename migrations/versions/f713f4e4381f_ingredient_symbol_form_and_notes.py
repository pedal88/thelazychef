"""ingredient symbol form and notes

Two inputs for ingredient symbols (services/ingredient_symbols.py):
image_form replaces the sub-category rule for an ingredient that does not
fit it, and image_notes adds what makes it look right. Seeds the forms and
notes tuned in the prompt lab on 18.10.2026, only where the field is empty.

Revision ID: f713f4e4381f
Revises: f22c269feda5
Create Date: 2026-10-18

"""
from alembic import op
import sqlalchemy as sa


revision = 'f713f4e4381f'
down_revision = 'f22c269feda5'
branch_labels = None
depends_on = None

STOCK_CUBE = "Show one unwrapped stock cube with nothing else, no container."
FORMS = {
    'beef stock cube': STOCK_CUBE,
    'chicken bouillon cube': STOCK_CUBE,
    'canned coconut milk': "Show one simple closed can with a coconut on the label and no words.",
}
NOTES = {
    'chicken breast': "Pale pink raw chicken breast with visible natural muscle grain, clearly poultry, not salmon or pork.",
    'salmon fillet': "Bright orange-pink raw salmon fillet with white fat lines.",
    'garlic': "A whole garlic bulb with one loose clove.",
    'garlic powder': "Fine pale beige powder.",
    'star anise': "Two or three whole star-shaped pods.",
    'eggs': "Two whole brown eggs, clearly oval, with clean, smooth, evenly colored shells and no spots.",
    'banana': "One whole unpeeled yellow banana.",
    'ground beef': "Lean minced beef, deep red with only small specks of fat.",
    'parmesan': "A wedge of hard aged cheese with rind.",
}


def upgrade():
    op.add_column('ingredient', sa.Column('image_form', sa.Text(), nullable=True))
    op.add_column('ingredient', sa.Column('image_notes', sa.Text(), nullable=True))

    conn = op.get_bind()
    for name, form in FORMS.items():
        conn.execute(sa.text("UPDATE ingredient SET image_form = :v WHERE name = :n AND image_form IS NULL"), {'v': form, 'n': name})
    for name, notes in NOTES.items():
        conn.execute(sa.text("UPDATE ingredient SET image_notes = :v WHERE name = :n AND image_notes IS NULL"), {'v': notes, 'n': name})


def downgrade():
    op.drop_column('ingredient', 'image_notes')
    op.drop_column('ingredient', 'image_form')
