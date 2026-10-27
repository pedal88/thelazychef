import os
import re
import json
import typing_extensions as typing # For TypedDict compatibility
from pathlib import Path
from dotenv import load_dotenv
from google.genai import types
from jinja2 import Environment, FileSystemLoader
from services.ai_models import GEMINI_TEXT, gemini_client

# Load Environment
load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")

# Initialize Jinja2 Environment
PROMPTS_DIR = os.path.join(os.path.dirname(__file__), 'data', 'prompts')
env = Environment(loader=FileSystemLoader(PROMPTS_DIR))

if not api_key:
    # In Cloud Run, this variable is injected via the job definition.
    # In local development, it comes from .env.
    print("CRITICAL ERROR: GOOGLE_API_KEY environment variable is missing.")
    raise ValueError("GOOGLE_API_KEY environment variable is missing. Please check Secrets/Env Vars.")

client = gemini_client()

# --- Pydantic/TypedDict Schema Definitions ---
# Using TypedDict as requested for Gemini response_schema

class IngredientAnalysisSchema(typing.TypedDict):
    name: str # The standardized name
    main_category: str
    sub_category: str
    amount: float # Default amount for context
    unit: str # Default unit
    average_g_per_unit: float
    calories_per_100g: float
    kj_per_100g: float
    protein_per_100g: float
    fat_per_100g: float
    carbs_per_100g: float
    sugar_per_100g: float
    fiber_per_100g: float
    sodium_mg_per_100g: float
    fat_saturated_per_100g: float
    image_prompt: str

# --- Helper Classes for Application Compatibility ---
# The app expects object access (recipe.title), not dict access (recipe['title'])
def load_json(path):
    with open(path, 'r') as f:
        return json.load(f)


# Name -> food_id for fuzzy matching. Filled from the database by
# set_pantry_memory(); aliases live in the ingredient_alias table.
pantry_map = {}


def load_controlled_vocabularies() -> dict:
    """
    Loads controlled vocabularies for metadata tagging from JSON files.
    Returns a unified dictionary containing lists for all metadata fields.
    """
    base_constraints = Path(os.path.dirname(__file__)) / 'data' / 'constraints'
    base_post = Path(os.path.dirname(__file__)) / 'data' / 'post_processing'
    
    vocab = {
        "diets": [],
        "cuisines": [],
        "meal_types": [],
        "cooking_methods": [],
        "tastes": [],
        "cleanup_factors": [],
        "difficulty": [],
        "time_intervals": []
    }

    try:
        # 1. Diets
        p = base_constraints / 'diets.json'
        if p.exists():
            data = json.loads(p.read_text(encoding='utf-8'))
            vocab["diets"] = data.get('diets', data) if isinstance(data, dict) else data

        # 2. Main Protein (Categories Only?)
        # Need to check structure. Assuming flat list or dict with categories.
        # User requested: "Extract just the category names or flattened examples"
        p = base_constraints / 'main_protein.json'
        if p.exists():
            data = json.loads(p.read_text(encoding='utf-8'))
            # If structure is {"protein_types": [{"category": "Beef", ...}]}
            raw = data.get('protein_types', data) if isinstance(data, dict) else data
            if isinstance(raw, list) and len(raw) > 0 and isinstance(raw[0], dict):
                 vocab["protein_types"] = [item.get('category') for item in raw]
            else:
                 vocab["protein_types"] = raw

        # 3. Meal Types (Flatten)
        p = base_constraints / 'meal_types.json'
        if p.exists():
            data = json.loads(p.read_text(encoding='utf-8'))
            # Assuming {"meal_types": ["Breakfast", ...]}
            vocab["meal_types"] = data.get('meal_types', data) if isinstance(data, dict) else data

        # 4. Difficulty
        p = base_constraints / 'difficulty.json'
        if p.exists():
            data = json.loads(p.read_text(encoding='utf-8'))
            vocab["difficulty"] = data.get('difficulty', data) if isinstance(data, dict) else data

        # 5. Cuisines
        p = base_post / 'cuisines.json'
        if p.exists():
            data = json.loads(p.read_text(encoding='utf-8'))
            vocab["cuisines"] = data.get('cuisines', data) if isinstance(data, dict) else data

        # 6. Cooking Methods
        p = base_post / 'cooking_methods.json'
        if p.exists():
            data = json.loads(p.read_text(encoding='utf-8'))
            # If list of objects, flatten to method names
            raw = data.get('cooking_methods', data) if isinstance(data, dict) else data
            if isinstance(raw, list) and len(raw) > 0 and isinstance(raw[0], dict):
                vocab["cooking_methods"] = [m.get('method') for m in raw]
            else:
                 vocab["cooking_methods"] = raw

        # 7. Taste
        p = base_post / 'taste.json'
        if p.exists():
            data = json.loads(p.read_text(encoding='utf-8'))
            vocab["tastes"] = data.get('tastes', data) if isinstance(data, dict) else data

        # 8. Time Intervals
        p = base_post / 'time_intervals.json'
        if p.exists():
            data = json.loads(p.read_text(encoding='utf-8'))
            vocab["time_intervals"] = data.get('time_intervals', data) if isinstance(data, dict) else data

        # 9. Cleanup Factors
        p = base_post / 'cleanup_factors.json'
        if p.exists():
            data = json.loads(p.read_text(encoding='utf-8'))
            # Assuming simple list or needing string conversion
            raw = data.get('cleanup_factors', data) if isinstance(data, dict) else data
            vocab["cleanup_factors"] = [str(x) for x in raw]

        return vocab

    except Exception as e:
        print(f"⚠️ Warning: Error loading controlled vocabularies: {e}")
        return vocab

FUZZY_MATCH_THRESHOLD = 90  # per word, see _match_score

# Cooking qualifiers to strip before fuzzy matching.
# These appear as adjectives/suffixes and add noise that dilutes match scores.
COOKING_QUALIFIERS = {
    # Words dropped before matching, but only when other words remain.
    # Never add words that change what the ingredient is (salted/unsalted,
    # dried, canned, frozen, pickled, smoked, roasted, light, dark): smoked
    # salmon is not salmon.
    # Preparation styles
    'diced', 'chopped', 'minced', 'sliced', 'crushed', 'crumbled',
    'grated', 'shredded', 'julienned', 'cubed', 'halved', 'quartered',
    'torn', 'mashed', 'pureed', 'zested', 'peeled', 'deseeded',
    'pitted', 'cored', 'trimmed', 'deboned', 'deveined', 'seeded',
    # State
    'fresh', 'uncooked', 'cooked', 'raw', 'ripe',
    'softened', 'melted', 'chilled', 'warmed', 'blanched',
    # Size / shape / variety descriptors
    'boneless', 'skinless', 'whole', 'large', 'small',
    'medium', 'thin', 'thick', 'finely', 'roughly', 'thinly',
    'lrg', 'sml', 'med', 'roma', 'english',
    'leaves', 'slices', 'sprigs', 'stalks',
    # Quality / measuring
    'organic', 'pure', 'packed', 'loosely', 'firmly',
}

def normalize_ingredient_name(name: str) -> str:
    """
    Strip cooking qualifiers and descriptors to get the core ingredient name.
    Examples:
      "English cucumber, diced"  → "english cucumber"
      "feta cheese, crumbled"    → "feta cheese"
      "chicken breasts, boneless and skinless" → "chicken breasts"
      "lime juice"               → "lime juice"  (unchanged — 'juice' is meaningful)
    """
    if not name:
        return name
    n = name.lower().strip()
    # 1. Remove parenthetical clarifiers: "pickled cucumbers (dill pickles)" → "pickled cucumbers"
    n = re.sub(r'\(.*?\)', '', n).strip()
    # 2. Split on comma — take only the first part (before ", diced" etc.)
    n = n.split(',')[0].strip()
    # 3. Remove remaining qualifying words
    words = n.split()
    cleaned = [w for w in words if w not in COOKING_QUALIFIERS]
    return ' '.join(cleaned).strip() if cleaned else n

def _singular(word: str) -> str:
    if len(word) > 4 and word.endswith('ves'):
        return word[:-3] + 'f'
    if len(word) > 4 and word.endswith('ies'):
        return word[:-3] + 'y'
    if len(word) > 4 and word.endswith(('oes', 'ches', 'shes')):
        return word[:-2]
    if len(word) > 3 and word.endswith('s') and not word.endswith('ss'):
        return word[:-1]
    return word


def _name_tokens(name: str) -> list[str]:
    return sorted({_singular(w) for w in re.findall(r"[^\W_]+", name.lower())})


def _match_score(query: str, key: str) -> float:
    """0-100. Both names must have the same words, allowing small spelling
    differences per word (chilli/chili, yoghurt/yogurt, plurals). An extra
    word means no match, because in food it changes the ingredient: garlic
    vs garlic powder, water vs canned tuna in water, salted vs unsalted."""
    from thefuzz import fuzz as fuzz_scorer

    q_tokens, k_tokens = _name_tokens(query), _name_tokens(key)
    if not q_tokens or len(q_tokens) != len(k_tokens):
        return 0
    remaining = list(k_tokens)
    scores = []
    for token in q_tokens:
        best = max(remaining, key=lambda k: fuzz_scorer.ratio(token, k))
        score = fuzz_scorer.ratio(token, best)
        if score < FUZZY_MATCH_THRESHOLD:
            return 0
        scores.append(score)
        remaining.remove(best)
    return sum(scores) / len(scores)


def _fuzzy_match(query: str, pantry_keys: list[str]) -> str | None:
    """
    Best pantry key whose words all match the query's words. Returns food_id or None.

    Precision beats recall here: a miss creates a pending ingredient that an
    admin reviews (and merging it adds an alias), while a wrong match silently
    puts the wrong ingredient in a recipe.
    """
    best_key, best_score = None, 0
    for key in pantry_keys:
        score = _match_score(query, key)
        if score > best_score:
            best_key, best_score = key, score
    if best_key:
        print(f"🔗 Fuzzy Match: '{query}' → '{best_key}' (score: {best_score:.0f})")
        return pantry_map[best_key]
    return None


def get_pantry_id(name: str):
    """
    Resolves an ingredient name to a pantry food_id.
    
    When the name contains cooking qualifiers (normalization changes it),
    the NORMALIZED version is tried first to prevent duplicate ingredients
    from poisoning exact matches. For clean names, raw exact match fires first.
    
    Strategy:
      If name has qualifiers (normalized ≠ raw):
        1. Exact match on normalized name
        2. Fuzzy match on normalized name
        3. Exact match on raw name (fallback)
        4. Fuzzy match on raw name (final fallback)
      If name is already clean (normalized == raw):
        1. Exact match on raw name
        2. Fuzzy match on raw name
    
    Returns the food_id string or None if no confident match.
    """
    if not name:
        return None
    if not pantry_map:
        print(f"⚠️  get_pantry_id called but pantry_map is EMPTY — cannot match '{name}'")
        return None

    n_lower = name.strip().lower()
    n_clean = normalize_ingredient_name(name)
    was_normalized = n_clean and n_clean != n_lower
    pantry_keys = list(pantry_map.keys())

    if was_normalized:
        # --- Normalized name takes priority (prevents duplicate matches) ---
        # 1. Exact match on normalized name
        if n_clean in pantry_map:
            print(f"🔗 Normalized Exact Match: '{name}' → '{n_clean}'")
            return pantry_map[n_clean]

        # 2. Fuzzy match on normalized name
        result_clean = _fuzzy_match(n_clean, pantry_keys)
        if result_clean:
            print(f"    ↳ (after normalizing '{name}' → '{n_clean}')")
            return result_clean

    # 3. Exact match on raw name (first check for clean names, fallback for normalized)
    if n_lower in pantry_map:
        return pantry_map[n_lower]

    # 4. Fuzzy match on raw name (final fallback)
    result = _fuzzy_match(n_lower, pantry_keys)
    if result:
        return result

    # Nothing matched
    print(f"⚠️  No match for '{name}' (normalized: '{n_clean}') — threshold: {FUZZY_MATCH_THRESHOLD}")
    return None

def set_pantry_memory(slim_context):
    """
    Rebuilds pantry_map from DB ingredients via slim_context.

    Two-pass strategy:
      Pass 1: Add all staple pantry items (is_staple=True).
      Pass 2: Add non-staple items ONLY if their normalized form
              doesn't collide with an existing map entry.
    
    The map is built in full and then swapped in, so a request running at
    the same time never sees it empty or half filled.
    """
    global pantry_map
    new_map = {}
    
    added_staple = 0
    added_standard = 0
    skipped = 0
    
    # Pass 1: Staple pantry items take priority
    for item in slim_context:
        name = item.get('n', item.get('name'))
        pantry_id = item.get('i', item.get('id'))
        is_staple = item.get('s', item.get('is_staple', False))
        
        # We now ALLOW IMP- IDs here because the upstream context generator
        # (pantry_service) already filters by `status == 'active'`. If it's active,
        # it's considered valid for injection.
        
        if name and pantry_id and is_staple:
            new_map[name.lower()] = pantry_id
            added_staple += 1
    
    # Pass 2: Non-staple items — add only if not a decorated duplicate
    for item in slim_context:
        name = item.get('n', item.get('name'))
        pantry_id = item.get('i', item.get('id'))
        is_staple = item.get('s', item.get('is_staple', False))
        
        if not name or not pantry_id or is_staple:
            continue
        
        # We now ALLOW IMP- IDs here for valid, active non-staple ingredients.
        
        n_lower = name.lower()
        n_clean = normalize_ingredient_name(name)
        
        # Skip if raw name already in map (staple takes precedence)
        if n_lower in new_map:
            skipped += 1
            continue
        # Skip if normalized form already in map (it's a decorated duplicate)
        if n_clean != n_lower and n_clean in new_map:
            skipped += 1
            continue
        
        # Clean standard item — add it (e.g. "olive", "avocado")
        new_map[n_lower] = pantry_id
        added_standard += 1
    
    pantry_map = new_map
    total = added_staple + added_standard
    print(f"📦 set_pantry_memory: {total} items ({added_staple} staples + {added_standard} standard active), skipped {skipped} duplicates/imports")

def analyze_ingredient_ai(prompt: str, valid_categories: dict) -> dict:
    
    print(f"DEBUG: Analyzing ingredient '{prompt}' via {GEMINI_TEXT}")
    
    # Load prompt from studio template
    from utils.prompt_manager import load_prompt
    
    system_prompt = load_prompt('ingredient_text/ingredient_analysis.jinja2', 
        user_input=prompt,
        valid_categories_json=json.dumps(valid_categories['main_categories']),
        valid_subcategories_json=json.dumps(valid_categories['sub_categories'])
    )

    try:
        response = client.models.generate_content(
            model=GEMINI_TEXT,
            contents=system_prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=IngredientAnalysisSchema
            )
        )
        
        if response.parsed:
            return response.parsed
        return json.loads(response.text)
        
    except Exception as e:
        print(f"ERROR: Ingredient Analysis failed: {e}")
        raise ValueError(f"AI Analysis failed: {e}")


# --- Nutrient Extraction from Text Dump ---
class NutrientExtractionSchema(typing.TypedDict):
    calories_per_100g: float
    kj_per_100g: float
    protein_per_100g: float
    fat_per_100g: float
    fat_saturated_per_100g: float
    carbs_per_100g: float
    sugar_per_100g: float
    fiber_per_100g: float
    sodium_mg_per_100g: float
    serving_size_note: str

def extract_nutrients_from_text(raw_text: str, ingredient_name: str = "") -> dict:
    """
    Extracts structured nutrition data from raw pasted text.
    Handles nutrition labels, website copy, product packaging text, etc.
    Normalises all values to per-100g.
    """
    print(f"🔬 Extracting nutrients from text dump for '{ingredient_name}'")

    prompt = f"""
    ROLE: Nutrition Data Analyst.
    TASK: Extract nutritional information from the text below and return it **normalised to per 100g**.

    INGREDIENT CONTEXT: {ingredient_name or "Unknown"}

    RAW TEXT:
    {raw_text[:8000]}

    CRITICAL RULES:
    1. The text may contain nutrition data in any format: tables, labels, prose, bullet points.
    2. Data might be "per serving", "per 85g", "per 250ml", "per slice", etc. You MUST convert ALL values to per 100g.
       - Example: If the label says "Calories: 140 per serving (50g)", then calories_per_100g = 140 * (100/50) = 280.
       - Example: If the label says "Protein: 8g per 30g serving", then protein_per_100g = 8 * (100/30) = 26.67.
    3. If a value is missing from the text, use 0.
    4. If sodium is given in grams, convert to mg (multiply by 1000).
    5. If salt is given instead of sodium, divide by 2.5 to get sodium.
    6. If kJ is missing but kcal is present, compute: kJ = kcal * 4.184.
    7. If kcal is missing but kJ is present, compute: kcal = kJ / 4.184.
    8. Record what serving size the original data was in (for transparency).
    9. Ignore any non-nutritional text (marketing, ingredients lists, allergens, etc.).
    """

    try:
        response = client.models.generate_content(
            model=GEMINI_TEXT,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=NutrientExtractionSchema
            )
        )

        if response.parsed:
            result = response.parsed
        else:
            result = json.loads(response.text)

        print(f"✅ Nutrients extracted: {result.get('calories_per_100g', '?')} kcal/100g "
              f"(source: {result.get('serving_size_note', 'unknown')})")
        return result

    except Exception as e:
        print(f"ERROR: Nutrient extraction failed: {e}")
        raise ValueError(f"Nutrient extraction failed: {e}")
