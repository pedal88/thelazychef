"""the post log's variant fields: round, series and number, hook and CTA group, recipes, views, look, slides, slot

social_post gets the fields the trial plan reads a post by (docs/SOCIAL.md "Learning from the posts",
services/funnel.py): the round of the plan, the series slug and the post's number in it, the hook group (the words
stay in hook), the CTA group, every recipe in the post, the slide kinds used, the look, how many slides and the time
of day it went up. Only adds nullable columns; no row changes.

Downgrade drops them.

Revision ID: b8d4f2a6c9e1
Revises: e3a9c5f7b1d2
Create Date: 2026-10-31
"""
from alembic import op
import sqlalchemy as sa


revision = 'b8d4f2a6c9e1'
down_revision = 'e3a9c5f7b1d2'
branch_labels = None
depends_on = None

COLUMNS = [
    ('round', sa.String(length=40)),
    ('series', sa.String(length=40)),
    ('series_n', sa.Integer()),
    ('hook_group', sa.String(length=20)),
    ('cta_group', sa.String(length=20)),
    ('recipe_ids', sa.String(length=200)),
    ('views', sa.String(length=300)),
    ('look', sa.String(length=10)),
    ('slides', sa.Integer()),
    ('slot', sa.String(length=20)),
]


def upgrade():
    with op.batch_alter_table('social_post') as batch:
        for name, kind in COLUMNS:
            batch.add_column(sa.Column(name, kind, nullable=True))


def downgrade():
    with op.batch_alter_table('social_post') as batch:
        for name, _ in reversed(COLUMNS):
            batch.drop_column(name)
