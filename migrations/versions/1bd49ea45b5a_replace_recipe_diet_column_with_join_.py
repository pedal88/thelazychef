"""replace_recipe_diet_column_with_join_table

Revision ID: 1bd49ea45b5a
Revises: cdb09877fc20
Create Date: 2026-02-21 10:13:06.955392

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '1bd49ea45b5a'
down_revision = 'cdb09877fc20'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = inspector.get_table_names()

    # Create the new recipe_diet join table (only if absent)
    if 'recipe_diet' not in existing_tables:
        op.create_table(
            'recipe_diet',
            sa.Column('recipe_id', sa.Integer(), sa.ForeignKey('recipe.id'), primary_key=True),
            sa.Column('diet', sa.String(), primary_key=True),
        )

    # Drop the old scalar column (only if still present)
    cols = [c['name'] for c in inspector.get_columns('recipe')]
    if 'diet' in cols:
        with op.batch_alter_table('recipe', schema=None) as batch_op:
            batch_op.drop_column('diet')


def downgrade():
    # Re-add the scalar column (nullable to avoid breaking existing rows)
    with op.batch_alter_table('recipe', schema=None) as batch_op:
        batch_op.add_column(sa.Column('diet', sa.VARCHAR(), nullable=True))

    # Drop the join table
    op.drop_table('recipe_diet')
