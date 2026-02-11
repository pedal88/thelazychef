import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import app, db
from database.models import Recipe
import os

def check_recipes():
    with app.app_context():
        recipes = db.session.execute(db.select(Recipe).limit(5)).scalars().all()
        print(f"--- Checking {len(recipes)} Recipes TEMPLATE ---")
        for r in recipes:
            print(f"ID: {r.id}, Title: {r.title}, Image: {r.image_filename}")

if __name__ == "__main__":
    check_recipes()
