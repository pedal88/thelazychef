"""meta learner image

The Meta-Learner's picture is static/chefs/meta_learner.png, but the chef row
has pointed at meta_learner.jpg since it was seeded, so the picture never
showed. Only that value is changed.

Revision ID: 8c4f1e2a6b93
Revises: 5e2a9b7c3d18
Create Date: 2026-10-20

"""
from alembic import op
import sqlalchemy as sa


revision = '8c4f1e2a6b93'
down_revision = '5e2a9b7c3d18'
branch_labels = None
depends_on = None


def upgrade():
    op.get_bind().execute(sa.text(
        "UPDATE chef SET image_filename = 'meta_learner.png' WHERE id = 'meta_learner' AND image_filename = 'meta_learner.jpg'"))


def downgrade():
    op.get_bind().execute(sa.text(
        "UPDATE chef SET image_filename = 'meta_learner.jpg' WHERE id = 'meta_learner' AND image_filename = 'meta_learner.png'"))
