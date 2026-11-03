"""the video inbox

video_inbox keeps the cooking videos shared from the phone until they are made into recipes or discarded
(services/recipe_v2/inbox.py). Only adds a table.

Downgrade drops it.

Revision ID: a7d4c1e9f3b6
Revises: f6c2a8d4e1b7
Create Date: 2026-11-03
"""
from alembic import op
import sqlalchemy as sa


revision = 'a7d4c1e9f3b6'
down_revision = 'f6c2a8d4e1b7'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'video_inbox',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('url', sa.String(length=1000), nullable=False),
        sa.Column('video_key', sa.String(length=300), nullable=False),
        sa.Column('status', sa.String(length=20), server_default='new', nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('webpage_url', sa.String(length=1000), nullable=True),
        sa.Column('caption', sa.Text(), nullable=True),
        sa.Column('uploader', sa.String(length=200), nullable=True),
        sa.Column('duration_s', sa.Integer(), nullable=True),
        sa.Column('dish_name', sa.String(length=200), nullable=True),
        sa.Column('suggestions', sa.JSON(), nullable=True),
        sa.Column('similar', sa.JSON(), nullable=True),
        sa.Column('meta_error', sa.String(length=300), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('video_key'),
    )


def downgrade():
    op.drop_table('video_inbox')
