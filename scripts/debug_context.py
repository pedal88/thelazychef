import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app

def check_context():
    print("Checking Jinja2 Globals...")
    if 'get_recipe_image_url' in app.jinja_env.globals:
        print("✅ get_recipe_image_url is registered.")
    else:
        print("❌ get_recipe_image_url is MISSING from globals.")
        print(f"Available globals: {list(app.jinja_env.globals.keys())}")

if __name__ == "__main__":
    check_context()
