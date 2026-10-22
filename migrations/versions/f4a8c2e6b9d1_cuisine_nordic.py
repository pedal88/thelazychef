"""cuisine: Norwegian becomes Nordic

The cuisine list changes (decided 22.10.2026, data/constraints/graph_metadata.json): Nordic replaces Norwegian
and also takes the Swedish and Danish dishes common in Norway; Middle Eastern and Eastern European are new;
Mediterranean, Spanish and Vietnamese are no longer offered (Mediterranean overlapped Italian, Greek and Spanish;
Spanish and Vietnamese are little cooked in Norwegian homes, and their ingredients are covered by others).
Mexican now includes Tex-Mex; the value stays "Mexican".

Recipes with cuisine Norwegian are renamed Nordic. Recipes with Mediterranean, Spanish or Vietnamese keep them:
they still show with their flag (retired_cuisines), but are not offered for new recipes.

Downgrade renames Nordic back to Norwegian (also on recipes made as Nordic after the upgrade).

Revision ID: f4a8c2e6b9d1
Revises: e2b9c4f7a1d6
Create Date: 2026-10-22

"""
from alembic import op
import sqlalchemy as sa


revision = 'f4a8c2e6b9d1'
down_revision = 'e2b9c4f7a1d6'
branch_labels = None
depends_on = None


def upgrade():
    op.get_bind().execute(sa.text("UPDATE recipe SET cuisine = 'Nordic' WHERE cuisine = 'Norwegian'"))


def downgrade():
    op.get_bind().execute(sa.text("UPDATE recipe SET cuisine = 'Norwegian' WHERE cuisine = 'Nordic'"))
