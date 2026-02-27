import time
import requests
import re
import sys
from app import app
from database.models import db, Ingredient

def fetch_edamam_data(ingredient_name, default_unit):
    # Sanitize the name by removing everything in parentheses
    clean_name = re.sub(r'\(.*?\)', '', ingredient_name).strip()
    
    query_unit = default_unit
    query_amount = 1
    
    # Normalize grams/ml to 100 for sufficient API mapping volume
    if default_unit.lower() in ['g', 'gram', 'grams', 'ml', 'milliliter', 'milliliters']:
        query_amount = 100
        # Expand abbreviations for Edamam's parsing engine
        query_unit = 'grams' if default_unit.lower().startswith('g') else 'milliliters'
        
    if default_unit.lower() in ['unit', 'units', 'pcs', 'piece', 'pieces']:
        query = f"{query_amount} {clean_name}"
    else:
        query = f"{query_amount} {query_unit} {clean_name}"
        
    url = "https://edamam-edamam-nutrition-analysis.p.rapidapi.com/api/nutrition-data"
    headers = {
        "x-rapidapi-key": "54e49fbee7msh8dea1330c6927d2p1ccfeajsncffb62a4508a",
        "x-rapidapi-host": "edamam-edamam-nutrition-analysis.p.rapidapi.com"
    }
    params = {
        'ingr': query
    }
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            # The RapidAPI payload has totalWeight and totalNutrients at the root!
            total_returned_weight = data.get('totalWeight')
            
            if total_returned_weight and total_returned_weight > 0:
                nutrients = data.get('totalNutrients', {})
                
                # Helper to calculate per 100g 
                def per_100g(key):
                    val = nutrients.get(key, {}).get('quantity', 0)
                    return (val / total_returned_weight) * 100
                
                # Actual weight per physical 1 unit
                # If queried 100g/ml, avg_weight = total_returned_weight / 100 (which is 1.0 if total_returned_weight == 100.0)
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
        elif response.status_code == 429:
            print(f"\n  🛑 HALTING SCRIPT: RapidAPI Limit Reached (HTTP 429)")
            sys.exit(1)
        else:
            return None
    except Exception as e:
        if isinstance(e, SystemExit):
            raise e
        print(f"  ❌ Network/Timeout Error: {e}")
        return None

def main():
    with app.app_context():
        targets = db.session.query(Ingredient).filter(
            Ingredient.average_g_per_unit.is_(None)
        ).all()
        
        total = len(targets)
        print(f"--- Starting RapidAPI Hydration for {total} Pantry Items ---")
        
        for idx, ing in enumerate(targets, 1):
            # Safe skip if no default unit is assigned
            if not ing.default_unit:
                print(f"[{idx}/{total}] Skipping '{ing.name}' (No default unit)")
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
                    
                    db.session.add(ing)
                    db.session.commit()
                    print(f"  ✓ Saved! avg_g_per_unit={result['weight']:.2f} | {result['calories']:.1f} kcal/100g")
                else:
                    print(f"  ❌ Unmapped by Edamam.")
            except Exception as e:
                if isinstance(e, SystemExit):
                    raise e
                print(f"  ⚠️ Critical loop failure for item '{ing.name}': {e}")
                db.session.rollback()
                
            time.sleep(0.5) # Fast 0.5-second buffer for RapidAPI
            
        print("\nAll Done.")

if __name__ == '__main__':
    main()
