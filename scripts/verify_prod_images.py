import sys
import os
from sqlalchemy import select

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db
from database.models import Ingredient

def verify_images():
    print("--- Verifying Ingredient Images in Production ---")
    with app.app_context():
        # Count total ingredients
        total = db.session.query(Ingredient).count()
        print(f"Total Ingredients: {total}")

        # Find ingredients with relative paths (not starting with http)
        # Note: image_url might be None or empty string too
        rel_paths = db.session.execute(
            select(Ingredient).where(
                Ingredient.image_url.notlike('http%')
            )
        ).scalars().all()

        if rel_paths:
            print(f"❌ Found {len(rel_paths)} ingredients with relative/missing paths:")
            for ing in rel_paths[:10]:
                print(f" - {ing.name} ({ing.food_id}): {ing.image_url}")
            if len(rel_paths) > 10:
                print(f" ... and {len(rel_paths) - 10} more.")
        else:
            print("✅ All ingredient images have absolute URLs (start with http).")

if __name__ == "__main__":
    verify_images()
