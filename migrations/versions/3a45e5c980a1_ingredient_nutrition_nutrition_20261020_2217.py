"""ingredient nutrition nutrition-20261020-2217

Nutrition per 100 g for 1 active ingredients that had none, estimated by
Claude from USDA FoodData Central where the food is there (run nutrition-20261020-2217).
Only ingredients that still have no nutrition are filled. They get
data_source 'ai_estimate', and default_unit and average_g_per_unit (grams per
ml for liquids, 1 for g).

Downgrade empties the values again and restores default_unit and data_source.

Made by scripts/ingredient_nutrition.py apply.

Revision ID: 3a45e5c980a1
Revises: d61b3a9e4f27
Create Date: 2026-10-20

"""
from alembic import op
import sqlalchemy as sa


revision = '3a45e5c980a1'
down_revision = 'd61b3a9e4f27'
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
VALUES = {'000703': ('g',
            1.0,
            {'calcium_mg': 25,
             'calories': 81,
             'carbs': 14.45,
             'cholesterol_mg': 0,
             'fat': 0.4,
             'fat_saturated': 0.07,
             'fiber': 5.7,
             'potassium_mg': 244,
             'protein': 5.42,
             'sodium_mg': 5,
             'sugar': 5.67},
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
