"""recipe.age_from_months: the age a recipe made with the Baby setting suits from

A new nullable column on recipe. Nothing that exists changes; every recipe gets NULL. Downgrade drops the column.

Revision ID: c7a2e9d4b1f8
Revises: b4e8d1f6a2c9
Create Date: 2026-10-23

"""
from alembic import op
import sqlalchemy as sa


revision = 'c7a2e9d4b1f8'
down_revision = 'b4e8d1f6a2c9'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('recipe', sa.Column('age_from_months', sa.Integer(), nullable=True))


def downgrade():
    op.drop_column('recipe', 'age_from_months')
