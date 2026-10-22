"""pantry: ground beef in the foundation pantry

c6e1a4d8b2f7 treated ground beef as missing, because the local copy of the pantry did not have it. Production
does (food_id 000011), so the migration only gave it its aliases (kjøttdeig and the rest) and left its tier.
Ground beef is in the foundation pantry v0 (RECIPE_MODEL_V2.md, "Grunnlager v0"); this sets its tier, matched
by name, and only when it is core.

Downgrade sets it back to core.

Revision ID: e2b9c4f7a1d6
Revises: 73ec0f99ab42
Create Date: 2026-10-22

"""
from alembic import op
import sqlalchemy as sa


revision = 'e2b9c4f7a1d6'
down_revision = '73ec0f99ab42'
branch_labels = None
depends_on = None


def upgrade():
    op.get_bind().execute(sa.text("UPDATE ingredient SET tier = 'foundation' WHERE lower(name) = 'ground beef' "
                                  "AND status = 'active' AND tier = 'core'"))


def downgrade():
    op.get_bind().execute(sa.text("UPDATE ingredient SET tier = 'core' WHERE lower(name) = 'ground beef' "
                                  "AND tier = 'foundation' AND data_source <> 'pantry-additions'"))
