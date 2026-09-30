import os
import sys

# Load venv environment correctly if needed
from app import app
from services.recipe_service import process_recipe_workflow

def run_test():
    with app.app_context():
        try:
            print(process_recipe_workflow("Norwegian meatballs with seasoned meat cakes, brown gravy, boiled potatoes and lingonberry jam", "gourmet"))
        except Exception as e:
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    run_test()
