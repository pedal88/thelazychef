"""what a video in the inbox shows, written down

video_inbox.video_text keeps what Gemini wrote down when the video was looked up, so the recipe is made from the same
text and the video is paid for once (services/recipe_v2/inbox.py). Starts empty. Only adds a column.

Downgrade drops the column.

Revision ID: e5a9c3f7b2d8
Revises: d4f7a2c8e6b1
Create Date: 2026-11-04
"""
from alembic import op
import sqlalchemy as sa


revision = 'e5a9c3f7b2d8'
down_revision = 'd4f7a2c8e6b1'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('video_inbox', sa.Column('video_text', sa.Text(), nullable=True))


def downgrade():
    op.drop_column('video_inbox', 'video_text')
