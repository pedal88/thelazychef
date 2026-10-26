"""recipe_line.state, grade and variety: the state catalog (data/constraints/states.json)

Three new nullable columns on recipe_line. Nothing that exists changes: every line gets NULL, and the old cut column
stays and is read as the state until the existing v2 recipes are converted. Downgrade drops the three columns.

Revision ID: d3f1a7c5e2b0
Revises: c7a2e9d4b1f8
Create Date: 2026-10-26

"""
from alembic import op
import sqlalchemy as sa


revision = 'd3f1a7c5e2b0'
down_revision = 'c7a2e9d4b1f8'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('recipe_line', sa.Column('state', sa.String(length=20), nullable=True))
    op.add_column('recipe_line', sa.Column('grade', sa.String(length=12), nullable=True))
    op.add_column('recipe_line', sa.Column('variety', sa.String(length=80), nullable=True))


def downgrade():
    op.drop_column('recipe_line', 'variety')
    op.drop_column('recipe_line', 'grade')
    op.drop_column('recipe_line', 'state')
