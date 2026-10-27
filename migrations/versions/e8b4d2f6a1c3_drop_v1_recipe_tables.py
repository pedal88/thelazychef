"""Drop the tables and columns of the retired recipe model v1 (step 4 of retiring v1, 27.10.2026)

The v1 recipes were exported as batch lines and archived (scripts/retire_v1.py), and the code that made and showed
them is gone. This drops what only they used:
- instruction and recipe_ingredient: the v1 steps and ingredient lines
- recipe_evaluation: the QA scores of the removed recipe scoring
- recipe.component_images, recipe.social_hooks and recipe.source_image_filename: v1 image and video fields

**This deletes data.** Take a database backup first. The archived v1 recipes stay as rows in recipe (titles, images,
saves), without their lines and steps. Downgrade recreates the tables and columns empty; the data comes back only
from the backup.

Revision ID: e8b4d2f6a1c3
Revises: d3f1a7c5e2b0
Create Date: 2026-10-27

"""
from alembic import op
import sqlalchemy as sa


revision = 'e8b4d2f6a1c3'
down_revision = 'd3f1a7c5e2b0'
branch_labels = None
depends_on = None


def upgrade():
    op.drop_table('recipe_ingredient')
    op.drop_table('instruction')
    op.drop_table('recipe_evaluation')
    op.drop_column('recipe', 'component_images')
    op.drop_column('recipe', 'social_hooks')
    op.drop_column('recipe', 'source_image_filename')


def downgrade():
    op.add_column('recipe', sa.Column('source_image_filename', sa.String(), nullable=True))
    op.add_column('recipe', sa.Column('social_hooks', sa.JSON(), server_default='{}', nullable=False))
    op.add_column('recipe', sa.Column('component_images', sa.JSON(), server_default='{}', nullable=False))
    op.create_table(
        'recipe_evaluation',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('recipe_id', sa.Integer(), nullable=False),
        sa.Column('score_name', sa.Integer(), nullable=False),
        sa.Column('score_ingredients', sa.Integer(), nullable=False),
        sa.Column('score_components', sa.Integer(), nullable=False),
        sa.Column('score_amounts', sa.Integer(), nullable=False),
        sa.Column('score_steps', sa.Integer(), nullable=False),
        sa.Column('score_image', sa.Integer(), nullable=True),
        sa.Column('total_score', sa.Float(), nullable=False),
        sa.Column('evaluation_details', sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(['recipe_id'], ['recipe.id'], name='recipe_evaluation_recipe_id_fkey', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('recipe_id'),
    )
    op.create_table(
        'instruction',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('recipe_id', sa.Integer(), nullable=False),
        sa.Column('phase', sa.String(), nullable=False),
        sa.Column('component', sa.String(length=100), nullable=False),
        sa.Column('step_number', sa.Integer(), nullable=False),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('estimated_minutes', sa.Integer(), nullable=True),
        sa.Column('global_order_index', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['recipe_id'], ['recipe.id'], name='instruction_recipe_id_fkey', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_table(
        'recipe_ingredient',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('recipe_id', sa.Integer(), nullable=False),
        sa.Column('ingredient_id', sa.Integer(), nullable=False),
        sa.Column('amount', sa.Float(), nullable=False),
        sa.Column('unit', sa.String(), nullable=False),
        sa.Column('prep_style', sa.String(), nullable=True),
        sa.Column('gram_weight', sa.Float(), nullable=True),
        sa.Column('component', sa.String(), nullable=False),
        sa.ForeignKeyConstraint(['ingredient_id'], ['ingredient.id']),
        sa.ForeignKeyConstraint(['recipe_id'], ['recipe.id'], name='recipe_ingredient_recipe_id_fkey', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
