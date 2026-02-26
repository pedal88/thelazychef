import time
import requests
import re
from app import app
from database.models import db, Ingredient

EDAMAM_APP_ID = "abe08a7b"
EDAMAM_APP_KEY = "5114c5d8f2d86f403004020932f5b6bf"

def fetch_edamam_data(ingredient_name, default_unit):
    # Sanitize the name by removing everything in parentheses
    clean_name = re.sub(r'\(.*?\)', '', ingredient_name).strip()
    
    # If the unit is literally 'unit' or 'units', omit it from the string
    if default_unit.lower() in ['unit', 'units', 'pcs', 'piece', 'pieces']:
        query = f"1 {clean_name}"
    else:
        query = f"1 {default_unit} {clean_name}"
        
    url = "https://api.edamam.com/api/nutrition-data"
    params = {
        'app_id': EDAMAM_APP_ID,
        'app_key': EDAMAM_APP_KEY,
        'nutrition-type': 'cooking',
        'ingr': query
    }
    
    print(f"\n[GET] {query} ...")
    try:
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            # Edamam nests the actual data inside ingredients -> parsed
            ingredients = data.get('ingredients', [])
            if not ingredients:
                print(f"  ❌ No ingredients found in Edamam response.")
                return None
                
            parsed = ingredients[0].get('parsed', [])
            if not parsed:
                print(f"  ❌ Edamam could not parse the query.")
                return None
                
            match = parsed[0]
            weight = match.get('weight')
            
            if weight and weight > 0:
                nutrients = match.get('nutrients', {})
                calories_data = nutrients.get('ENERC_KCAL', {})
                calories = calories_data.get('quantity', 0)
                
                # Math: If 1 unit weighs X grams and has Y calories. Then 100g has (Y / X) * 100 calories.
                cal_per_100g = (calories / weight) * 100
                
                print(f"  ✓ Edamam Found -> Weight: {weight:.1f}g | Calories: {cal_per_100g:.1f} per 100g")
                return {
                    'weight': weight,
                    'calories_per_100g': cal_per_100g
                }
            else:
                print(f"  ❌ No physical weight mapping found in Edamam dictionary.")
                return None
        else:
            print(f"  ❌ API Error: HTTP {response.status_code}")
            return None
    except Exception as e:
        print(f"  ❌ Network Error: {Exception}")
        return None

def main():
    with app.app_context():
        # Target 5 ingredients that have a unit string, but missing the math constants
        targets = db.session.query(Ingredient).filter(
            Ingredient.default_unit.isnot(None),
            Ingredient.average_g_per_unit.is_(None)
        ).limit(5).all()
        
        print(f"--- Starting Edamam Backfill Test for {len(targets)} Items ---")
        
        for ing in targets:
            result = fetch_edamam_data(ing.name, ing.default_unit)
            
            if result:
                # Update the database
                ing.average_g_per_unit = result['weight']
                ing.calories_per_100g = result['calories_per_100g']
                db.session.add(ing)
                print(f"  -> DB Staged ✅")
            
            # Rate Limiter: 40 calls per minute = 1.5s per call. Sleep 2s to be safe.
            time.sleep(2)
            
        print("\nCommitting to Database...")
        db.session.commit()
        print("Done.")

if __name__ == '__main__':
    main()
