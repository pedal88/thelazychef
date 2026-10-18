"""cascade deletes and ingredient aliases

1. Foreign keys get ON DELETE rules, so the database itself removes child
   rows when a recipe, ingredient, collection, user or resource is deleted
   (CASCADE), and clears optional links (SET NULL). recipe.chef_id and
   recipe_ingredient.ingredient_id keep blocking deletes on purpose.
2. Aliases move from the JSON column ingredient.aliases to the new table
   ingredient_alias, and the column is dropped.

Existing foreign keys are looked up by table, column and referred table
instead of by name, because constraint names in production may differ
from a database built from the baseline.

Revision ID: 2f46e44cc1ae
Revises: 9b03971c9808
Create Date: 2026-10-18

"""
import datetime
import json

from alembic import op
import sqlalchemy as sa


revision = '2f46e44cc1ae'
down_revision = '9b03971c9808'
branch_labels = None
depends_on = None

# (table, column, referred table, ON DELETE)
FK_RULES = [
    ('collection_item', 'collection_id', 'recipe_collection', 'CASCADE'),
    ('collection_item', 'recipe_id', 'recipe', 'CASCADE'),
    ('ingredient', 'primary_resource_id', 'resource', 'SET NULL'),
    ('ingredient', 'sub_recipe_id', 'recipe', 'SET NULL'),
    ('ingredient_evaluation', 'ingredient_id', 'ingredient', 'CASCADE'),
    ('instruction', 'recipe_id', 'recipe', 'CASCADE'),
    ('recipe', 'primary_resource_id', 'resource', 'SET NULL'),
    ('recipe_diet', 'recipe_id', 'recipe', 'CASCADE'),
    ('recipe_evaluation', 'recipe_id', 'recipe', 'CASCADE'),
    ('recipe_ingredient', 'recipe_id', 'recipe', 'CASCADE'),
    ('recipe_meal_type', 'recipe_id', 'recipe', 'CASCADE'),
    ('resource_relations', 'source_id', 'resource', 'CASCADE'),
    ('resource_relations', 'related_id', 'resource', 'CASCADE'),
    ('user_link', 'user_id_1', 'user', 'CASCADE'),
    ('user_link', 'user_id_2', 'user', 'CASCADE'),
    ('user_queue', 'user_id', 'user', 'CASCADE'),
    ('user_queue', 'recipe_id', 'recipe', 'CASCADE'),
    ('user_recipe_interaction', 'user_id', 'user', 'CASCADE'),
    ('user_recipe_interaction', 'recipe_id', 'recipe', 'CASCADE'),
]

ingredient = sa.table(
    'ingredient',
    sa.column('id', sa.Integer),
    sa.column('name', sa.String),
    sa.column('aliases', sa.Text),
)
ingredient_alias = sa.table(
    'ingredient_alias',
    sa.column('ingredient_id', sa.Integer),
    sa.column('name', sa.String),
    sa.column('created_at', sa.DateTime),
)


def _normalize(name):
    return " ".join((name or "").split()).lower()


def _set_ondelete(rules):
    inspector = sa.inspect(op.get_bind())
    for table, column, referred, ondelete in rules:
        for fk in inspector.get_foreign_keys(table):
            if fk['constrained_columns'] == [column] and fk['referred_table'] == referred:
                op.drop_constraint(fk['name'], table, type_='foreignkey')
        op.create_foreign_key(f'{table}_{column}_fkey', table, referred, [column], ['id'], ondelete=ondelete)


def upgrade():
    op.create_table(
        'ingredient_alias',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('ingredient_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['ingredient_id'], ['ingredient.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
    )
    op.create_index('ix_ingredient_alias_ingredient_id', 'ingredient_alias', ['ingredient_id'], unique=False)

    # Copy the JSON aliases. The first ingredient to claim an alias keeps it;
    # aliases equal to the ingredient's own name are skipped.
    bind = op.get_bind()
    now = datetime.datetime.utcnow()
    seen, rows = set(), []
    for ing_id, name, raw in bind.execute(sa.select(ingredient.c.id, ingredient.c.name, ingredient.c.aliases).order_by(ingredient.c.id)):
        try:
            values = json.loads(raw) if raw else []
        except (TypeError, ValueError):
            values = [raw]
        if not isinstance(values, list):
            values = [values]
        for value in values:
            alias = _normalize(str(value))
            if alias and alias != _normalize(name) and alias not in seen and len(alias) <= 200:
                seen.add(alias)
                rows.append({'ingredient_id': ing_id, 'name': alias, 'created_at': now})
    if rows:
        op.bulk_insert(ingredient_alias, rows)
    print(f"Copied {len(rows)} aliases to ingredient_alias")

    op.drop_column('ingredient', 'aliases')
    _set_ondelete(FK_RULES)


def downgrade():
    _set_ondelete([(t, c, r, None) for t, c, r, _ in FK_RULES])

    op.add_column('ingredient', sa.Column('aliases', sa.Text(), nullable=False, server_default='[]'))
    bind = op.get_bind()
    by_ingredient = {}
    for ing_id, name in bind.execute(sa.select(ingredient_alias.c.ingredient_id, ingredient_alias.c.name)):
        by_ingredient.setdefault(ing_id, []).append(name)
    for ing_id, names in by_ingredient.items():
        bind.execute(ingredient.update().where(ingredient.c.id == ing_id).values(aliases=json.dumps(names)))

    op.drop_index('ix_ingredient_alias_ingredient_id', table_name='ingredient_alias')
    op.drop_table('ingredient_alias')
