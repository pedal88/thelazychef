"""pantry: dark chocolate, red wine vinegar, vanilla sugar

Three core ingredients the test recipes need and the pantry lacks
(brownies, lasagne). Added the same way as the new ingredients in
0d4f84fc82e7: active, tier core, the next free food_id. Nutrition and symbols
come in a later migration, made by scripts/ingredient_nutrition.py and
scripts/ingredient_symbols.py once the rows exist in production.

An ingredient that already exists with the same name is skipped. Nothing else
is changed or deleted.

Downgrade removes the three again (one a recipe already uses is set inactive
instead).

Revision ID: 938d10ac6005
Revises: edb2c0f81d8a
Create Date: 2026-10-20

"""
import datetime

from alembic import op
import sqlalchemy as sa


revision = '938d10ac6005'
down_revision = 'edb2c0f81d8a'
branch_labels = None
depends_on = None

SOURCE = 'pantry-additions'  # data_source of the new ingredients

NEW = [('dark chocolate', 'baking ingredients', 'flavorings'),
       ('red wine vinegar', 'sauces and condiments', 'other sauces & condiments'),
       ('vanilla sugar', 'baking ingredients', 'sugar')]


def _q(conn, sql, **params):
    return conn.execute(sa.text(sql), params)


def upgrade():
    conn = op.get_bind()
    number = max((int(f) for (f,) in _q(conn, 'SELECT food_id FROM ingredient').all() if f and f.isdigit()), default=0)
    for name, main, sub in NEW:
        if _q(conn, 'SELECT 1 FROM ingredient WHERE lower(name) = :n', n=name).first():
            continue
        number += 1
        _q(conn, "INSERT INTO ingredient (food_id, name, main_category, sub_category, default_unit, is_staple, "
                 "has_transparent_image, status, tier, data_source, created_at) "
                 "VALUES (:f, :n, :m, :s, 'g', :no, :no, 'active', 'core', :src, :t)",
           f=f'{number:06d}', n=name, m=main, s=sub, no=False, src=SOURCE, t=datetime.date.today().isoformat())


def downgrade():
    conn = op.get_bind()
    for name, *_ in NEW:
        for (i,) in _q(conn, 'SELECT id FROM ingredient WHERE lower(name) = :n AND data_source = :s', n=name, s=SOURCE).all():
            used = _q(conn, 'SELECT 1 FROM recipe_ingredient WHERE ingredient_id = :i UNION ALL '
                            'SELECT 1 FROM recipe_line WHERE ingredient_id = :i', i=i).first()
            if used:
                _q(conn, "UPDATE ingredient SET status = 'inactive', tier = NULL WHERE id = :i", i=i)
            else:
                _q(conn, 'DELETE FROM ingredient_alias WHERE ingredient_id = :i', i=i)
                _q(conn, 'DELETE FROM ingredient WHERE id = :i', i=i)
