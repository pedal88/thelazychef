import sys
import os

# Ensure the root of the project is in PYTHONPATH so we can import from `app` and `database`
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from database.models import db, Recipe
from services.recipe_service import recalculate_recipe_nutrition

def hydrate_all_recipes():
    print("--- Starting Bulk Recipe Recalculation ---")
    
    with app.app_context():
        recipes = db.session.query(Recipe).all()
        total = len(recipes)
        
        print(f"Found {total} recipes in the database.")
        
        count_updated = 0
        for idx, recipe in enumerate(recipes, 1):
            print(f"[{idx}/{total}] Recalculating Nutrition for: {recipe.title}")
            try:
                # Modifies the recipe objects total_* fields in-place
                recalculate_recipe_nutrition(recipe.id, db.session)
                count_updated += 1
                
                # Commit in small batches or after each update to prevent huge memory buildup
                if count_updated % 50 == 0:
                    db.session.commit()
            except Exception as e:
                print(f"  ❌ Error recalculating {recipe.title} (ID: {recipe.id}): {e}")
                db.session.rollback()

        # Final commit to catch remainder
        db.session.commit()
        print(f"--- Successfully hydrated {count_updated}/{total} recipes. ---")

if __name__ == '__main__':
    hydrate_all_recipes()
