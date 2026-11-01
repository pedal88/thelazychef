"""a post in the log can be a draft: planned and rendered by scripts/social_batch.py, not up yet

Adds social_post.status, 'posted' for every post logged so far (the server default) and 'draft' for the ones the
batch script plans. Only adds a column.

Downgrade drops it.

Revision ID: c3f9a1e5d7b2
Revises: b8d4f2a6c9e1
Create Date: 2026-11-01
"""
from alembic import op
import sqlalchemy as sa


revision = 'c3f9a1e5d7b2'
down_revision = 'b8d4f2a6c9e1'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('social_post', schema=None) as batch_op:
        batch_op.add_column(sa.Column('status', sa.String(length=20), nullable=False, server_default='posted'))


def downgrade():
    with op.batch_alter_table('social_post', schema=None) as batch_op:
        batch_op.drop_column('status')
