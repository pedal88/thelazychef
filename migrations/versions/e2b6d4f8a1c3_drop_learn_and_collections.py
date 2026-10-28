"""drop Learn (resource) and collections

Learn (the articles in the resource tables) and the curated collections are removed from the app (28.10.2026); guides
will be built again from scratch. Pål chose to drop the rows without a backup. This drops resource,
resource_relations, recipe_collection, collection_item and the unused primary_resource_id on ingredient and recipe.

Downgrade puts the tables and columns back, empty.

Revision ID: e2b6d4f8a1c3
Revises: c5e8a1d3f9b2
Create Date: 2026-10-28
"""
from alembic import op
import sqlalchemy as sa


revision = 'e2b6d4f8a1c3'
down_revision = 'c5e8a1d3f9b2'
branch_labels = None
depends_on = None


def upgrade():
    inspector = sa.inspect(op.get_bind())
    for table in ('ingredient', 'recipe'):
        names = [fk['name'] for fk in inspector.get_foreign_keys(table)
                 if fk['constrained_columns'] == ['primary_resource_id'] and fk['name']]
        with op.batch_alter_table(table) as batch_op:
            for name in names:
                batch_op.drop_constraint(name, type_='foreignkey')
            batch_op.drop_column('primary_resource_id')

    op.drop_table('resource_relations')
    op.drop_table('collection_item')
    with op.batch_alter_table('resource') as batch_op:
        batch_op.drop_index('ix_resource_status')
        batch_op.drop_index('ix_resource_slug')
    op.drop_table('resource')
    with op.batch_alter_table('recipe_collection') as batch_op:
        batch_op.drop_index('ix_recipe_collection_slug')
    op.drop_table('recipe_collection')


def downgrade():
    op.create_table('recipe_collection',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('title', sa.String(length=150), nullable=False),
    sa.Column('slug', sa.String(length=150), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('image_filename', sa.String(length=255), nullable=True),
    sa.Column('is_published', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('recipe_collection') as batch_op:
        batch_op.create_index('ix_recipe_collection_slug', ['slug'], unique=True)

    op.create_table('resource',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('slug', sa.String(length=100), nullable=False),
    sa.Column('title', sa.String(length=200), nullable=False),
    sa.Column('summary', sa.String(length=500), nullable=True),
    sa.Column('content_markdown', sa.Text(), nullable=True),
    sa.Column('image_filename', sa.String(length=255), nullable=True),
    sa.Column('tags', sa.String(length=255), nullable=True),
    sa.Column('status', sa.String(length=20), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('resource') as batch_op:
        batch_op.create_index('ix_resource_slug', ['slug'], unique=True)
        batch_op.create_index('ix_resource_status', ['status'], unique=False)

    op.create_table('collection_item',
    sa.Column('collection_id', sa.Integer(), nullable=False),
    sa.Column('recipe_id', sa.Integer(), nullable=False),
    sa.Column('added_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['collection_id'], ['recipe_collection.id'], name='collection_item_collection_id_fkey',
                            ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['recipe_id'], ['recipe.id'], name='collection_item_recipe_id_fkey', ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('collection_id', 'recipe_id')
    )
    op.create_table('resource_relations',
    sa.Column('source_id', sa.Integer(), nullable=False),
    sa.Column('related_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['related_id'], ['resource.id'], name='resource_relations_related_id_fkey',
                            ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['source_id'], ['resource.id'], name='resource_relations_source_id_fkey',
                            ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('source_id', 'related_id')
    )

    for table in ('ingredient', 'recipe'):
        with op.batch_alter_table(table) as batch_op:
            batch_op.add_column(sa.Column('primary_resource_id', sa.Integer(), nullable=True))
            batch_op.create_foreign_key(f'{table}_primary_resource_id_fkey', 'resource', ['primary_resource_id'],
                                        ['id'], ondelete='SET NULL')
