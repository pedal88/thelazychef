"""pantry: the staple tier

The pantry's lowest level (RECIPE_MODEL_V2.md, "Kjerne og lang hale"): what every user is assumed to have,
so the recipe pages put it under "You probably have" instead of on the shopping list. Decided 22.10.2026:
water, salt, black pepper, neutral oil, olive oil, sugar and wheat flour. These are core ingredients today;
they move one step down the ladder staple < foundation < core < long_tail. Only the tier changes, matched by
name, and a name the pantry does not have is skipped.

is_staple is left as it is: the v1 generation reads it.

Downgrade sets them back to core.

Revision ID: a3d7f2c9e1b6
Revises: f1c3a8e2b7d4
Create Date: 2026-10-22

"""
from alembic import op
import sqlalchemy as sa


revision = 'a3d7f2c9e1b6'
down_revision = 'f1c3a8e2b7d4'
branch_labels = None
depends_on = None

STAPLES = ('water', 'table salt', 'sea salt', 'ground black pepper', 'black peppercorns', 'canola oil', 'sunflower oil',
           'olive oil', 'extra virgin olive oil', 'white sugar', 'all-purpose flour')


def upgrade():
    op.get_bind().execute(sa.text("UPDATE ingredient SET tier = 'staple' WHERE lower(name) IN :names AND status = 'active'")
                          .bindparams(sa.bindparam('names', expanding=True)), {'names': list(STAPLES)})


def downgrade():
    op.get_bind().execute(sa.text("UPDATE ingredient SET tier = 'core' WHERE lower(name) IN :names AND tier = 'staple'")
                          .bindparams(sa.bindparam('names', expanding=True)), {'names': list(STAPLES)})
