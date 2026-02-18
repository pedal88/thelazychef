import json
import os
import sys
from flask import Flask

# Add root directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database.models import db, Ingredient
# Import the create_app or configure the app context manually if app isn't easily importable
# Assuming we can import 'app' from 'app.py' or create a basic context
try:
    from app import app
except ImportError:
    # Fallback if app.py has side effects
    print("⚠️ Could not import 'app' directly. Creating minimal context.")
    app = Flask(__name__)
    from database.db_connector import configure_database
    configure_database(app)
    db.init_app(app)

def export_pantry():
    """
    Dumps the database ingredients table to data/constraints/pantry_seed.json
    """
    print("🥡 Exporting Database Ingredients to JSON...")
    
    # Path to your seed file
    output_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'constraints', 'pantry_seed.json')
    output_path = os.path.abspath(output_path)

    with app.app_context():
        # Fetch all ingredients, sorted by ID for consistency
        ingredients = db.session.execute(
            db.select(Ingredient).order_by(Ingredient.food_id)
        ).scalars().all()
        
        export_list = []
        for ing in ingredients:
            # Reconstruct the JSON structure expected by the seed file
            item = {
                "food_id": ing.food_id,
                "food_name": ing.name,
                "main_category": ing.main_category,
                "sub_category": ing.sub_category,
                "unit": ing.default_unit,
                "nutrition": {
                    "calories_per_100g": ing.calories_per_100g,
                    "kj_per_100g": ing.kj_per_100g,
                    "protein_per_100g": ing.protein_per_100g,
                    "fat_per_100g": ing.fat_per_100g,
                    "carbs_per_100g": ing.carbs_per_100g,
                    "sugar_per_100g": ing.sugar_per_100g,
                    "fiber_per_100g": ing.fiber_per_100g,
                    "fat_saturated_per_100g": ing.fat_saturated_per_100g,
                    "sodium_mg_per_100g": ing.sodium_mg_per_100g
                },
                "images": {
                    "image_url": ing.image_url,
                    "image_prompt": ing.image_prompt
                }
            }
            # Clean up None values if necessary or keep them as null
            export_list.append(item)
            
    # Write to file
    with open(output_path, 'w') as f:
        json.dump(export_list, f, indent=2)
        
    print(f"✅ Exported {len(export_list)} items to {output_path}")
    print("👉 Now commit this file to Git to save these changes permanently.")

if __name__ == "__main__":
    export_pantry()
