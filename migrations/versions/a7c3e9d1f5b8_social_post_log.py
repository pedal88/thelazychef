"""the post log: posts on TikTok and Instagram by their code, and the platforms' numbers for them

social_post is one post (platform, code, format, recipe, what it tries) and social_post_stat the views, likes, saves,
shares and profile visits copied from the platform some days after it went up (services/funnel.py). Only adds two
tables.

Downgrade drops them.

Revision ID: a7c3e9d1f5b8
Revises: e6a2c9f4b8d1
Create Date: 2026-10-30
"""
from alembic import op
import sqlalchemy as sa


revision = 'a7c3e9d1f5b8'
down_revision = 'e6a2c9f4b8d1'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'social_post',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('platform', sa.String(length=20), nullable=False),
        sa.Column('code', sa.String(length=20), nullable=False),
        sa.Column('format', sa.String(length=20), nullable=False),
        sa.Column('recipe_id', sa.Integer(), nullable=True),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('hook', sa.String(length=200), nullable=True),
        sa.Column('sound', sa.String(length=120), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('url', sa.String(length=300), nullable=True),
        sa.Column('posted_on', sa.Date(), nullable=False),
        sa.ForeignKeyConstraint(['recipe_id'], ['recipe.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('platform', 'code', name='uq_social_post_code'),
    )
    op.create_table(
        'social_post_stat',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('post_id', sa.Integer(), nullable=False),
        sa.Column('day', sa.Integer(), nullable=False),
        sa.Column('views', sa.Integer(), nullable=True),
        sa.Column('likes', sa.Integer(), nullable=True),
        sa.Column('comments', sa.Integer(), nullable=True),
        sa.Column('saves', sa.Integer(), nullable=True),
        sa.Column('shares', sa.Integer(), nullable=True),
        sa.Column('profile_visits', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['post_id'], ['social_post.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('post_id', 'day', name='uq_social_post_stat_day'),
    )


def downgrade():
    op.drop_table('social_post_stat')
    op.drop_table('social_post')
