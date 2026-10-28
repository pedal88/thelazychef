"""drop recipe_line.cut

The cut column is from before the state catalog (26.10.2026). Where it was right it was converted to the state
(scripts/convert_states.py, run on prod 27.10.2026: "from the cut: 0" lines left to convert), and the app has not
read or written it since #182. Dropping it removes no information the app uses.

Downgrade adds the column back, empty.

Revision ID: c5e8a1d3f9b2
Revises: b3d7e9f1a2c4
Create Date: 2026-10-28
"""
from alembic import op
import sqlalchemy as sa


revision = 'c5e8a1d3f9b2'
down_revision = 'b3d7e9f1a2c4'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('recipe_line') as batch_op:
        batch_op.drop_column('cut')


def downgrade():
    with op.batch_alter_table('recipe_line') as batch_op:
        batch_op.add_column(sa.Column('cut', sa.String(length=20), nullable=True))
