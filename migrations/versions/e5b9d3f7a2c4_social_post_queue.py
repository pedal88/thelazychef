"""the Instagram queue: a post's text, slides, when it goes up, Instagram's id for it and why it failed

Adds social_post.caption, .slide_urls, .scheduled_at, .media_id and .publish_error (services/social_publish.py). Only
adds nullable columns; no row changes.

Downgrade drops them.

Revision ID: e5b9d3f7a2c4
Revises: d4a8c2e6f1b3
Create Date: 2026-11-02
"""
from alembic import op
import sqlalchemy as sa


revision = 'e5b9d3f7a2c4'
down_revision = 'd4a8c2e6f1b3'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('social_post', schema=None) as batch_op:
        batch_op.add_column(sa.Column('caption', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('slide_urls', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('scheduled_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('media_id', sa.String(length=40), nullable=True))
        batch_op.add_column(sa.Column('publish_error', sa.Text(), nullable=True))


def downgrade():
    with op.batch_alter_table('social_post', schema=None) as batch_op:
        batch_op.drop_column('publish_error')
        batch_op.drop_column('media_id')
        batch_op.drop_column('scheduled_at')
        batch_op.drop_column('slide_urls')
        batch_op.drop_column('caption')
