"""recipes and ingredients in other languages

recipe_translation keeps a recipe's words per language, and ingredient.name_nb an ingredient's Norwegian name
(services/recipe_v2/translation.py). Both start empty and everything shows as today. Only adds.

Downgrade drops the table and the column.

Revision ID: d4f7a2c8e6b1
Revises: a7d4c1e9f3b6
Create Date: 2026-11-04
"""
from alembic import op
import sqlalchemy as sa


revision = 'd4f7a2c8e6b1'
down_revision = 'a7d4c1e9f3b6'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('ingredient', sa.Column('name_nb', sa.String(), nullable=True))
    op.create_table(
        'recipe_translation',
        sa.Column('recipe_id', sa.Integer(), nullable=False),
        sa.Column('language', sa.String(length=8), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('source_title', sa.String(), nullable=False),
        sa.Column('texts', sa.JSON(), nullable=False),
        sa.Column('source_hash', sa.String(length=64), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['recipe_id'], ['recipe.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('recipe_id', 'language'),
    )


def downgrade():
    op.drop_table('recipe_translation')
    op.drop_column('ingredient', 'name_nb')
