"""step verb and line cut

Two nullable columns for recipe model v2, filled by the structure prompt from
now on: recipe_step.verb (the action in the step's short name, "kok opp") and
recipe_line.cut (how the ingredient is cut, an id from
data/constraints/cuts.json). Existing rows stay null. Nothing else changes.

Revision ID: 7c1e5a2b9d40
Revises: 4ecb711c94bc
Create Date: 2026-10-20

"""
from alembic import op
import sqlalchemy as sa


revision = '7c1e5a2b9d40'
down_revision = '4ecb711c94bc'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('recipe_step', sa.Column('verb', sa.String(length=60), nullable=True))
    op.add_column('recipe_line', sa.Column('cut', sa.String(length=20), nullable=True))


def downgrade():
    op.drop_column('recipe_line', 'cut')
    op.drop_column('recipe_step', 'verb')
