import json
import os
import sys

# Add parent directory to path to import app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db
from database.models import Ingredient

def clean_pantry_seed():
    seed_path = 'data/constraints/pantry_seed.json'
    with open(seed_path, 'r') as f:
        data = json.load(f)
    
    # Filter out anything with main_category 'Imported' or food_id starting with 'IMP-'
    cleaned_data = []
    removed_count = 0
    for item in data:
        if item.get('main_category') != 'Imported' and not str(item.get('food_id', '')).startswith('IMP-'):
            cleaned_data.append(item)
        else:
            removed_count += 1
            
    with open(seed_path, 'w') as f:
        json.dump(cleaned_data, f, indent=2)
        
    print(f"Removed {removed_count} imported ingredients from pantry_seed.json.")

def clean_database():
    with app.app_context():
        # Find all imported ingredients
        imported_ingredients = db.session.query(Ingredient).filter(
            db.or_(
                Ingredient.main_category == 'Imported',
                Ingredient.food_id.like('IMP-%')
            )
        ).all()
        
        count = 0
        for ing in imported_ingredients:
            if ing.status != 'inactive':
                ing.status = 'inactive'
                count += 1
                
        db.session.commit()
        print(f"Updated {count} imported ingredients to 'inactive' in the database.")

if __name__ == "__main__":
    clean_pantry_seed()
    clean_database()
