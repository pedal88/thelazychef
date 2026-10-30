"""the measuring system a user chose: user.unit_system

'metric' or 'us', set by the switch in the site menu for a signed-in user (routes/_shared.unit_system), so the choice
follows them to other devices. Only adds an empty column.

Downgrade drops the column.

Revision ID: e6a2c9f4b8d1
Revises: d5f1a8c3e7b2
Create Date: 2026-10-30
"""
from alembic import op
import sqlalchemy as sa


revision = 'e6a2c9f4b8d1'
down_revision = 'd5f1a8c3e7b2'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('user') as batch_op:
        batch_op.add_column(sa.Column('unit_system', sa.String(length=10), nullable=True))


def downgrade():
    with op.batch_alter_table('user') as batch_op:
        batch_op.drop_column('unit_system')
