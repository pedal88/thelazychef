import os
import re
import json
import uuid
import typing_extensions as typing # For TypedDict compatibility
from pathlib import Path
from thefuzz import process as fuzz_process
from dotenv import load_dotenv
from google import genai
from google.genai import types
from jinja2 import Environment, FileSystemLoader

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

client = genai.Client(api_key=api_key)

# --- Pydantic/TypedDict Schema Definitions ---
# Using TypedDict as requested for Gemini response_schema

class Ingredient(typing.TypedDict):
    name: str
    amount: float
    unit: str
    gram_weight_estimate: float
    pantry_id: typing.NotRequired[str]  # Optional: Pre-resolved pantry food_id from LLM

class IngredientGroup(typing.TypedDict):
    component: str
    ingredients: list[Ingredient]

class Instruction(typing.TypedDict):
    step_number: int
    phase: str # 'Prep', 'Cook', 'Serve'
    text: str
    estimated_minutes: int
    global_order_index: int

class ComponentSchema(typing.TypedDict):
    name: str # e.g., "The Steak", "Garlic Butter Sauce", "Main Dish"
    steps: list[Instruction]

class RecipeSchema(typing.TypedDict):
    title: str
    cuisine: str
    diet: list[str]  # All diets that apply (e.g. ["vegan", "gluten-free"])
    difficulty: str
    protein_type: str
    meal_types: list[str]
    chef_id: str
    # Numeric metadata (Critical for App Compatibility)
    cleanup_factor: int 
    taste_level: int
    prep_time_mins: int
    
    ingredient_groups: list[IngredientGroup]
    components: list[ComponentSchema]  # CHANGED: From instructions to components
    chef_note: str
    
    # Safe Failure Flags (Optional)
    is_valid_recipe: typing.NotRequired[bool]
    error_reason: typing.NotRequired[str]

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
class RecipeObj:
    def __init__(self, **entries):
        self.__dict__.update(entries)
        # Handle nested objects for dot access
        if 'ingredient_groups' in entries:
            self.ingredient_groups = [
                RecipeObj(**g) if isinstance(g, dict) else g 
                for g in entries['ingredient_groups']
            ]
            for group in self.ingredient_groups:
                if hasattr(group, 'ingredients'):
                    group.ingredients = [RecipeObj(**i) if isinstance(i, dict) else i for i in group.ingredients]
        
        # Handle NEW nested components
        if 'components' in entries:
            self.components = [RecipeObj(**c) if isinstance(c, dict) else c for c in entries['components']]
            for comp in self.components:
                if hasattr(comp, 'steps'):
                    comp.steps = [RecipeObj(**s) if isinstance(s, dict) else s for s in comp.steps]

# --- Data Loading (Retaining Pantry/Chef Context) ---
# --- Data Loading (Retaining Pantry/Chef Context) ---
SYNONYMS_PATH = os.path.join(os.path.dirname(__file__), 'data', 'constraints', 'synonyms.json')

def load_json(path):
    with open(path, 'r') as f:
        return json.load(f)

def load_pantry_memory():
    """Loads pantry data and user-defined synonyms into memory."""
    global pantry_map
    pantry_map = {}
    
    # 1. Load Main Pantry (Seed Data)
    try:
        pantry_data = load_json("data/constraints/pantry.json")
        for item in pantry_data:
            # Handle both list formats if legacy exists
            n = item.get('food_name', item.get('name', '')).lower()
            i = item.get('food_id', item.get('id', ''))
            if n and i:
                pantry_map[n] = i
    except Exception as e:
        print(f"Warning: Error loading pantry.json: {e}")

    # 2. Load User Synonyms (Overrides)
    if os.path.exists(SYNONYMS_PATH):
        try:
            with open(SYNONYMS_PATH, 'r') as f:
                syns = json.load(f)
                for name, fid in syns.items():
                    pantry_map[name.lower()] = fid
        except Exception as e:
            print(f"Warning: Error loading synonyms.json: {e}")

# Initialize empty - will be populated by app via set_pantry_memory(db_context)
pantry_map = {}

# DEPRECATED: We no longer load from JSON on import. Database source of truth only.
# load_pantry_memory()


# --- RESTORED EXPORTS FOR APP COMPATIBILITY ---
try:
    chefs_data = load_json("data/agents/chefs.json")['chefs']
except Exception:
    chefs_data = []

try:
    protein_data = load_json("data/constraints/main_protein.json")['protein_types']
except Exception:
    protein_data = []

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

def generate_recipe_from_web_text(text: str, source_url: str = "User Input", slim_context: list[dict] = None) -> RecipeObj:
    """
    Generates a recipe from raw text (e.g. from a website extract or manual paste).
    Sends full pantry context (with food_ids) so the LLM can pre-resolve
    ingredient matches via the pantry_id field.
    """
    if slim_context:
        set_pantry_memory(slim_context)
        pantry_str = json.dumps(slim_context)
    else:
        # Fallback to name-only list from static map
        pantry_str = json.dumps([{"n": k, "i": v} for k, v in pantry_map.items()])
    
    # Load Controlled Vocabularies
    vocab = load_controlled_vocabularies()
    
    # Initialize basic user constraints - for web/video extraction we assume neutral constraints
    # unless extracted, but the prompt handles classification.
    # We pass an empty dict for strict constraints unless valid metadata is passed in.
    user_constraints = {}

    # Use Jinja2 Template
    try:
        template = env.get_template('recipe_text/web_extraction.jinja2')
        prompt = template.render(
            source_url=source_url,
            pantry_context=pantry_str,
            raw_text=text,
            vocab=vocab,
            user_constraints=user_constraints
        )

    except Exception as e:
        print(f"ERROR: Failed to render web_extraction template: {e}")
        raise ValueError(f"Template rendering failed: {e}")
    
    print(f"DEBUG: Generating from Web Text via 'gemini-flash-latest' (with pantry IDs)")
    response = client.models.generate_content(
        model='gemini-flash-latest',
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=RecipeSchema
        )
    )

    try:
        if response.parsed:
             return RecipeObj(**response.parsed)

        data = json.loads(response.text)
        return RecipeObj(**data)
    except Exception as e:
        print(f"ERROR: Web Generation failed. Raw output: {response.text[:200]}")
        raise ValueError(f"AI Generation failed: {e}")

# Fuzzy matching threshold — scores below this are rejected.
# 85 works well for food names: "Lrg Eggs" → "Whole Eggs" (88), 
# but "Salt" ≠ "Unsalted Butter" (45).
FUZZY_MATCH_THRESHOLD = 85

# Cooking qualifiers to strip before fuzzy matching.
# These appear as adjectives/suffixes and add noise that dilutes match scores.
COOKING_QUALIFIERS = {
    # Preparation styles
    'diced', 'chopped', 'minced', 'sliced', 'crushed', 'crumbled',
    'grated', 'shredded', 'julienned', 'cubed', 'halved', 'quartered',
    'torn', 'mashed', 'pureed', 'zested', 'peeled', 'deseeded',
    'pitted', 'cored', 'trimmed', 'deboned', 'deveined', 'seeded',
    # Temperature / State
    'fresh', 'frozen', 'dried', 'canned', 'uncooked', 'cooked',
    'raw', 'roasted', 'toasted', 'smoked', 'pickled', 'marinated',
    'softened', 'melted', 'chilled', 'warmed', 'blanched', 'ripe',
    # Size / Descriptor
    'boneless', 'skinless', 'whole', 'large', 'small',
    'medium', 'thin', 'thick', 'finely', 'roughly', 'thinly',
    'extra', 'lrg', 'sml', 'med',
    # Descriptor / Quality
    'organic', 'pure', 'virgin', 'unsalted', 'salted',
    'packed', 'loosely', 'firmly', 'light', 'dark',
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

def _fuzzy_match(query: str, pantry_keys: list[str]) -> str | None:
    """
    Run fuzzy matching against pantry_keys. Returns food_id or None.
    Uses WRatio first, then token_set_ratio as fallback.
    """
    from thefuzz import fuzz as fuzz_scorer
    
    # Stage A: WRatio (good for similar-length strings)
    result = fuzz_process.extractOne(query, pantry_keys)
    if result:
        matched_key, score = result
        if score >= FUZZY_MATCH_THRESHOLD:
            print(f"🔗 Fuzzy Match (WRatio): '{query}' → '{matched_key}' (score: {score})")
            return pantry_map[matched_key]

    # Stage B: token_set_ratio (handles subsets: "feta" inside "feta cheese")
    result_tsr = fuzz_process.extractOne(query, pantry_keys, scorer=fuzz_scorer.token_set_ratio)
    if result_tsr:
        matched_key_tsr, score_tsr = result_tsr
        if score_tsr >= FUZZY_MATCH_THRESHOLD:
            print(f"🔗 Fuzzy Match (token_set): '{query}' → '{matched_key_tsr}' (score: {score_tsr})")
            return pantry_map[matched_key_tsr]
    
    return None

def add_synonym(name: str, food_id: str):
    """
    Adds a manual synonym mapping (e.g. 'Soy Milk' -> '000123') and persists it.
    This allows the AI to resolve missing ingredients to existing pantry items in future runs.
    """
    syns = {}
    if os.path.exists(SYNONYMS_PATH):
        try:
            with open(SYNONYMS_PATH, 'r') as f:
                syns = json.load(f)
        except: pass
        
    syns[name.lower()] = food_id
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(SYNONYMS_PATH), exist_ok=True)
    
    with open(SYNONYMS_PATH, 'w') as f:
        json.dump(syns, f, indent=2)
        
    # Update memory immediately
    if 'pantry_map' in globals():
        pantry_map[name.lower()] = food_id
    print(f"✅ Added Synonym: '{name}' -> '{food_id}'")
    return True


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

def get_top_pantry_suggestions(name: str, top_n: int = 3) -> list[dict]:
    """
    Returns the top N fuzzy matches from pantry_map for a given ingredient name.
    Unlike get_pantry_id (which returns only the best match above threshold),
    this returns multiple ranked suggestions with scores — useful for
    showing substitute candidates in the UI.
    
    Returns: [{"name": str, "food_id": str, "score": int}, ...]
    """
    if not name or not pantry_map:
        return []
    
    from thefuzz import fuzz as fuzz_scorer
    
    n_lower = name.strip().lower()
    n_clean = normalize_ingredient_name(name)
    pantry_keys = list(pantry_map.keys())
    
    # Collect candidates from both raw and normalized names, both scorers
    candidates = {}  # key → best_score
    
    queries = [n_lower]
    if n_clean and n_clean != n_lower:
        queries.append(n_clean)
    
    for query in queries:
        # WRatio matches
        results_wr = fuzz_process.extract(query, pantry_keys, limit=top_n * 2)
        for matched_key, score in results_wr:
            if matched_key not in candidates or score > candidates[matched_key]:
                candidates[matched_key] = score
        
        # token_set_ratio matches
        results_tsr = fuzz_process.extract(query, pantry_keys, scorer=fuzz_scorer.token_set_ratio, limit=top_n * 2)
        for matched_key, score in results_tsr:
            if matched_key not in candidates or score > candidates[matched_key]:
                candidates[matched_key] = score
    
    # Sort by score descending, take top N
    sorted_candidates = sorted(candidates.items(), key=lambda x: x[1], reverse=True)[:top_n]
    
    return [
        {"name": key, "food_id": pantry_map[key], "score": score}
        for key, score in sorted_candidates
    ]

def set_pantry_memory(slim_context):
    """
    Populates pantry_map from DB ingredients via slim_context.
    
    CLEARS the map first to prevent accumulation across calls.
    
    Two-pass strategy:
      Pass 1: Add all staple pantry items (is_staple=True).
      Pass 2: Add non-staple items ONLY if their normalized form
              doesn't collide with an existing map entry.
    
    IMP- food_ids are ALWAYS rejected (auto-created duplicates).
    """
    pantry_map.clear()  # Prevent accumulation across calls
    
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
            pantry_map[name.lower()] = pantry_id
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
        if n_lower in pantry_map:
            skipped += 1
            continue
        # Skip if normalized form already in map (it's a decorated duplicate)
        if n_clean != n_lower and n_clean in pantry_map:
            skipped += 1
            continue
        
        # Clean standard item — add it (e.g. "olive", "avocado")
        pantry_map[n_lower] = pantry_id
        added_standard += 1
    
    total = added_staple + added_standard
    print(f"📦 set_pantry_memory: {total} items ({added_staple} staples + {added_standard} standard active), skipped {skipped} duplicates/imports")

# --- Core Generation Function ---
def generate_recipe_ai(
    query: str, 
    slim_context: list[dict] = None, 
    chef_id: str = "gourmet",
    target_diet: str = None,
    target_cuisine: str = None,
    target_method: str = None,
    target_protein: str = None
) -> RecipeObj:
    
    if slim_context:
        set_pantry_memory(slim_context)
        pantry_str = json.dumps(slim_context)
    else:
        pantry_str = "[]"

    # Chef Context
    chef_context = f"You are acting as the Chef ID: {chef_id}."

    # Load Vocabularies
    vocab = load_controlled_vocabularies()

    # Build User Constraints Dictionary for Template Injection
    user_constraints = {
        "diet": target_diet,
        "cuisine": target_cuisine,
        "cooking_method": target_method,
        "protein": target_protein
    }
    
    # Load Template
    try:
        template = env.get_template('recipe_text/recipe_generation.jinja2')
        prompt = template.render(
            chef_context=chef_context,
            query=query,
            pantry_context=pantry_str,
            vocab=vocab,
            user_constraints=user_constraints
        )
    except Exception as e:
        print(f"Error loading prompt template: {e}")
        raise ValueError(f"Template rendering failed: {e}")




    print(f"DEBUG: Using Model 'gemini-flash-latest' with Few-Shot Prompt")
    
    response = client.models.generate_content(
        model='gemini-flash-latest',
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=RecipeSchema
        )
    )

    # === CRITICAL DEBUG LOGGING ===
    print("\n" + "="*80)
    print("RAW AI RESPONSE (Full JSON):")
    print("="*80)
    print(response.text)
    print("="*80 + "\n")
    
    # Parse and count instructions
    try:
        parsed_data = response.parsed if response.parsed else json.loads(response.text)
        instruction_count = len(parsed_data.get('instructions', []))
        print(f"🔍 INSTRUCTION COUNT IN AI RESPONSE: {instruction_count}")
        for idx, instr in enumerate(parsed_data.get('instructions', []), 1):
            print(f"  Step {idx}: [{instr.get('phase')}] {instr.get('text', '')[:60]}...")
        print("="*80 + "\n")
    except Exception as debug_err:
        print(f"⚠️  Debug parsing failed: {debug_err}")
    
    # Normalization Helper
    def normalize_recipe_data(data_dict):
        # 1. Component Mismatch Fix (Single Component)
        # If there is exactly 1 component and 1 ingredient group, force them to match.
        # Priority is given to the Component Name (from instructions).
        if 'components' in data_dict and 'ingredient_groups' in data_dict:
            comps = data_dict['components']
            ings = data_dict['ingredient_groups']
            
            if isinstance(comps, list) and isinstance(ings, list):
                if len(comps) == 1 and len(ings) == 1:
                    # Check for mismatch
                    c_name = comps[0].get('name')
                    i_name = ings[0].get('component')
                    
                    if c_name and i_name and c_name != i_name:
                        print(f"🔧 Normalizing Component Mismatch: Ingredients '{i_name}' -> '{c_name}'")
                        ings[0]['component'] = c_name
        return data_dict

    # Original logic
    try:
        if response.parsed:
             # Convert Dict to Object for App Compatibility
             data = response.parsed
             if isinstance(data, dict):
                 data = normalize_recipe_data(data)
             return RecipeObj(**data)
        
        # Fallback if parsed is empty (rare with native schema)
        data = json.loads(response.text)
        data = normalize_recipe_data(data)
        return RecipeObj(**data)

    except Exception as e:
        print(f"ERROR: Generation failed. Raw output: {response.text[:200]}")
        raise ValueError(f"AI Generation failed: {e}")

# --- Video Generation (Retained for Safety) ---
def generate_recipe_from_video(video_path: str, caption: str, slim_context: list[dict] = None, chef_id: str = "gourmet"):
    """
    Generates a structured recipe from a video file (TikTok/Reel).
    Sends full pantry context so the LLM can pre-resolve ingredient IDs.
    """
    if slim_context:
        set_pantry_memory(slim_context)
        pantry_str = json.dumps(slim_context)
    else:
        pantry_str = json.dumps([{"n": k, "i": v} for k, v in pantry_map.items()])

    print(f"🎬 Uploading video to Gemini: {video_path}")
    file_ref = client.files.upload(file=video_path)
    
    import time
    while True:
        file_info = client.files.get(name=file_ref.name)
        if file_info.state == "ACTIVE":
            break
        elif file_info.state == "FAILED":
            raise ValueError("Video processing failed")
        time.sleep(2)

    # Load Controlled Vocabularies
    vocab = load_controlled_vocabularies()
    user_constraints = {} # Videos are extraction tasks, usually no pre-constraints

    try:
        template = env.get_template('recipe_text/video_extraction.jinja2')
        prompt = template.render(
            caption=caption,
            chef_id=chef_id,
            pantry_context=pantry_str,
            vocab=vocab,
            user_constraints=user_constraints
        )
    except Exception as e:
        print(f"ERROR: Failed to render video_extraction template: {e}")
        raise ValueError(f"Template rendering failed: {e}")
    
    print(f"DEBUG: Generating from Video via 'gemini-flash-latest' (with pantry IDs)")
    
    response = client.models.generate_content(
        model='gemini-flash-latest',
        contents=[file_ref, prompt],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=RecipeSchema
        )
    )
    
    
    recipe_dict = response.parsed if response.parsed else json.loads(response.text)
    
    # Check if the AI explicitly flagged this as NOT a recipe
    if recipe_dict.get('is_valid_recipe') is False:
        reason = recipe_dict.get('error_reason', 'The provided media does not appear to contain a recipe.')
        raise ValueError(f"AI rejected extraction: {reason}")
        
    return RecipeObj(**recipe_dict)

# --- Ingredient Analysis ---
def analyze_ingredient_ai(prompt: str, valid_categories: dict) -> dict:
    
    print(f"DEBUG: Analyzing ingredient '{prompt}' via 'gemini-flash-latest'")
    
    # Load prompt from studio template
    from utils.prompt_manager import load_prompt
    
    system_prompt = load_prompt('ingredient_text/ingredient_analysis.jinja2', 
        user_input=prompt,
        valid_categories_json=json.dumps(valid_categories['main_categories']),
        valid_subcategories_json=json.dumps(valid_categories['sub_categories'])
    )

    try:
        response = client.models.generate_content(
            model='gemini-flash-latest',
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
            model='gemini-flash-latest',
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
#