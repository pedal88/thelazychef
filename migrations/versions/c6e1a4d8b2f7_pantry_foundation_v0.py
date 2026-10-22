"""pantry: the foundation pantry, v0

Level 2 of the pantry (RECIPE_MODEL_V2.md, "Basisvarer og grunnlager"): the default choices recipes reuse.
Chosen 22.10.2026 from a sample of 272 dishes Norwegian home cooks make in 13 cuisines
(scripts/foundation_sample.py, run foundation-v0, and the review page "Grunnlager v0"): the top 60 by use, the
cuisine keys, canned kidney beans and chili peppers. Decisions on the way: jasmine rice is the rice (white rice
is left out), onion and red onion both stay, sour cream over crème fraîche, and grated white cheese (Norvegia
and the like) instead of cheddar.

Four of them are not in the pantry and are added like 938d10ac6005 (active, the next free food_id), with
aliases that are free: ground beef, taco seasoning, grated white cheese and gochugaru. Nutrition and symbols
follow in a later migration (scripts/ingredient_nutrition.py and scripts/ingredient_symbols.py).

Only the tier of the others changes, core to foundation, matched by name.

Downgrade sets them back to core and removes the four again (one a recipe already uses is set inactive).

Revision ID: c6e1a4d8b2f7
Revises: a3d7f2c9e1b6
Create Date: 2026-10-22

"""
import datetime

from alembic import op
import sqlalchemy as sa


revision = 'c6e1a4d8b2f7'
down_revision = 'a3d7f2c9e1b6'
branch_labels = None
depends_on = None

SOURCE = 'pantry-additions'  # data_source of the new ingredients

FOUNDATION = (
    'bacon', 'baking powder', 'beef sirloin', 'bell peppers', 'brown sugar', 'butter', 'button mushrooms', 'cabbage',
    'canned corn', 'canned kidney beans', 'canned tomatoes', 'carrots', 'chicken breast', 'chicken stock',
    'chicken thigh', 'chili peppers', 'chili powder', 'cilantro', 'coconut milk', 'cornstarch', 'cucumber',
    'dried oregano', 'eggs', 'fish sauce', 'fresh ginger', 'garam masala', 'garlic', 'ghee', 'gochujang',
    'ground cinnamon', 'ground cumin', 'ground nutmeg', 'ground paprika', 'ground turmeric', 'heavy cream',
    'jasmine rice', 'ketchup', 'kimchi', 'lemon', 'lemon juice', 'lettuce', 'mirin', 'mozzarella', 'onion',
    'oyster sauce', 'parmesan', 'parsley', 'plain yogurt', 'potatoes', 'red onion', 'rice vinegar', 'salsa',
    'sesame oil', 'sesame seeds', 'sour cream', 'soy sauce', 'spaghetti', 'spring onions', 'tomato paste',
    'tomatoes', 'tortilla', 'whole milk',
)
# name, main category, sub category, aliases
NEW = [
    ('ground beef', 'meat', 'beef', ('minced beef', 'beef mince', 'kjøttdeig', 'kjøttdeig av storfe')),
    ('taco seasoning', 'spices and herbs', 'ground spices', ('taco spice mix', 'taco spice', 'tacokrydder')),
    ('grated white cheese', 'dairy and egg', 'cheese', ('grated cheese', 'revet ost', 'revet hvitost', 'norvegia')),
    ('gochugaru', 'spices and herbs', 'ground spices', ('korean chili flakes', 'korean red pepper flakes')),
]


def _q(conn, sql, **params):
    return conn.execute(sa.text(sql), params)



def upgrade():
    conn = op.get_bind()
    number = max((int(f) for (f,) in _q(conn, 'SELECT food_id FROM ingredient').all() if f and f.isdigit()), default=0)
    today = datetime.date.today()
    for name, main, sub, aliases in NEW:
        if not _q(conn, 'SELECT 1 FROM ingredient WHERE lower(name) = :n', n=name).first():
            number += 1
            _q(conn, "INSERT INTO ingredient (food_id, name, main_category, sub_category, default_unit, is_staple, "
                     "has_transparent_image, status, tier, data_source, created_at) "
                     "VALUES (:f, :n, :m, :s, 'g', :no, :no, 'active', 'foundation', :src, :t)",
               f=f'{number:06d}', n=name, m=main, s=sub, no=False, src=SOURCE, t=today.isoformat())
        (iid,) = _q(conn, 'SELECT id FROM ingredient WHERE lower(name) = :n', n=name).first()
        for alias in aliases:
            taken = _q(conn, 'SELECT 1 FROM ingredient WHERE lower(name) = :a UNION ALL '
                             'SELECT 1 FROM ingredient_alias WHERE lower(name) = :a', a=alias).first()
            if not taken:
                _q(conn, 'INSERT INTO ingredient_alias (ingredient_id, name, created_at) VALUES (:i, :a, :t)',
                   i=iid, a=alias, t=datetime.datetime.combine(today, datetime.time()))
    conn.execute(sa.text("UPDATE ingredient SET tier = 'foundation' WHERE lower(name) IN :names AND status = 'active'")
                 .bindparams(sa.bindparam('names', expanding=True)), {'names': list(FOUNDATION)})


def downgrade():
    conn = op.get_bind()
    conn.execute(sa.text("UPDATE ingredient SET tier = 'core' WHERE lower(name) IN :names AND tier = 'foundation'")
                 .bindparams(sa.bindparam('names', expanding=True)), {'names': list(FOUNDATION)})
    for name, *_ in NEW:
        for (i,) in _q(conn, 'SELECT id FROM ingredient WHERE lower(name) = :n AND data_source = :s', n=name, s=SOURCE).all():
            used = _q(conn, 'SELECT 1 FROM recipe_ingredient WHERE ingredient_id = :i UNION ALL '
                            'SELECT 1 FROM recipe_line WHERE ingredient_id = :i', i=i).first()
            if used:
                _q(conn, "UPDATE ingredient SET status = 'inactive', tier = NULL WHERE id = :i", i=i)
            else:
                _q(conn, 'DELETE FROM ingredient_alias WHERE ingredient_id = :i', i=i)
                _q(conn, 'DELETE FROM ingredient WHERE id = :i', i=i)
