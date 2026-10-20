"""pantry: green peas

Green (garden) peas, fresh or frozen, are a core ingredient the pantry lacks:
only canned peas, snow peas, sugar snap peas and split peas are there. Recipe
290 got no nutrition because its frozen peas matched nothing. Added like
938d10ac6005: active, tier core, the next free food_id, with the aliases
"frozen peas", "peas" and "garden peas" when no other ingredient has them.
Nutrition and symbol follow in a later migration.

Downgrade removes it again (set inactive instead if a recipe uses it).

Revision ID: d61b3a9e4f27
Revises: 8c4f1e2a6b93
Create Date: 2026-10-20

"""
import datetime

from alembic import op
import sqlalchemy as sa


revision = 'd61b3a9e4f27'
down_revision = '8c4f1e2a6b93'
branch_labels = None
depends_on = None

SOURCE = 'pantry-additions'
NAME, MAIN, SUB = 'green peas', 'vegetables', 'podded vegetables'
ALIASES = ('frozen peas', 'peas', 'garden peas')


def _q(conn, sql, **params):
    return conn.execute(sa.text(sql), params)


def upgrade():
    conn = op.get_bind()
    if _q(conn, 'SELECT 1 FROM ingredient WHERE lower(name) = :n', n=NAME).first():
        return
    number = max((int(f) for (f,) in _q(conn, 'SELECT food_id FROM ingredient').all() if f and f.isdigit()), default=0) + 1
    _q(conn, "INSERT INTO ingredient (food_id, name, main_category, sub_category, default_unit, is_staple, "
             "has_transparent_image, status, tier, data_source, created_at) "
             "VALUES (:f, :n, :m, :s, 'g', :no, :no, 'active', 'core', :src, :t)",
       f=f'{number:06d}', n=NAME, m=MAIN, s=SUB, no=False, src=SOURCE, t=datetime.date.today().isoformat())
    new_id = _q(conn, 'SELECT id FROM ingredient WHERE food_id = :f', f=f'{number:06d}').scalar()
    now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
    for alias in ALIASES:
        if not _q(conn, 'SELECT 1 FROM ingredient_alias WHERE lower(name) = :n', n=alias).first():
            _q(conn, 'INSERT INTO ingredient_alias (ingredient_id, name, created_at) VALUES (:i, :n, :t)', i=new_id, n=alias, t=now)


def downgrade():
    conn = op.get_bind()
    for (i,) in _q(conn, 'SELECT id FROM ingredient WHERE lower(name) = :n AND data_source = :s', n=NAME, s=SOURCE).all():
        used = _q(conn, 'SELECT 1 FROM recipe_ingredient WHERE ingredient_id = :i UNION ALL '
                        'SELECT 1 FROM recipe_line WHERE ingredient_id = :i', i=i).first()
        if used:
            _q(conn, "UPDATE ingredient SET status = 'inactive', tier = NULL WHERE id = :i", i=i)
        else:
            _q(conn, 'DELETE FROM ingredient_alias WHERE ingredient_id = :i', i=i)
            _q(conn, 'DELETE FROM ingredient WHERE id = :i', i=i)
