"""the weekly report on the posts

social_report keeps, per week, the numbers the report was written from and what Claude read out of them
(services/social_report.py). Only adds a table.

Downgrade drops it.

Revision ID: f6c2a8d4e1b7
Revises: e5b9d3f7a2c4
Create Date: 2026-11-02
"""
from alembic import op
import sqlalchemy as sa


revision = 'f6c2a8d4e1b7'
down_revision = 'e5b9d3f7a2c4'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'social_report',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('week_ending', sa.Date(), nullable=False),
        sa.Column('written_at', sa.DateTime(), nullable=False),
        sa.Column('facts', sa.JSON(), nullable=False),
        sa.Column('report', sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('week_ending'),
    )


def downgrade():
    op.drop_table('social_report')
