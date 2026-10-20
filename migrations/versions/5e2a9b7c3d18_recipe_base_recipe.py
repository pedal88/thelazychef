"""recipe base recipe

A nullable link from a version (the same dish made by a chef persona) to its
base recipe. Existing rows stay null. Deleting a base recipe sets the link to
null in its versions; nothing else changes.

Revision ID: 5e2a9b7c3d18
Revises: a4d9c2f7e61b
Create Date: 2026-10-20

"""
from alembic import op
import sqlalchemy as sa


revision = '5e2a9b7c3d18'
down_revision = 'a4d9c2f7e61b'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('recipe', sa.Column('base_recipe_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_recipe_base_recipe_id'), 'recipe', ['base_recipe_id'], unique=False)
    op.create_foreign_key('recipe_base_recipe_id_fkey', 'recipe', 'recipe', ['base_recipe_id'], ['id'], ondelete='SET NULL')


def downgrade():
    op.drop_constraint('recipe_base_recipe_id_fkey', 'recipe', type_='foreignkey')
    op.drop_index(op.f('ix_recipe_base_recipe_id'), table_name='recipe')
    op.drop_column('recipe', 'base_recipe_id')
