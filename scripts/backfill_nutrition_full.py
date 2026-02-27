import time
import requests
import re
import sys
from app import app
from database.models import db, Ingredient

def fetch_edamam_data(ingredient_name, default_unit):
    # Sanitize the name: Strip parentheses from ingredient names
    clean_name = re.sub(r'\(.*?\)', '', ingredient_name).strip()
    
    query_unit = default_unit
    query_amount = 1
    
    # 100g RECALIBRATION: Normalize volume queries to 100 multipliers
    if default_unit.lower() in ['g', 'gram', 'grams', 'ml', 'milliliter', 'milliliters']:
        query_amount = 100
        query_unit = 'grams' if default_unit.lower().startswith('g') else 'milliliters'
        
    if default_unit.lower() in ['unit', 'units', 'pcs', 'piece', 'pieces']:
        query = f"{query_amount} {clean_name}"
    else:
        query = f"{query_amount} {query_unit} {clean_name}"
        
    url = "https://api.edamam.com/api/nutrition-data"
    params = {
        'app_id': '144a8231',
        'app_key': 'f4b119e11be9443f14e7f042d5e80eef',
        'ingr': query
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        
        # RATE LIMIT HIT
        if response.status_code == 429:
            print(f"\n  🛑 RATE LIMIT HIT (HTTP 429). Exiting safely.")
            sys.exit(1)
            
        if response.status_code == 200:
            try:
                data = response.json()
            except Exception as json_err:
                # Catch JSON parsing to skip unmappable items without crashing
                print(f"  ⚠️ JSON Parse Error: {json_err}")
                return None
            
            # ARCHITECTURAL OVERRIDE: RapidAPI flattens the response structure.
            # It DOES NOT return `data['ingredients'][0]['parsed']` like the free tier does. 
            # We MUST use `totalWeight` and `totalNutrients` at the root layer.
            total_returned_weight = data.get('totalWeight')
            
            if total_returned_weight and total_returned_weight > 0:
                nutrients = data.get('totalNutrients', {})
                
                # Normalize ALL macros to 'per 100g' using: (nutrient_quantity / weight) * 100
                def per_100g(key):
                    val = nutrients.get(key, {}).get('quantity', 0)
                    return (val / total_returned_weight) * 100
                
                # Actual weight per physical 1 unit
                avg_weight = total_returned_weight / query_amount
                
                return {
                    'weight': avg_weight,
                    'calories': per_100g('ENERC_KCAL'),
                    'protein': per_100g('PROCNT'),
                    'fat': per_100g('FAT'),
                    'fat_saturated': per_100g('FASAT'),
                    'carbs': per_100g('CHOCDF'),
                    'sugar': per_100g('SUGAR'),
                    'fiber': per_100g('FIBTG'),
                    'sodium': per_100g('NA'),
                    'cholesterol': per_100g('CHOLE'),
                    'calcium': per_100g('CA'),
                    'potassium': per_100g('K')
                }
            else:
                return None
        else:
            return None
    except Exception as e:
        if isinstance(e, SystemExit):
            raise e
        print(f"  ❌ Network/Timeout Error: {e}")
        return None

def main():
    with app.app_context():
        # Only query items that haven't been successfully evaluated
        targets = db.session.query(Ingredient).filter(
            Ingredient.average_g_per_unit.is_(None)
        ).all()
        
        total = len(targets)
        print(f"--- Starting Edamam Enterprise Hydration for {total} Pantry Items ---")
        
        for idx, ing in enumerate(targets, 1):
            if not ing.default_unit:
                continue
                
            print(f"[{idx}/{total}] GET {ing.default_unit} {ing.name}...")
            
            try:
                result = fetch_edamam_data(ing.name, ing.default_unit)
                
                if result:
                    ing.average_g_per_unit = result['weight']
                    ing.calories_per_100g = result['calories']
                    ing.protein_per_100g = result['protein']
                    ing.fat_per_100g = result['fat']
                    ing.fat_saturated_per_100g = result['fat_saturated']
                    ing.carbs_per_100g = result['carbs']
                    ing.sugar_per_100g = result['sugar']
                    ing.fiber_per_100g = result['fiber']
                    ing.sodium_mg_per_100g = result['sodium']
                    ing.cholesterol_mg_per_100g = result['cholesterol']
                    ing.calcium_mg_per_100g = result['calcium']
                    ing.potassium_mg_per_100g = result['potassium']
                    ing.data_source = 'edamam_enterprise'
                    
                    db.session.add(ing)
                    db.session.commit() # Commit after every successful ingredient
                    print(f"  ✓ Saved! avg_g_per_unit={result['weight']:.2f} | {result['calories']:.1f} kcal/100g")
                else:
                    print(f"  ❌ Unmapped by Edamam.")
            except Exception as e:
                if isinstance(e, SystemExit):
                    sys.exit(1)
                print(f"  ⚠️ Critical loop failure for item '{ing.name}': {e}")
                db.session.rollback()
                
            # Enterprise Speed: 0.2s Buffer
            time.sleep(0.2) 
            
        print("\nAll Done.")

if __name__ == '__main__':
    main()
