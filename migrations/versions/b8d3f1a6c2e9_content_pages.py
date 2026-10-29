"""content: pages made of blocks, their versions per language, and embeds

The home page and later guides (services/content, docs/CONTENT.md). Adds page, page_text and page_embed; only new
tables.

Downgrade drops the three tables.

Revision ID: b8d3f1a6c2e9
Revises: a7c2e9d4b1f6
Create Date: 2026-10-29
"""
from alembic import op
import sqlalchemy as sa


revision = 'b8d3f1a6c2e9'
down_revision = 'a7c2e9d4b1f6'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'page',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('slug', sa.String(120), nullable=False),
        sa.Column('kind', sa.String(20), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )
    op.create_index('ix_page_slug', 'page', ['slug'], unique=True)
    op.create_table(
        'page_text',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('page_id', sa.Integer(), sa.ForeignKey('page.id', ondelete='CASCADE'), nullable=False),
        sa.Column('lang', sa.String(5), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('hero_image', sa.String(300), nullable=True),
        sa.Column('blocks', sa.JSON(), nullable=False),
        sa.Column('note', sa.String(200), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('published_at', sa.DateTime(), nullable=True),
        sa.UniqueConstraint('page_id', 'lang', 'version', name='uq_page_text_version'),
    )
    op.create_index('ix_page_text_page_id', 'page_text', ['page_id'])
    op.create_table(
        'page_embed',
        sa.Column('id', sa.String(32), primary_key=True),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('html', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )


def downgrade():
    op.drop_table('page_embed')
    op.drop_index('ix_page_text_page_id', table_name='page_text')
    op.drop_table('page_text')
    op.drop_index('ix_page_slug', table_name='page')
    op.drop_table('page')
