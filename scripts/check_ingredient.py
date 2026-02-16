import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db
from database.models import Ingredient

with app.app_context():
    print("Searching for 'Chili'...")
    ings = db.session.execute(db.select(Ingredient).where(Ingredient.name.ilike('%Chili%'))).scalars().all()
    
    if not ings:
        print("No ingredients found matching 'Chili'.")
    else:
        for i in ings:
            print(f"FOUND: ID={i.id} | FoodID={i.food_id} | Name='{i.name}' | MainCat='{i.main_category}' | SubCat='{i.sub_category}' | ImageURL='{i.image_url}' | InStock={getattr(i, 'is_in_stock', 'N/A')}")
