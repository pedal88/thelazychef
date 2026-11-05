"""an amount the source did not give

recipe_line.estimated marks a line whose amount the model estimated, so the reader is told and approval can wait
(services/recipe_v2/estimated.py). Empty for every recipe made before. Only adds a column: nothing is rewritten.

Downgrade drops the column.

Revision ID: f6b1d3a8c2e4
Revises: e5a9c3f7b2d8
Create Date: 2026-11-05
"""
from alembic import op
import sqlalchemy as sa


revision = 'f6b1d3a8c2e4'
down_revision = 'e5a9c3f7b2d8'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('recipe_line', sa.Column('estimated', sa.Boolean(), nullable=True))


def downgrade():
    op.drop_column('recipe_line', 'estimated')
