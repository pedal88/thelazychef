"""drop tables left by removed tools

Media Hub, TikTok Sidecar and Style Center were removed in PR #40 and
#42. This drops their tables (social_media_post, sequence_template,
tiktok_source, style_sandbox_run, style_sandbox_preset), the old
system_config table and two unused concept_visual columns. The data is
deleted for good; the six TikTok links were exported first.

Downgrade recreates the empty tables, not the data.

Revision ID: 9b03971c9808
Revises: f2300672909e
Create Date: 2026-10-18 10:44:56.401818

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '9b03971c9808'
down_revision = 'f2300672909e'
branch_labels = None
depends_on = None


def upgrade():
    op.drop_table('system_config')
    with op.batch_alter_table('social_media_post', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_social_media_post_recipe_id'))

    op.drop_table('social_media_post')
    with op.batch_alter_table('style_sandbox_run', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_style_sandbox_run_preset_name'))
        batch_op.drop_index(batch_op.f('ix_style_sandbox_run_scope'))
        batch_op.drop_index(batch_op.f('ix_style_sandbox_run_test_item'))

    op.drop_table('style_sandbox_run')
    with op.batch_alter_table('style_sandbox_preset', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_style_sandbox_preset_name'))
        batch_op.drop_index(batch_op.f('ix_style_sandbox_preset_scope'))

    op.drop_table('style_sandbox_preset')
    with op.batch_alter_table('sequence_template', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_sequence_template_name'))

    op.drop_table('sequence_template')
    with op.batch_alter_table('tiktok_source', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_tiktok_source_tiktok_url'))

    op.drop_table('tiktok_source')
    with op.batch_alter_table('concept_visual', schema=None) as batch_op:
        batch_op.drop_column('image_prompt')
        batch_op.drop_column('image_model')



def downgrade():
    with op.batch_alter_table('concept_visual', schema=None) as batch_op:
        batch_op.add_column(sa.Column('image_model', sa.VARCHAR(length=100), autoincrement=False, nullable=True))
        batch_op.add_column(sa.Column('image_prompt', sa.TEXT(), autoincrement=False, nullable=True))

    op.create_table('tiktok_source',
    sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
    sa.Column('tiktok_url', sa.VARCHAR(length=500), autoincrement=False, nullable=False),
    sa.Column('dish_name', sa.VARCHAR(length=200), autoincrement=False, nullable=True),
    sa.Column('entity_type', sa.VARCHAR(length=50), server_default=sa.text("'NO_MATCH'::character varying"), autoincrement=False, nullable=False),
    sa.Column('format_type', sa.VARCHAR(length=50), server_default=sa.text("'UNKNOWN'::character varying"), autoincrement=False, nullable=False),
    sa.Column('status', sa.VARCHAR(length=50), server_default=sa.text("'SUGGESTED'::character varying"), autoincrement=False, nullable=False),
    sa.Column('raw_caption', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('created_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('tiktok_source_pkey'))
    )
    with op.batch_alter_table('tiktok_source', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_tiktok_source_tiktok_url'), ['tiktok_url'], unique=True)

    op.create_table('sequence_template',
    sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
    sa.Column('name', sa.VARCHAR(length=100), autoincrement=False, nullable=False),
    sa.Column('fragments_sequence', postgresql.JSON(astext_type=sa.Text()), server_default=sa.text("'[]'::json"), autoincrement=False, nullable=False),
    sa.Column('created_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('sequence_template_pkey'))
    )
    with op.batch_alter_table('sequence_template', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_sequence_template_name'), ['name'], unique=True)

    op.create_table('style_sandbox_preset',
    sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
    sa.Column('scope', sa.VARCHAR(length=100), server_default=sa.text("'ingredient'::character varying"), autoincrement=False, nullable=False),
    sa.Column('name', sa.VARCHAR(length=100), autoincrement=False, nullable=False),
    sa.Column('prompt', sa.TEXT(), autoincrement=False, nullable=False),
    sa.Column('order_index', sa.INTEGER(), server_default=sa.text('0'), autoincrement=False, nullable=False),
    sa.Column('negative_prompt', sa.TEXT(), autoincrement=False, nullable=True),
    sa.PrimaryKeyConstraint('id', name=op.f('style_sandbox_preset_pkey')),
    sa.UniqueConstraint('scope', 'name', name=op.f('uq_style_sandbox_preset_scope_name'), postgresql_include=[], postgresql_nulls_not_distinct=False)
    )
    with op.batch_alter_table('style_sandbox_preset', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_style_sandbox_preset_scope'), ['scope'], unique=False)
        batch_op.create_index(batch_op.f('ix_style_sandbox_preset_name'), ['name'], unique=True)

    op.create_table('style_sandbox_run',
    sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
    sa.Column('scope', sa.VARCHAR(length=100), autoincrement=False, nullable=False),
    sa.Column('preset_name', sa.VARCHAR(length=100), autoincrement=False, nullable=False),
    sa.Column('test_item', sa.VARCHAR(length=100), autoincrement=False, nullable=False),
    sa.Column('image_url', sa.VARCHAR(length=500), autoincrement=False, nullable=False),
    sa.Column('prompt_used', sa.TEXT(), autoincrement=False, nullable=False),
    sa.Column('model_used', sa.VARCHAR(length=100), autoincrement=False, nullable=False),
    sa.Column('timestamp', postgresql.TIMESTAMP(), autoincrement=False, nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('style_sandbox_run_pkey'))
    )
    with op.batch_alter_table('style_sandbox_run', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_style_sandbox_run_test_item'), ['test_item'], unique=False)
        batch_op.create_index(batch_op.f('ix_style_sandbox_run_scope'), ['scope'], unique=False)
        batch_op.create_index(batch_op.f('ix_style_sandbox_run_preset_name'), ['preset_name'], unique=False)

    op.create_table('social_media_post',
    sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
    sa.Column('recipe_id', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.Column('platform', sa.VARCHAR(length=20), autoincrement=False, nullable=False),
    sa.Column('status', sa.VARCHAR(length=20), autoincrement=False, nullable=False),
    sa.Column('template_name', sa.VARCHAR(length=100), autoincrement=False, nullable=False),
    sa.Column('voiceover_script', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('video_url', sa.VARCHAR(length=500), autoincrement=False, nullable=True),
    sa.Column('error_message', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('created_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=False),
    sa.ForeignKeyConstraint(['recipe_id'], ['recipe.id'], name=op.f('social_media_post_recipe_id_fkey')),
    sa.PrimaryKeyConstraint('id', name=op.f('social_media_post_pkey')),
    sa.UniqueConstraint('recipe_id', 'platform', 'template_name', name=op.f('uq_social_recipe_platform_template'), postgresql_include=[], postgresql_nulls_not_distinct=False)
    )
    with op.batch_alter_table('social_media_post', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_social_media_post_recipe_id'), ['recipe_id'], unique=False)

    op.create_table('system_config',
    sa.Column('key', sa.VARCHAR(length=100), autoincrement=False, nullable=False),
    sa.Column('value', sa.TEXT(), autoincrement=False, nullable=True),
    sa.PrimaryKeyConstraint('key', name=op.f('system_config_pkey'))
    )
