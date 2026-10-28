"""taxonomy cleanup 2026-10-28

Moves pantry ingredients to the categories that fit them (data/constraints/categories.json, decided with Pål
28.10.2026 after the ingredient galaxy review):

- fish by kind: "white fish", "oily fish" and "shellfish" instead of one sub category per species
- stocks and stock cubes to "stocks & broths", vinegars to "vinegars" (both were in "other sauces & condiments")
- the rice to "rice" (it was in "refined grains" and "whole grains")
- butter and herb butter to dairy, beside salted and unsalted butter
- lemon and lime juice to "citrus fruits", so "juices" is only the drinks
- nori from canned and preserved / other to vegetables / "sea vegetables"
- "carbonara", a dish and not an ingredient, inactive when no recipe uses it
- category names saved with non-breaking spaces ("canned\\xa0fish") written with plain spaces

Each move names the ingredient and the category it is expected in; one that is not there is left alone, so a
database that differs (or a fresh one) is safe. Downgrade moves them back the same way.

Revision ID: b3d7e9f1a2c4
Revises: e8b4d2f6a1c3
Create Date: 2026-10-28
"""
from alembic import op
import sqlalchemy as sa


revision = 'b3d7e9f1a2c4'
down_revision = 'e8b4d2f6a1c3'
branch_labels = None
depends_on = None

FISH, SAUCES, GRAINS = 'fish and seafood', 'sauces and condiments', 'cereal grains and pasta'
# (name, from main, from sub, to main, to sub)
MOVES = [
    ('cod', FISH, 'fish', FISH, 'white fish'),
    ('salmon fillet', FISH, 'salmon', FISH, 'oily fish'),
    ('whole salmon', FISH, 'salmon', FISH, 'oily fish'),
    ('shrimps', FISH, 'shrimps', FISH, 'shellfish'),
    ('scampi', FISH, 'scampi', FISH, 'shellfish'),
    ('lobster', FISH, 'lobster', FISH, 'shellfish'),
    ('beef stock', SAUCES, 'other sauces & condiments', SAUCES, 'stocks & broths'),
    ('beef stock cube', SAUCES, 'other sauces & condiments', SAUCES, 'stocks & broths'),
    ('chicken stock', SAUCES, 'other sauces & condiments', SAUCES, 'stocks & broths'),
    ('chicken bouillon cube', SAUCES, 'other sauces & condiments', SAUCES, 'stocks & broths'),
    ('vegetable stock', SAUCES, 'other sauces & condiments', SAUCES, 'stocks & broths'),
    ('balsamic vinegar', SAUCES, 'other sauces & condiments', SAUCES, 'vinegars'),
    ('red wine vinegar', SAUCES, 'other sauces & condiments', SAUCES, 'vinegars'),
    ('rice vinegar', SAUCES, 'other sauces & condiments', SAUCES, 'vinegars'),
    ('white vinegar', SAUCES, 'other sauces & condiments', SAUCES, 'vinegars'),
    ('arborio rice', GRAINS, 'refined grains', GRAINS, 'rice'),
    ('basmati rice', GRAINS, 'refined grains', GRAINS, 'rice'),
    ('jasmine rice', GRAINS, 'refined grains', GRAINS, 'rice'),
    ('sushi rice', GRAINS, 'refined grains', GRAINS, 'rice'),
    ('white rice', GRAINS, 'refined grains', GRAINS, 'rice'),
    ('brown rice', GRAINS, 'whole grains', GRAINS, 'rice'),
    ('butter', 'fats and oils', 'animal fats', 'dairy and egg', 'butter and spreads'),
    ('herb butter', 'fats and oils', 'spreads', 'dairy and egg', 'butter and spreads'),
    ('lemon juice', 'fruit and fruit products', 'juices', 'fruit and fruit products', 'citrus fruits'),
    ('lime juice', 'fruit and fruit products', 'juices', 'fruit and fruit products', 'citrus fruits'),
    ('nori', 'canned and preserved', 'other', 'vegetables', 'sea vegetables'),
]
MOVE = sa.text('UPDATE ingredient SET main_category = :to_main, sub_category = :to_sub '
               'WHERE lower(name) = :name AND main_category = :from_main AND sub_category = :from_sub')


def _move(back=False):
    conn = op.get_bind()
    for name, from_main, from_sub, to_main, to_sub in MOVES:
        if back:
            from_main, from_sub, to_main, to_sub = to_main, to_sub, from_main, from_sub
        conn.execute(MOVE, {'name': name, 'from_main': from_main, 'from_sub': from_sub,
                            'to_main': to_main, 'to_sub': to_sub})


def upgrade():
    conn = op.get_bind()
    for column in ('main_category', 'sub_category'):
        conn.execute(sa.text(f"UPDATE ingredient SET {column} = REPLACE({column}, :nb, ' ') "
                             f"WHERE {column} LIKE :has_nb"), {'nb': '\xa0', 'has_nb': '%\xa0%'})
    _move()
    conn.execute(sa.text("UPDATE ingredient SET status = 'inactive' WHERE lower(name) = 'carbonara' "
                         "AND status = 'active' AND NOT EXISTS (SELECT 1 FROM recipe_line "
                         "WHERE recipe_line.ingredient_id = ingredient.id)"))


def downgrade():
    _move(back=True)
    conn = op.get_bind()
    conn.execute(sa.text("UPDATE ingredient SET status = 'active' WHERE lower(name) = 'carbonara' "
                         "AND status = 'inactive'"))
