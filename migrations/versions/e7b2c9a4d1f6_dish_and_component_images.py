"""dish and component images

New nullable columns for the v2 dish and component images
(services/recipe_v2/images.py): recipe.plating, recipe.hero_image_prompt and
recipe.image_style; recipe_component.appearance and recipe_component.image_from.
No data is changed. Downgrade drops the columns.

Revision ID: e7b2c9a4d1f6
Revises: c4e8a1f05b3d
Create Date: 2026-10-21

"""
from alembic import op
import sqlalchemy as sa


revision = 'e7b2c9a4d1f6'
down_revision = 'c4e8a1f05b3d'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('recipe', schema=None) as batch_op:
        batch_op.add_column(sa.Column('plating', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('hero_image_prompt', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('image_style', sa.String(length=40), nullable=True))
    with op.batch_alter_table('recipe_component', schema=None) as batch_op:
        batch_op.add_column(sa.Column('appearance', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('image_from', sa.String(), nullable=True))


def downgrade():
    with op.batch_alter_table('recipe_component', schema=None) as batch_op:
        batch_op.drop_column('image_from')
        batch_op.drop_column('appearance')
    with op.batch_alter_table('recipe', schema=None) as batch_op:
        batch_op.drop_column('image_style')
        batch_op.drop_column('hero_image_prompt')
        batch_op.drop_column('plating')
