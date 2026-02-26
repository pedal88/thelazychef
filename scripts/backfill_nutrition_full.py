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
    
    # If the unit is an abstract counting term, omit it from the string
    if default_unit.lower() in ['unit', 'units', 'pcs', 'piece', 'pieces']:
        query = f"1 {clean_name}"
    else:
        query = f"1 {default_unit} {clean_name}"
        
    url = "https://api.edamam.com/api/nutrition-data"
    params = {
        'app_id': EDAMAM_APP_ID,
        'app_key': EDAMAM_APP_KEY,
        'ingr': query
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            ingredients = data.get('ingredients', [])
            if not ingredients:
                return None
                
            parsed = ingredients[0].get('parsed', [])
            if not parsed:
                return None
                
            match = parsed[0]
            weight = match.get('weight')
            
            if weight and weight > 0:
                nutrients = match.get('nutrients', {})
                
                # Helper to calculate per 100g 
                def per_100g(key):
                    val = nutrients.get(key, {}).get('quantity', 0)
                    return (val / weight) * 100
                
                return {
                    'weight': weight,
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
        print(f"  ❌ Network/Timeout Error: {e}")
        return None

def main():
    with app.app_context():
        targets = db.session.query(Ingredient).filter(
            Ingredient.average_g_per_unit.is_(None)
        ).all()
        
        total = len(targets)
        print(f"--- Starting Full Spectrum Hydration for {total} Pantry Items ---")
        
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
                    print(f"  ✓ Saved! {result['weight']}g | {result['calories']:.1f} kcal")
                else:
                    print(f"  ❌ Unmapped by Edamam.")
            except Exception as e:
                print(f"  ⚠️ Critical loop failure for item '{ing.name}': {e}")
                db.session.rollback()
                
            time.sleep(2) # 40 calls/minute constraint mapping
            
        print("\nAll Done.")

if __name__ == '__main__':
    main()
