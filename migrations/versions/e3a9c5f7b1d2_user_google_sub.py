"""sign in with Google: user.google_sub

The Google account a user signs in with (services/google_signin.py), by its "sub", which stays the same when the
address changes. Only adds an empty column with a unique constraint; no row changes.

Downgrade drops the constraint and the column.

Revision ID: e3a9c5f7b1d2
Revises: a7c3e9d1f5b8
Create Date: 2026-10-31
"""
from alembic import op
import sqlalchemy as sa


revision = 'e3a9c5f7b1d2'
down_revision = 'a7c3e9d1f5b8'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('user') as batch_op:
        batch_op.add_column(sa.Column('google_sub', sa.String(length=255), nullable=True))
        batch_op.create_unique_constraint('uq_user_google_sub', ['google_sub'])


def downgrade():
    with op.batch_alter_table('user') as batch_op:
        batch_op.drop_constraint('uq_user_google_sub', type_='unique')
        batch_op.drop_column('google_sub')
