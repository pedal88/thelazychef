"""chefs: time limits that hold

The chef trial (scripts/chef_trial.py, 22.10.2026) broke the time limits in all eight recipes that had one, by
6 to 20 minutes: the model plans optimistically, and the planner also counts preheating and bringing water to the
boil. The limits now match what a cook meets: The Smart Cook 60 minutes (was 45), The Minimalist 35 minutes in
all (was 25) and at most 15 minutes of hands-on work (new: max_active_minutes).

Only the two chefs' constraints change. Downgrade puts back 45 and 25 and removes max_active_minutes.

Revision ID: a9c3e7f1b5d2
Revises: f4a8c2e6b9d1
Create Date: 2026-10-22

"""
import json

from alembic import op
import sqlalchemy as sa


revision = 'a9c3e7f1b5d2'
down_revision = 'f4a8c2e6b9d1'
branch_labels = None
depends_on = None

NEW = {'the_smart_cook': {'max_total_minutes': 60}, 'the_minimalist': {'max_total_minutes': 35, 'max_active_minutes': 15}}
OLD = {'the_smart_cook': {'max_total_minutes': 45}, 'the_minimalist': {'max_total_minutes': 25, 'max_active_minutes': None}}


def _set(values):
    conn = op.get_bind()
    for chef_id, change in values.items():
        row = conn.execute(sa.text('SELECT constraints FROM chef WHERE id = :i'), {'i': chef_id}).first()
        if row is None:
            continue
        rules = json.loads(row[0] or '{}')
        for key, value in change.items():
            if value is None:
                rules.pop(key, None)
            else:
                rules[key] = value
        conn.execute(sa.text('UPDATE chef SET constraints = :c WHERE id = :i'), {'c': json.dumps(rules), 'i': chef_id})


def upgrade():
    _set(NEW)


def downgrade():
    _set(OLD)
