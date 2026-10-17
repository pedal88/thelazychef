"""Seed missing chefs from data/agents/chefs.json

The chef editor now saves to the chef table instead of a JSON file, so the
table is the source of truth. This copies chefs that exist in the JSON file but
not in the table. It only inserts: existing rows are never changed, and
downgrade removes nothing.

Revision ID: f2300672909e
Revises: 698f1c8b3e3d
Create Date: 2026-10-01 12:00:00

"""
import json
import os

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f2300672909e'
down_revision = '698f1c8b3e3d'
branch_labels = None
depends_on = None

CHEFS_JSON = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'agents', 'chefs.json')

chef_table = sa.table(
    'chef',
    sa.column('id', sa.String),
    sa.column('name', sa.String),
    sa.column('archetype', sa.String),
    sa.column('description', sa.Text),
    sa.column('image_filename', sa.String),
    sa.column('constraints', sa.Text),
    sa.column('diet_preferences', sa.Text),
    sa.column('cooking_style', sa.Text),
    sa.column('ingredient_logic', sa.Text),
    sa.column('instruction_style', sa.Text),
)


def upgrade():
    try:
        with open(CHEFS_JSON) as f:
            chefs = json.load(f)['chefs']
    except (OSError, ValueError, KeyError) as e:
        print(f"Skipping chef seed, could not read {CHEFS_JSON}: {e}")
        return

    conn = op.get_bind()
    existing = {row[0] for row in conn.execute(sa.select(chef_table.c.id))}
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
    print(f"Seeded {len(rows)} chef(s): {[r['id'] for r in rows]}")


def downgrade():
    # Chefs may have been edited or referenced by recipes since; leave them.
    pass
