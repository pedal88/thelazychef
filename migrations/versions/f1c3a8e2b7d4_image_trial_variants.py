"""image trial variants

recipe.image_variants (JSON, nullable): dish and part images in other styles,
made on request for the image trial and shown only to admins who switch to them
(services/recipe_v2/images.py). No data is changed. Downgrade drops the column.

Revision ID: f1c3a8e2b7d4
Revises: e7b2c9a4d1f6
Create Date: 2026-10-21

"""
from alembic import op
import sqlalchemy as sa


revision = 'f1c3a8e2b7d4'
down_revision = 'e7b2c9a4d1f6'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('recipe', schema=None) as batch_op:
        batch_op.add_column(sa.Column('image_variants', sa.JSON(), nullable=True))


def downgrade():
    with op.batch_alter_table('recipe', schema=None) as batch_op:
        batch_op.drop_column('image_variants')
