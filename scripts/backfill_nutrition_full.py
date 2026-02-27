import time
import requests
import re
import sys
import os
import json
from datetime import datetime
from google import genai
from google.genai import types
from app import app
from database.models import db, Ingredient

_api_key = os.getenv("GOOGLE_API_KEY")
gemini_client = genai.Client(api_key=_api_key) if _api_key else None

def generate_nutrition_estimate(ingredient_name):
    """Fallback LLM-based macro estimator."""
    if not gemini_client:
        return None
        
    prompt = f"Provide a scientific nutritional estimate for 100g of {ingredient_name}. Return ONLY simple JSON with these exact numeric keys: weight (average weight in grams of 1 logical unit, default 1.0), calories, protein, fat, fat_saturated, carbs, sugar, fiber, sodium, cholesterol, calcium, potassium. Use only raw numbers."
    try:
        response = gemini_client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.0,
            ),
        )
        return json.loads(response.text)
    except Exception as e:
        print(f"  ⚠️ Gemini Fallback failed: {e}")
        return None

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
    
    max_retries = 3
    retries = 0
    
    while retries < max_retries:
        try:
            response = requests.get(url, params=params, timeout=10)
            
            # Continuous Loop Logic
            if response.status_code == 429:
                print(f"  ⏳ Rate Limit Hit (HTTP 429). Sleeping for 60 seconds before retrying...")
                time.sleep(60)
                retries += 1
                continue
                
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
            retries += 1
            time.sleep(5) # Small backoff for standard network errors
            
    print(f"  🛑 Failed after {max_retries} attempts. Giving up on {ingredient_name}.")
    return None

def main():
    with app.app_context():
        # Target unscored items OR items mapped under the old legacy RapidAPI payload
        targets = db.session.query(Ingredient).filter(
            db.or_(
                Ingredient.average_g_per_unit.is_(None),
                Ingredient.data_source == 'edamam_rapidapi'
            )
        ).all()
        
        total = len(targets)
        print(f"--- Starting Edamam Enterprise Hydration for {total} Pantry Items ---")
        
        for idx, ing in enumerate(targets, 1):
            if not ing.default_unit:
                continue
                
            print(f"[{idx}/{total}] GET {ing.default_unit} {ing.name}...")
            
            try:
                result = fetch_edamam_data(ing.name, ing.default_unit)
                source_label = 'edamam_enterprise'
                
                if not result:
                    print(f"  🔍 Unmapped by Edamam. Triggering AI Fallback...")
                    result = generate_nutrition_estimate(ing.name)
                    source_label = 'ai_fallback'
                
                if result:
                    ing.average_g_per_unit = float(result.get('weight', 1.0))
                    ing.calories_per_100g = float(result.get('calories', 0))
                    ing.protein_per_100g = float(result.get('protein', 0))
                    ing.fat_per_100g = float(result.get('fat', 0))
                    ing.fat_saturated_per_100g = float(result.get('fat_saturated', 0))
                    ing.carbs_per_100g = float(result.get('carbs', 0))
                    ing.sugar_per_100g = float(result.get('sugar', 0))
                    ing.fiber_per_100g = float(result.get('fiber', 0))
                    ing.sodium_mg_per_100g = float(result.get('sodium', 0))
                    ing.cholesterol_mg_per_100g = float(result.get('cholesterol', 0))
                    ing.calcium_mg_per_100g = float(result.get('calcium', 0))
                    ing.potassium_mg_per_100g = float(result.get('potassium', 0))
                    ing.data_source = source_label
                    
                    db.session.add(ing)
                    db.session.commit()
                    
                    if source_label == 'ai_fallback':
                        os.makedirs('logs', exist_ok=True)
                        with open('logs/unmapped_ingredients.log', 'a') as log_f:
                            log_f.write(f"[{datetime.now().isoformat()}] {ing.name} solved via AI Fallback.\n")
                        print(f"  🟢 AI Saved! avg_g_per_unit={ing.average_g_per_unit:.2f} | {ing.calories_per_100g:.1f} kcal/100g")
                    else:
                        print(f"  ✓ API Saved! avg_g_per_unit={ing.average_g_per_unit:.2f} | {ing.calories_per_100g:.1f} kcal/100g")
                else:
                    print(f"  ❌ Still unmapped after Fallback.")
            except Exception as e:
                if isinstance(e, SystemExit):
                    sys.exit(1)
                print(f"  ⚠️ Critical loop failure for item '{ing.name}': {e}")
                db.session.rollback()
                
            # Enterprise Basic Speed: 1.5s Buffer (~40 calls/min) constraints requested by user
            time.sleep(1.5)
            
        print("\nAll Done.")

if __name__ == '__main__':
    main()
