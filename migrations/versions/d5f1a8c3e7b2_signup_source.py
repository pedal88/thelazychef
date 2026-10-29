"""where users come from: signup time, source and ref, and visits per ref code

The funnel for TikTok and Instagram (services/funnel.py, routes/funnel_routes.py): user gets created_at, signup_source
(the answer to "How did you find us?") and signup_ref (the first ref code the visit brought), and referral_visit counts
visits per ref code and day. Only adds a table and empty columns; users from before have no created_at.

Downgrade drops the table and the three columns.

Revision ID: d5f1a8c3e7b2
Revises: c4e7a2b9d5f1
Create Date: 2026-10-29
"""
from alembic import op
import sqlalchemy as sa


revision = 'd5f1a8c3e7b2'
down_revision = 'c4e7a2b9d5f1'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('user') as batch_op:
        batch_op.add_column(sa.Column('created_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('signup_source', sa.String(length=30), nullable=True))
        batch_op.add_column(sa.Column('signup_ref', sa.String(length=60), nullable=True))
    op.create_table(
        'referral_visit',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('ref', sa.String(length=60), nullable=False),
        sa.Column('day', sa.Date(), nullable=False),
        sa.Column('count', sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('ref', 'day', name='uq_referral_visit_day'),
    )


def downgrade():
    op.drop_table('referral_visit')
    with op.batch_alter_table('user') as batch_op:
        batch_op.drop_column('signup_ref')
        batch_op.drop_column('signup_source')
        batch_op.drop_column('created_at')
