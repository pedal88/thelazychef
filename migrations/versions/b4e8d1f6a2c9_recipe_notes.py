"""recipe notes: an admin's feedback on a recipe, written on the recipe pages

A new table, recipe_note. Nothing that exists changes. Downgrade drops the table and the notes in it.

Revision ID: b4e8d1f6a2c9
Revises: 3c67b67732b3
Create Date: 2026-10-23

"""
from alembic import op
import sqlalchemy as sa


revision = 'b4e8d1f6a2c9'
down_revision = '3c67b67732b3'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'recipe_note',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('recipe_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('place', sa.String(length=80), nullable=True),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('done', sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.ForeignKeyConstraint(['recipe_id'], ['recipe.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_recipe_note_recipe_id', 'recipe_note', ['recipe_id'])


def downgrade():
    op.drop_index('ix_recipe_note_recipe_id', table_name='recipe_note')
    op.drop_table('recipe_note')
