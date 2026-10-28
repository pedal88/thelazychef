"""how often a user has made a recipe, and when last

The celebration after the last step (templates/recipe_v2_make.html) saves "I made this" and says how many times the
dish has been made. Adds made_count and last_made_at to user_recipe_interaction. Only adds columns; a recipe already
marked as made counts once.

Downgrade drops the two columns.

Revision ID: a7c2e9d4b1f6
Revises: e2b6d4f8a1c3
Create Date: 2026-10-28
"""
from alembic import op
import sqlalchemy as sa


revision = 'a7c2e9d4b1f6'
down_revision = 'e2b6d4f8a1c3'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('user_recipe_interaction') as batch_op:
        batch_op.add_column(sa.Column('made_count', sa.Integer(), nullable=False, server_default='0'))
        batch_op.add_column(sa.Column('last_made_at', sa.DateTime(), nullable=True))
    op.execute(sa.text('UPDATE user_recipe_interaction SET made_count = 1 WHERE is_made AND made_count = 0'))


def downgrade():
    with op.batch_alter_table('user_recipe_interaction') as batch_op:
        batch_op.drop_column('last_made_at')
        batch_op.drop_column('made_count')
