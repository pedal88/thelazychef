"""recipe v2 metadata

Four nullable columns on recipe: heat_source (derived from the steps),
spice_level, keeps_days and freezes (set by the structure prompt). Existing
rows stay null. Nothing else changes.

Revision ID: 3b8f2d61a7c5
Revises: 7c1e5a2b9d40
Create Date: 2026-10-20

"""
from alembic import op
import sqlalchemy as sa


revision = '3b8f2d61a7c5'
down_revision = '7c1e5a2b9d40'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('recipe', sa.Column('heat_source', sa.String(length=20), nullable=True))
    op.add_column('recipe', sa.Column('spice_level', sa.Integer(), nullable=True))
    op.add_column('recipe', sa.Column('keeps_days', sa.Integer(), nullable=True))
    op.add_column('recipe', sa.Column('freezes', sa.Boolean(), nullable=True))


def downgrade():
    op.drop_column('recipe', 'freezes')
    op.drop_column('recipe', 'keeps_days')
    op.drop_column('recipe', 'spice_level')
    op.drop_column('recipe', 'heat_source')
