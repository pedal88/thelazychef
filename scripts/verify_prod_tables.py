import sys
import os
import json

# Add project root to path to verify imports work
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db
from database.models import User, Chef, Recipe, Ingredient, RecipeIngredient
from sqlalchemy import select

def check_tables():
    print("--- Verifying Cloud Database Content ---")
    
    with app.app_context():
        # 1. User
        print("\n=== Table: User ===")
        print("Description: Stores user accounts and admin status.")
        users = db.session.execute(select(User).limit(2)).scalars().all()
        if not users:
            print("No data found.")
        for u in users:
            print(f"Row: id={u.id}, email={u.email}, is_admin={u.is_admin}")

        # 2. Chef
        print("\n=== Table: Chef ===")
        print("Description: AI personas with specific cooking styles.")
        chefs = db.session.execute(select(Chef).limit(2)).scalars().all()
        if not chefs:
            print("No data found.")
        for c in chefs:
            print(f"Row: id={c.id}, name={c.name}, archetype={c.archetype}, diet_preferences={c.diet_preferences[:50]}...")

        # 3. Recipe
        print("\n=== Table: Recipe ===")
        print("Description: Generated recipes with metadata.")
        recipes = db.session.execute(select(Recipe).limit(2)).scalars().all()
        if not recipes:
            print("No data found.")
        for r in recipes:
            print(f"Row: id={r.id}, title={r.title}, cuisine={r.cuisine}, prep={r.prep_time_mins}m, taste={r.taste_level}, cals={r.total_calories}")

        # 4. Ingredient
        print("\n=== Table: Ingredient ===")
        print("Description: Standardized food items with nutrition.")
        ingredients = db.session.execute(select(Ingredient).limit(2)).scalars().all()
        if not ingredients:
            print("No data found.")
        for i in ingredients:
            print(f"Row: id={i.id}, food_id={i.food_id}, name={i.name}, cals_100g={i.calories_per_100g}, img={i.image_url}")

        # 5. RecipeIngredient
        print("\n=== Table: RecipeIngredient ===")
        print("Description: Links ingredients to recipes with amounts.")
        ris = db.session.execute(select(RecipeIngredient).limit(2)).scalars().all()
        if not ris:
            print("No data found.")
        for ri in ris:
            print(f"Row: id={ri.id}, amount={ri.amount}, unit={ri.unit}, component={ri.component}")

if __name__ == "__main__":
    check_tables()
