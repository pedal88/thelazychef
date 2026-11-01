"""a post's numbers can come from the platform's API: reach, where they came from and when

Adds social_post_stat.reach, .source ('manual' for every row so far, the server default; 'instagram' for the rows
services/social_stats.py fetches) and .fetched_at. Only adds columns.

Downgrade drops them.

Revision ID: d4a8c2e6f1b3
Revises: c3f9a1e5d7b2
Create Date: 2026-11-01
"""
from alembic import op
import sqlalchemy as sa


revision = 'd4a8c2e6f1b3'
down_revision = 'c3f9a1e5d7b2'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('social_post_stat', schema=None) as batch_op:
        batch_op.add_column(sa.Column('reach', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('fetched_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('source', sa.String(length=20), nullable=False, server_default='manual'))


def downgrade():
    with op.batch_alter_table('social_post_stat', schema=None) as batch_op:
        batch_op.drop_column('source')
        batch_op.drop_column('fetched_at')
        batch_op.drop_column('reach')
