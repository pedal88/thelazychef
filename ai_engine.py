
import os
import re
import json
import uuid
import typing_extensions as typing # For TypedDict compatibility
from thefuzz import process as fuzz_process
from dotenv import load_dotenv
from google import genai
from google.genai import types

# Load Environment
load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")

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
    pantry_id: typing.NotRequired[str]  # Optional: Pre-resolved pantry food_id from LLM

class IngredientGroup(typing.TypedDict):
    component: str
    ingredients: list[Ingredient]

class Instruction(typing.TypedDict):
    step_number: int
    phase: str # 'Prep', 'Cook', 'Serve'
    text: str

class ComponentSchema(typing.TypedDict):
    name: str # e.g., "The Steak", "Garlic Butter Sauce", "Main Dish"
    steps: list[Instruction]

class RecipeSchema(typing.TypedDict):
    title: str
    cuisine: str
    diet: str
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
def load_json(path):
    with open(path, 'r') as f:
        return json.load(f)

try:
    pantry_data = load_json("data/constraints/pantry.json")
    # pantry.json is a flat list of dicts with 'food_name' and 'food_id' keys
    if isinstance(pantry_data, list):
        pantry_map = {item['food_name'].lower(): item['food_id'] for item in pantry_data if 'food_name' in item and 'food_id' in item}
    elif isinstance(pantry_data, dict) and 'ingredients' in pantry_data:
        pantry_map = {item.get('name', item.get('food_name', '')).lower(): item.get('id', item.get('food_id', '')) for item in pantry_data['ingredients']}
    else:
        pantry_map = {}
    print(f"✅ pantry_map loaded with {len(pantry_map)} entries from pantry.json")
except Exception as e:
    print(f"⚠️  Failed to load pantry.json: {e}")
    pantry_map = {}

# --- RESTORED EXPORTS FOR APP COMPATIBILITY ---
try:
    chefs_data = load_json("data/agents/chefs.json")['chefs']
except Exception:
    chefs_data = []

try:
    protein_data = load_json("data/constraints/main_protein.json")['protein_types']
except Exception:
    protein_data = []

def generate_recipe_from_web_text(text: str, source_url: str, slim_context: list[dict] = None) -> RecipeObj:
    """
    Generates a recipe from raw text (e.g. from a website extract).
    Sends full pantry context (with food_ids) so the LLM can pre-resolve
    ingredient matches via the pantry_id field.
    """
    if slim_context:
        set_pantry_memory(slim_context)
        pantry_str = json.dumps(slim_context)
    else:
        # Fallback to name-only list from static map
        pantry_str = json.dumps([{"n": k, "i": v} for k, v in pantry_map.items()])
    
    prompt = f"""
    ROLE: Data Engineer.
    TASK: Extract a structured recipe from this text content.
    SOURCE URL: {source_url}
    
    PANTRY INVENTORY (JSON — 'i' = ingredient ID, 'n' = name):
    {pantry_str}
    
    CONTENT:
    {text[:15000]}
    
    PANTRY ID INJECTION RULE (CRITICAL):
    For EACH ingredient in the recipe:
    - Search the PANTRY INVENTORY above for a match (even partial, e.g. "diced onions" → pantry "onions").
    - If it matches, you MUST:
      1. Use the EXACT 'n' (name) value from the pantry as the ingredient name.
      2. Include its 'i' value in the 'pantry_id' field.
    - If the ingredient is truly NEW and not in the pantry, set 'pantry_id' to null and use a clean, generic name.
    - ALWAYS prefer existing pantry names over creating new variations.
    - Examples:
      * "boneless skinless chicken breasts" → pantry has "chicken breast" → use name="chicken breast", pantry_id="000xxx"
      * "English cucumber, diced" → pantry has "cucumber" → use name="cucumber", pantry_id="000xxx"  
      * "feta cheese, crumbled" → pantry has "feta cheese" → use name="feta cheese", pantry_id="000xxx"
      * "lemons, juiced" → pantry has "lemon" → use name="lemon", pantry_id="000xxx"
    
    OTHER RULES:
    1. Extract the title, cuisine, diet, etc.
    2. Infer numeric values for taste_level, prep_time_mins, cleanup_factor, etc.
    3. Structure instructions into Prep/Cook/Serve phases with separate components.
    """
    
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
      Pass 1: Add all original pantry items (is_original=True).
      Pass 2: Add non-original items ONLY if their normalized form
              doesn't collide with an existing map entry.
    
    IMP- food_ids are ALWAYS rejected (auto-created duplicates).
    """
    pantry_map.clear()  # Prevent accumulation across calls
    
    added_orig = 0
    added_user = 0
    skipped = 0
    
    # Pass 1: Original pantry items take priority
    for item in slim_context:
        name = item.get('n', item.get('name'))
        pantry_id = item.get('i', item.get('id'))
        is_original = item.get('o', item.get('is_original', True))
        
        # Never add IMP- duplicates
        if pantry_id and str(pantry_id).startswith('IMP-'):
            skipped += 1
            continue
        
        if name and pantry_id and is_original:
            pantry_map[name.lower()] = pantry_id
            added_orig += 1
    
    # Pass 2: Non-original items — add only if not a decorated duplicate
    for item in slim_context:
        name = item.get('n', item.get('name'))
        pantry_id = item.get('i', item.get('id'))
        is_original = item.get('o', item.get('is_original', True))
        
        if not name or not pantry_id or is_original:
            continue
        
        # Never add IMP- duplicates
        if str(pantry_id).startswith('IMP-'):
            skipped += 1
            continue
        
        n_lower = name.lower()
        n_clean = normalize_ingredient_name(name)
        
        # Skip if raw name already in map (original takes precedence)
        if n_lower in pantry_map:
            skipped += 1
            continue
        # Skip if normalized form already in map (it's a decorated duplicate)
        if n_clean != n_lower and n_clean in pantry_map:
            skipped += 1
            continue
        
        # Clean user-created item — add it (e.g. "olive", "avocado")
        pantry_map[n_lower] = pantry_id
        added_user += 1
    
    total = added_orig + added_user
    print(f"📦 set_pantry_memory: {total} items ({added_orig} original + {added_user} user-created), skipped {skipped} duplicates/imports")

# --- Core Generation Function ---
def generate_recipe_ai(query: str, slim_context: list[dict] = None, chef_id: str = "gourmet") -> RecipeObj:
    
    if slim_context:
        set_pantry_memory(slim_context)
        pantry_str = json.dumps(slim_context)
    else:
        pantry_str = "[]"

    # Chef Context
    chef_context = f"You are acting as the Chef ID: {chef_id}."

    
    # Load Template
    try:
        from jinja2 import Environment, FileSystemLoader
        env = Environment(loader=FileSystemLoader(os.path.join(os.path.dirname(__file__), 'data', 'prompts')))
        template = env.get_template('recipe_text/recipe_generation.jinja2')
        prompt = template.render(
            chef_context=chef_context,
            query=query,
            pantry_context=pantry_str
        )
    except Exception as e:
        print(f"Error loading prompt template: {e}")
        # Fallback (Safety)
        prompt = f"""
        You are a precise Data Engineer Chef.
        {chef_context}
        GOAL: Generate a structured recipe for: "{query}" using these ingredients: {pantry_str}.
        """




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
    # Reuse the same schema logic ideally, for now just a stub or basic version
    # Since user emphasized 'Rewrite entire file', we keep a minimal working version
    
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

    prompt = f"""
    Watch this video and create a structured recipe.
    Caption: {caption}
    Chef ID: {chef_id}
    
    CRITICAL: Follow the same strict multi-step rules:
    1. At least 5 distinct steps.
    2. Prep, Cook, Serve phases.
    3. Estimate numeric amounts for ingredients.
    """
    
    response = client.models.generate_content(
        model='gemini-flash-latest',
        contents=[file_ref, prompt],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=RecipeSchema
        )
    )
    
    if response.parsed:
        return RecipeObj(**response.parsed)
    return RecipeObj(**json.loads(response.text))

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
#