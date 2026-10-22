"""ingredient nutrition nutrition-20261022-1434

Nutrition per 100 g for 4 active ingredients that had none, estimated by
Claude from USDA FoodData Central where the food is there (run nutrition-20261022-1434).
Only ingredients that still have no nutrition are filled. They get
data_source 'ai_estimate', and default_unit and average_g_per_unit (grams per
ml for liquids, 1 for g).

Downgrade empties the values again and restores default_unit and data_source.

Made by scripts/ingredient_nutrition.py apply.

Revision ID: 73ec0f99ab42
Revises: d7f3a1c9e5b2
Create Date: 2026-10-22

"""
from alembic import op
import sqlalchemy as sa


revision = '73ec0f99ab42'
down_revision = 'd7f3a1c9e5b2'
branch_labels = None
depends_on = None

FIELDS = {'calcium_mg': 'calcium_mg_per_100g',
 'calories': 'calories_per_100g',
 'carbs': 'carbs_per_100g',
 'cholesterol_mg': 'cholesterol_mg_per_100g',
 'fat': 'fat_per_100g',
 'fat_saturated': 'fat_saturated_per_100g',
 'fiber': 'fiber_per_100g',
 'potassium_mg': 'potassium_mg_per_100g',
 'protein': 'protein_per_100g',
 'sodium_mg': 'sodium_mg_per_100g',
 'sugar': 'sugar_per_100g'}
# food_id: (default_unit, average_g_per_unit, {nutrient: value}, (old default_unit, old data_source))
VALUES = {'000704': ('g',
            1.0,
            {'calcium_mg': 182,
             'calories': 322,
             'carbs': 66,
             'cholesterol_mg': 0,
             'fat': 0,
             'fat_saturated': 0,
             'fiber': 7.4,
             'potassium_mg': 873,
             'protein': 4.5,
             'sodium_mg': 7203,
             'sugar': 10.9},
            ('g', 'pantry-additions')),
 '000705': ('g',
            1.0,
            {'calcium_mg': 720,
             'calories': 373,
             'carbs': 1,
             'cholesterol_mg': 89,
             'fat': 30,
             'fat_saturated': 18,
             'fiber': 0,
             'potassium_mg': 81,
             'protein': 24,
             'sodium_mg': 600,
             'sugar': 0.5},
            ('g', 'pantry-additions')),
 '000706': ('g',
            1.0,
            {'calcium_mg': 148,
             'calories': 300,
             'carbs': 55,
             'cholesterol_mg': 0,
             'fat': 14,
             'fat_saturated': 2.5,
             'fiber': 30,
             'potassium_mg': 2000,
             'protein': 12,
             'sodium_mg': 30,
             'sugar': 10},
            ('g', 'pantry-additions')),
 '000707': ('g',
            1.0,
            {'calcium_mg': 127,
             'calories': 489,
             'carbs': 66,
             'cholesterol_mg': 0,
             'fat': 22,
             'fat_saturated': 2.9,
             'fiber': 5.3,
             'potassium_mg': 192,
             'protein': 6.8,
             'sodium_mg': 300,
             'sugar': 0.6},
            ('g', 'pantry-additions'))}


def upgrade():
    conn = op.get_bind()
    sets = ', '.join(f'{column} = :{column}' for column in FIELDS.values())
    for fid, (unit, grams, values, _) in VALUES.items():
        params = {FIELDS[k]: v for k, v in values.items()}
        conn.execute(sa.text(f"UPDATE ingredient SET {sets}, default_unit = :unit, average_g_per_unit = :grams, "
                             "data_source = 'ai_estimate' WHERE food_id = :fid AND calories_per_100g IS NULL"),
                     dict(params, unit=unit, grams=grams, fid=fid))


def downgrade():
    conn = op.get_bind()
    sets = ', '.join(f'{column} = NULL' for column in FIELDS.values())
    for fid, (_, _, _, (unit, source)) in VALUES.items():
        conn.execute(sa.text(f"UPDATE ingredient SET {sets}, average_g_per_unit = NULL, default_unit = :unit, "
                             "data_source = :source WHERE food_id = :fid AND data_source = 'ai_estimate'"),
                     dict(unit=unit, source=source, fid=fid))
