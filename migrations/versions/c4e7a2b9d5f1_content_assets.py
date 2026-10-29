"""content: images a page names by file name

The images of guides, uploaded in Admin -> Pages under the page's slug (services/content/assets.py). Adds
content_asset; only a new table.

Downgrade drops it.

Revision ID: c4e7a2b9d5f1
Revises: b8d3f1a6c2e9
Create Date: 2026-10-29
"""
from alembic import op
import sqlalchemy as sa


revision = 'c4e7a2b9d5f1'
down_revision = 'b8d3f1a6c2e9'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'content_asset',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('slug', sa.String(120), nullable=False),
        sa.Column('name', sa.String(120), nullable=False),
        sa.Column('url', sa.String(500), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.UniqueConstraint('slug', 'name', name='uq_content_asset_name'),
    )
    op.create_index('ix_content_asset_slug', 'content_asset', ['slug'])


def downgrade():
    op.drop_index('ix_content_asset_slug', table_name='content_asset')
    op.drop_table('content_asset')
