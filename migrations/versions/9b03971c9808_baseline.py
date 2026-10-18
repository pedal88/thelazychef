"""baseline: the whole schema as of 2026-10-18

Replaces the 34 earlier migrations. Eleven tables had been created by
db.create_all() and never had a migration, so the old chain could not
build an empty database.

This revision has the same ID as the last migration of the old chain
(9b03971c9808, "drop tables left by removed tools"). A database that ran
the old chain is already at this revision, so upgrade does nothing there.
An empty database gets the whole schema from this file. The old chain is
in git history.

Revision ID: 9b03971c9808
Revises:
Create Date: 2026-10-18

"""
import json
import os

from alembic import op
import sqlalchemy as sa
import pgvector.sqlalchemy


# revision identifiers, used by Alembic.
revision = '9b03971c9808'
down_revision = None
branch_labels = None
depends_on = None

CHEFS_JSON = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'agents', 'chefs.json')


def upgrade():
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table('chef',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('archetype', sa.String(), nullable=False),
    sa.Column('description', sa.Text(), nullable=False),
    sa.Column('image_filename', sa.String(), nullable=False),
    sa.Column('constraints', sa.Text(), nullable=False),
    sa.Column('diet_preferences', sa.Text(), nullable=False),
    sa.Column('cooking_style', sa.Text(), nullable=False),
    sa.Column('ingredient_logic', sa.Text(), nullable=False),
    sa.Column('instruction_style', sa.Text(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('concept_visual',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('concept_type', sa.String(length=50), nullable=False),
    sa.Column('concept_name', sa.String(length=100), nullable=False),
    sa.Column('image_url', sa.String(length=500), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('concept_type', 'concept_name', name='uq_concept_visual_type_name')
    )
    with op.batch_alter_table('concept_visual', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_concept_visual_concept_name'), ['concept_name'], unique=False)
        batch_op.create_index(batch_op.f('ix_concept_visual_concept_type'), ['concept_type'], unique=False)

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
    with op.batch_alter_table('recipe_collection', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_recipe_collection_slug'), ['slug'], unique=True)

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
    with op.batch_alter_table('resource', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_resource_slug'), ['slug'], unique=True)
        batch_op.create_index(batch_op.f('ix_resource_status'), ['status'], unique=False)

    op.create_table('user',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('email', sa.String(length=150), nullable=False),
    sa.Column('password_hash', sa.String(length=256), nullable=False),
    sa.Column('is_admin', sa.Boolean(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('email')
    )
    op.create_table('visual_style_guide',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('scope', sa.String(length=100), nullable=False),
    sa.Column('base_wrapper', sa.Text(), nullable=False),
    sa.Column('negative_prompt', sa.Text(), nullable=True),
    sa.Column('remove_background', sa.Boolean(), server_default='0', nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('visual_style_guide', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_visual_style_guide_scope'), ['scope'], unique=True)

    op.create_table('recipe',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('title', sa.String(), nullable=False),
    sa.Column('cuisine', sa.String(), nullable=False),
    sa.Column('difficulty', sa.String(), nullable=False),
    sa.Column('protein_type', sa.String(), nullable=True),
    sa.Column('image_filename', sa.String(), nullable=True),
    sa.Column('source_image_filename', sa.String(), nullable=True),
    sa.Column('base_servings', sa.Integer(), server_default='4', nullable=False),
    sa.Column('chef_id', sa.String(), nullable=True),
    sa.Column('is_flagged_for_review', sa.Boolean(), nullable=False),
    sa.Column('status', sa.String(length=20), server_default='draft', nullable=False),
    sa.Column('taste_level', sa.Integer(), nullable=True),
    sa.Column('prep_time_mins', sa.Integer(), nullable=True),
    sa.Column('cleanup_factor', sa.Integer(), nullable=True),
    sa.Column('source_input', sa.String(length=500), nullable=True),
    sa.Column('source_type', sa.String(length=50), server_default='manual', nullable=False),
    sa.Column('total_calories', sa.Float(), nullable=True),
    sa.Column('total_protein', sa.Float(), nullable=True),
    sa.Column('total_carbs', sa.Float(), nullable=True),
    sa.Column('total_fat', sa.Float(), nullable=True),
    sa.Column('total_saturated_fat', sa.Float(), nullable=True),
    sa.Column('total_fiber', sa.Float(), nullable=True),
    sa.Column('total_sugar', sa.Float(), nullable=True),
    sa.Column('total_cholesterol_mg', sa.Float(), nullable=True),
    sa.Column('total_sodium_mg', sa.Float(), nullable=True),
    sa.Column('total_calcium_mg', sa.Float(), nullable=True),
    sa.Column('total_potassium_mg', sa.Float(), nullable=True),
    sa.Column('component_images', sa.JSON(), server_default='{}', nullable=False),
    sa.Column('social_hooks', sa.JSON(), server_default='{}', nullable=False),
    sa.Column('primary_resource_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['chef_id'], ['chef.id'], ),
    sa.ForeignKeyConstraint(['primary_resource_id'], ['resource.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('recipe', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_recipe_is_flagged_for_review'), ['is_flagged_for_review'], unique=False)
        batch_op.create_index(batch_op.f('ix_recipe_status'), ['status'], unique=False)

    op.create_table('resource_relations',
    sa.Column('source_id', sa.Integer(), nullable=False),
    sa.Column('related_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['related_id'], ['resource.id'], ),
    sa.ForeignKeyConstraint(['source_id'], ['resource.id'], ),
    sa.PrimaryKeyConstraint('source_id', 'related_id')
    )
    op.create_table('user_link',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id_1', sa.Integer(), nullable=False),
    sa.Column('user_id_2', sa.Integer(), nullable=True),
    sa.Column('pairing_code', sa.String(length=10), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('is_default', sa.Boolean(), server_default='0', nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['user_id_1'], ['user.id'], ),
    sa.ForeignKeyConstraint(['user_id_2'], ['user.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_id_1', 'user_id_2', name='uq_user_link_pair')
    )
    with op.batch_alter_table('user_link', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_user_link_pairing_code'), ['pairing_code'], unique=True)

    op.create_table('collection_item',
    sa.Column('collection_id', sa.Integer(), nullable=False),
    sa.Column('recipe_id', sa.Integer(), nullable=False),
    sa.Column('added_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['collection_id'], ['recipe_collection.id'], ),
    sa.ForeignKeyConstraint(['recipe_id'], ['recipe.id'], ),
    sa.PrimaryKeyConstraint('collection_id', 'recipe_id')
    )
    op.create_table('ingredient',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('food_id', sa.String(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('main_category', sa.String(), nullable=True),
    sa.Column('sub_category', sa.String(), nullable=True),
    sa.Column('tags', sa.String(), nullable=True),
    sa.Column('default_unit', sa.String(), nullable=False),
    sa.Column('average_g_per_unit', sa.Float(), nullable=True),
    sa.Column('aliases', sa.Text(), nullable=False),
    sa.Column('is_staple', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.String(), nullable=True),
    sa.Column('status', sa.String(length=20), server_default='active', nullable=False),
    sa.Column('image_url', sa.String(), nullable=True),
    sa.Column('has_transparent_image', sa.Boolean(), server_default='0', nullable=False),
    sa.Column('image_prompt', sa.Text(), nullable=True),
    sa.Column('data_source', sa.String(length=50), server_default='placeholder', nullable=False),
    sa.Column('embedding', pgvector.sqlalchemy.vector.VECTOR(dim=768), nullable=True),
    sa.Column('calories_per_100g', sa.Float(), nullable=True),
    sa.Column('kj_per_100g', sa.Float(), nullable=True),
    sa.Column('protein_per_100g', sa.Float(), nullable=True),
    sa.Column('carbs_per_100g', sa.Float(), nullable=True),
    sa.Column('fat_per_100g', sa.Float(), nullable=True),
    sa.Column('fat_saturated_per_100g', sa.Float(), nullable=True),
    sa.Column('sugar_per_100g', sa.Float(), nullable=True),
    sa.Column('fiber_per_100g', sa.Float(), nullable=True),
    sa.Column('sodium_mg_per_100g', sa.Float(), nullable=True),
    sa.Column('cholesterol_mg_per_100g', sa.Float(), nullable=True),
    sa.Column('calcium_mg_per_100g', sa.Float(), nullable=True),
    sa.Column('potassium_mg_per_100g', sa.Float(), nullable=True),
    sa.Column('sub_recipe_id', sa.Integer(), nullable=True),
    sa.Column('primary_resource_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['primary_resource_id'], ['resource.id'], ),
    sa.ForeignKeyConstraint(['sub_recipe_id'], ['recipe.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('ingredient', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_ingredient_food_id'), ['food_id'], unique=True)
        batch_op.create_index(batch_op.f('ix_ingredient_name'), ['name'], unique=False)
        batch_op.create_index(batch_op.f('ix_ingredient_status'), ['status'], unique=False)

    op.create_table('instruction',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('recipe_id', sa.Integer(), nullable=False),
    sa.Column('phase', sa.String(), nullable=False),
    sa.Column('component', sa.String(length=100), nullable=False),
    sa.Column('step_number', sa.Integer(), nullable=False),
    sa.Column('text', sa.Text(), nullable=False),
    sa.Column('estimated_minutes', sa.Integer(), nullable=True),
    sa.Column('global_order_index', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['recipe_id'], ['recipe.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('recipe_diet',
    sa.Column('recipe_id', sa.Integer(), nullable=False),
    sa.Column('diet', sa.String(), nullable=False),
    sa.ForeignKeyConstraint(['recipe_id'], ['recipe.id'], ),
    sa.PrimaryKeyConstraint('recipe_id', 'diet')
    )
    op.create_table('recipe_evaluation',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('recipe_id', sa.Integer(), nullable=False),
    sa.Column('score_name', sa.Integer(), nullable=False),
    sa.Column('score_ingredients', sa.Integer(), nullable=False),
    sa.Column('score_components', sa.Integer(), nullable=False),
    sa.Column('score_amounts', sa.Integer(), nullable=False),
    sa.Column('score_steps', sa.Integer(), nullable=False),
    sa.Column('score_image', sa.Integer(), nullable=True),
    sa.Column('total_score', sa.Float(), nullable=False),
    sa.Column('evaluation_details', sa.JSON(), nullable=False),
    sa.ForeignKeyConstraint(['recipe_id'], ['recipe.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('recipe_id')
    )
    op.create_table('recipe_meal_type',
    sa.Column('recipe_id', sa.Integer(), nullable=False),
    sa.Column('meal_type', sa.String(), nullable=False),
    sa.ForeignKeyConstraint(['recipe_id'], ['recipe.id'], ),
    sa.PrimaryKeyConstraint('recipe_id', 'meal_type')
    )
    op.create_table('user_queue',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('recipe_id', sa.Integer(), nullable=False),
    sa.Column('position', sa.Integer(), nullable=False),
    sa.Column('added_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['recipe_id'], ['recipe.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_id', 'recipe_id', name='uq_user_queue_recipe')
    )
    with op.batch_alter_table('user_queue', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_user_queue_user_id'), ['user_id'], unique=False)

    op.create_table('user_recipe_interaction',
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('recipe_id', sa.Integer(), nullable=False),
    sa.Column('status', sa.String(), nullable=False),
    sa.Column('is_super_like', sa.Boolean(), nullable=False),
    sa.Column('timestamp', sa.DateTime(), nullable=False),
    sa.Column('is_made', sa.Boolean(), server_default='0', nullable=False),
    sa.Column('rating', sa.Integer(), nullable=True),
    sa.Column('comment', sa.Text(), nullable=True),
    sa.Column('user_photos', sa.JSON(), server_default='[]', nullable=False),
    sa.ForeignKeyConstraint(['recipe_id'], ['recipe.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
    sa.PrimaryKeyConstraint('user_id', 'recipe_id')
    )
    op.create_table('ingredient_evaluation',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('ingredient_id', sa.Integer(), nullable=False),
    sa.Column('score_image', sa.Integer(), nullable=True),
    sa.Column('score_nutrition', sa.Integer(), nullable=True),
    sa.Column('score_taxonomy', sa.Integer(), nullable=True),
    sa.Column('score_utility', sa.Integer(), nullable=True),
    sa.Column('score_commonness', sa.Integer(), nullable=True),
    sa.Column('total_score', sa.Float(), nullable=True),
    sa.Column('evaluation_details', sa.JSON(), nullable=False),
    sa.ForeignKeyConstraint(['ingredient_id'], ['ingredient.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('ingredient_id')
    )
    op.create_table('recipe_ingredient',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('recipe_id', sa.Integer(), nullable=False),
    sa.Column('ingredient_id', sa.Integer(), nullable=False),
    sa.Column('amount', sa.Float(), nullable=False),
    sa.Column('unit', sa.String(), nullable=False),
    sa.Column('prep_style', sa.String(), nullable=True),
    sa.Column('gram_weight', sa.Float(), nullable=True),
    sa.Column('component', sa.String(), nullable=False),
    sa.ForeignKeyConstraint(['ingredient_id'], ['ingredient.id'], ),
    sa.ForeignKeyConstraint(['recipe_id'], ['recipe.id'], ),
    sa.PrimaryKeyConstraint('id')
    )

    _seed_chefs()


def downgrade():
    op.drop_table('recipe_ingredient')
    op.drop_table('ingredient_evaluation')
    op.drop_table('user_recipe_interaction')
    with op.batch_alter_table('user_queue', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_user_queue_user_id'))

    op.drop_table('user_queue')
    op.drop_table('recipe_meal_type')
    op.drop_table('recipe_evaluation')
    op.drop_table('recipe_diet')
    op.drop_table('instruction')
    with op.batch_alter_table('ingredient', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_ingredient_status'))
        batch_op.drop_index(batch_op.f('ix_ingredient_name'))
        batch_op.drop_index(batch_op.f('ix_ingredient_food_id'))

    op.drop_table('ingredient')
    op.drop_table('collection_item')
    with op.batch_alter_table('user_link', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_user_link_pairing_code'))

    op.drop_table('user_link')
    op.drop_table('resource_relations')
    with op.batch_alter_table('recipe', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_recipe_status'))
        batch_op.drop_index(batch_op.f('ix_recipe_is_flagged_for_review'))

    op.drop_table('recipe')
    with op.batch_alter_table('visual_style_guide', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_visual_style_guide_scope'))

    op.drop_table('visual_style_guide')
    op.drop_table('user')
    with op.batch_alter_table('resource', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_resource_status'))
        batch_op.drop_index(batch_op.f('ix_resource_slug'))

    op.drop_table('resource')
    with op.batch_alter_table('recipe_collection', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_recipe_collection_slug'))

    op.drop_table('recipe_collection')
    with op.batch_alter_table('concept_visual', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_concept_visual_concept_type'))
        batch_op.drop_index(batch_op.f('ix_concept_visual_concept_name'))

    op.drop_table('concept_visual')
    op.drop_table('chef')


def _seed_chefs():
    """Insert the chefs from data/agents/chefs.json (the old chain did this
    in f2300672909e). Only inserts missing chefs; never changes a row."""
    chef_table = sa.table(
        'chef',
        sa.column('id', sa.String), sa.column('name', sa.String),
        sa.column('archetype', sa.String), sa.column('description', sa.Text),
        sa.column('image_filename', sa.String), sa.column('constraints', sa.Text),
        sa.column('diet_preferences', sa.Text), sa.column('cooking_style', sa.Text),
        sa.column('ingredient_logic', sa.Text), sa.column('instruction_style', sa.Text),
    )
    try:
        with open(CHEFS_JSON) as f:
            chefs = json.load(f)['chefs']
    except (OSError, ValueError, KeyError) as e:
        print(f"Skipping chef seed, could not read {CHEFS_JSON}: {e}")
        return

    existing = {row[0] for row in op.get_bind().execute(sa.select(chef_table.c.id))}
    rows = [
        {
            'id': c['id'],
            'name': c['name'],
            'archetype': c.get('archetype'),
            'description': c.get('description'),
            'image_filename': c.get('image_filename'),
            'constraints': json.dumps(c.get('constraints', {})),
            'diet_preferences': json.dumps(c.get('diet_preferences', [])),
            'cooking_style': json.dumps(c.get('cooking_style', {})),
            'ingredient_logic': json.dumps(c.get('ingredient_logic', {})),
            'instruction_style': json.dumps(c.get('instruction_style', {})),
        }
        for c in chefs if c['id'] not in existing
    ]
    if rows:
        op.bulk_insert(chef_table, rows)
