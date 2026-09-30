import os
from dotenv import load_dotenv
import io

# Load Environment Variables Forcefully BEFORE other imports might need them
load_dotenv()
print(f"--- CONFIG DEBUG: STORAGE_BACKEND={os.getenv('STORAGE_BACKEND')} ---")
print(f"--- CONFIG DEBUG: DB_BACKEND={os.getenv('DB_BACKEND', 'local')} ---")

import uuid
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, abort, session
from slugify import slugify
from flask_migrate import Migrate
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
import markdown
from database.db_connector import configure_database
from database.models import db, Ingredient, Recipe, Instruction, RecipeIngredient, RecipeMealType, RecipeDiet, User, Resource, resource_relations, Chef, UserRecipeInteraction, RecipeEvaluation, RecipeCollection, CollectionItem, UserQueue, UserLink, SocialMediaPost, TikTokSource, ConceptVisual, VisualStyleGuide
from utils.decorators import admin_required
from sqlalchemy import or_, func
from sqlalchemy.orm import joinedload
from sqlalchemy.orm.attributes import flag_modified
from services.pantry_service import get_slim_pantry_context
from ai_engine import generate_recipe_ai, get_pantry_id, get_top_pantry_suggestions, chefs_data, generate_recipe_from_web_text, analyze_ingredient_ai, extract_nutrients_from_text, load_controlled_vocabularies
from services.recipe_service import process_recipe_workflow, STATUS_SUCCESS, STATUS_MISSING
from services.photographer_service import generate_visual_prompt, generate_actual_image, generate_visual_prompt_from_image, load_photographer_config, generate_image_variation, process_external_image
from services.web_scraper_service import WebScraper
from services.storage_service import get_storage_provider, GoogleCloudStorageProvider
from utils.image_helpers import generate_ingredient_placeholder
from utils.ai_errors import friendly_ai_error
import base64
from io import BytesIO
from urllib.parse import urlencode
import shutil
import datetime
from sqlalchemy import func
from utils.prompt_manager import load_prompt
from routes._shared import get_recipe_image_url, get_image_url, load_json_option

import json


app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 20 * 1024 * 1024 # 20MB limit

# Register Blueprints
from routes.studio_routes import prompts_bp
app.register_blueprint(prompts_bp)

from routes.admin_collections_routes import collections_bp
app.register_blueprint(collections_bp)

from routes.admin_ingredients_routes import ingredients_bp
app.register_blueprint(ingredients_bp)

from routes.queue_routes import queue_bp
app.register_blueprint(queue_bp)

from routes.media_hub_routes import media_hub_bp
app.register_blueprint(media_hub_bp)

from routes.admin_tiktok_routes import tiktok_bp
app.register_blueprint(tiktok_bp)

from routes.admin_concept_routes import admin_concept_bp
app.register_blueprint(admin_concept_bp)

from routes.admin_style_center import admin_style_center_bp
app.register_blueprint(admin_style_center_bp)


from utils.markdown_extensions import VideoExtension

@app.template_filter('markdown')
def parse_markdown(text):
    if not text: return ""
    return markdown.markdown(text, extensions=['tables', VideoExtension()])

@app.template_filter('parse_chef_dna')
def parse_chef_dna(prompt):
    """Extracts sections from the system prompt for display."""
    sections = {}
    
    if not prompt: return sections
    
    # Normalize newlines
    prompt = str(prompt).replace('\\n', '\n')
    parts = prompt.split('\n')
    
    current_key = "General"
    sections[current_key] = []
    
    for line in parts:
        line = line.strip()
        if not line: continue
        
        lower_line = line.lower()
        if lower_line.startswith("role:"):
            current_key = "Role"
            sections[current_key] = [line[5:].strip()]
        elif lower_line.startswith("philosophy:"):
            current_key = "Philosophy"
            sections[current_key] = [line[11:].strip()]
        elif lower_line.startswith("tone:"):
            current_key = "Tone"
            sections[current_key] = [line[5:].strip()]
        elif lower_line.startswith("rules:"):
            current_key = "Rules"
            sections[current_key] = []
        elif current_key == "Rules" and (line[0].isdigit() or line.startswith('-')):
            sections["Rules"].append(line)
        else:
             # Append to current section
             if current_key in sections:
                sections[current_key].append(line)
             else:
                sections[current_key] = [line]
    return sections
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
if not app.config['SECRET_KEY']:
    if os.environ.get('K_SERVICE'):
        # Running on Cloud Run: never fall back to a guessable key
        raise RuntimeError("SECRET_KEY environment variable must be set in production")
    print("WARNING: SECRET_KEY not set, using a random key (sessions reset on restart)")
    app.config['SECRET_KEY'] = os.urandom(32).hex()
# Database Configuration (Local vs Cloud SQL)
configure_database(app)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize Flask-Migrate
migrate = Migrate(app, db)

@app.template_filter('get_protein_category')
def get_protein_category(protein_name):
    """Finds the Tier 1 category for a given protein name."""
    if not protein_name: return None
    from ai_engine import protein_data
    for category in protein_data:
        if protein_name in category['examples']:
            return category['category']
    return "Other"
@app.context_processor
def utility_processor():
    def update_query_params(**kwargs):
        args = request.args.copy()
        for key, value in kwargs.items():
            args[key] = value
        return url_for(request.endpoint, **args)
    
    return dict(update_query_params=update_query_params)

# Also imported from app by services/evaluation_service.py
app.add_template_global(get_recipe_image_url)
app.add_template_global(get_image_url)

db.init_app(app)

# Initialize Storage Provider
storage_provider = get_storage_provider(app.root_path)
print(f"--- STORAGE SYSTEM ACTIVE: {storage_provider.__class__.__name__} ---")
app.extensions['storage_provider'] = storage_provider

# Inject storage provider into blueprint context
# Note: Blueprints are registered earlier, but we can attach attributes to the object
prompts_bp.storage_provider = storage_provider
media_hub_bp.storage_provider = storage_provider

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# Routes moved out of app.py. FlatBlueprint keeps their original endpoint names.
from routes.auth_routes import auth_bp
app.register_blueprint(auth_bp)

from routes.mirror_routes import mirror_bp
app.register_blueprint(mirror_bp)

from routes.explore_routes import explore_bp
app.register_blueprint(explore_bp)

from routes.resources_routes import resources_bp
app.register_blueprint(resources_bp)

from routes.admin_chefs_routes import admin_chefs_bp
app.register_blueprint(admin_chefs_bp)

from routes.interactions_routes import interactions_bp
app.register_blueprint(interactions_bp)

from routes.admin_image_studio_routes import image_studio_bp
app.register_blueprint(image_studio_bp)

from routes.generate_routes import generate_bp
app.register_blueprint(generate_bp)

from routes.admin_recipes_routes import admin_recipes_bp
app.register_blueprint(admin_recipes_bp)

from routes.recipes_routes import recipes_bp
app.register_blueprint(recipes_bp)




@app.route('/ingredients')
def pantry_management():
    # Fetch all ingredients sorted by Category then Name
    ingredients = db.session.execute(db.select(Ingredient).order_by(Ingredient.main_category, Ingredient.name)).scalars().all()
    
    # Load constraints for dependent filtering
    data_dir = os.path.join(app.root_path, 'data', 'constraints')
    sub_categories_map = {}
    try:
        with open(os.path.join(data_dir, 'categories.json'), 'r') as f:
            data = json.load(f)
            sub_categories_map = data.get('sub_categories', {})
    except Exception as e:
        print(f"Error loading categories: {e}")

    return render_template('pantry_management.html', ingredients=ingredients, sub_categories_map=sub_categories_map)

@app.route('/api/ingredient/<int:id>/link-recipe', methods=['PATCH'])
@login_required
@admin_required
def link_recipe_to_ingredient(id: int):
    """Set (or clear) sub_recipe_id on an ingredient from the admin UI."""
    if not current_user.is_admin:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    ing = db.session.get(Ingredient, id)
    if not ing:
        return jsonify({'success': False, 'error': 'Ingredient not found'}), 404
    data = request.get_json()
    recipe_id = data.get('recipe_id')  # int or None
    if recipe_id:
        recipe = db.session.get(Recipe, recipe_id)
        if not recipe:
            return jsonify({'success': False, 'error': 'Recipe not found'}), 404
        ing.sub_recipe_id = recipe_id
        db.session.commit()
        return jsonify({'success': True, 'ingredient_name': ing.name, 'recipe_title': recipe.title})
    else:
        ing.sub_recipe_id = None
        db.session.commit()
        return jsonify({'success': True, 'ingredient_name': ing.name, 'recipe_title': None})


@app.route('/api/ingredient/<int:id>/toggle_basic', methods=['POST'])
@login_required
@admin_required
def toggle_basic_ingredient(id):
    ing = db.session.get(Ingredient, id)
    if not ing:
        return jsonify({'success': False, 'error': 'Ingredient not found'}), 404
    
    # Toggle
    ing.is_staple = not ing.is_staple
    db.session.commit()
    
    return jsonify({
        'success': True, 
        'new_status': ing.is_basic_ingredient,
        'id': ing.id,
        'name': ing.name
    })

# --- New Ingredient Workflow ---

@app.route('/new-ingredient', methods=['GET'])
@login_required
@admin_required
def new_ingredient_view():
    # Load categories for the dropdown in the template (manually or via API)
    # We can pass them to the template
    data_dir = os.path.join(app.root_path, 'data', 'constraints')
    with open(os.path.join(data_dir, 'categories.json'), 'r') as f:
        category_data = json.load(f)
        
    return render_template('new_ingredient.html', 
                         main_categories=category_data.get('main_categories', []),
                         sub_categories_map=category_data.get('sub_categories', {}))

@app.route('/api/search-ingredients', methods=['POST'])
def search_ingredients_api():
    try:
        data = request.get_json()
        query = data.get('query', '').strip()
        
        if not query or len(query) < 2:
            return jsonify({'success': True, 'results': []})
            
        # Search for name matches (ILIKE)
        results = db.session.execute(
            db.select(Ingredient)
            .where(Ingredient.name.ilike(f"%{query}%"))
            .order_by(Ingredient.name)
            .limit(10)
        ).scalars().all()
        
        # Serialize results
        items = []
        for i in results:
            img = None
            if i.image_url:
                if i.image_url.startswith('http'):
                    img = i.image_url
                else:
                    img = url_for('static', filename=i.image_url)
            items.append({
                'id': i.id,
                'name': i.name, 
                'category': i.main_category,
                'food_id': i.food_id,
                'image_url': img
            })
        
        return jsonify({'success': True, 'results': items})
        
    except Exception as e:
        print(f"Search API Error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/relink-ingredient', methods=['POST'])
@login_required
@admin_required
def relink_ingredient_api():
    """Swap the ingredient linked to a RecipeIngredient row. Admin only."""
    if not current_user.is_admin:
        return jsonify({'success': False, 'error': 'Admin access required'}), 403
    
    try:
        data = request.get_json()
        ri_id = data.get('recipe_ingredient_id')
        new_ing_id = data.get('new_ingredient_id')
        
        if not ri_id or not new_ing_id:
            return jsonify({'success': False, 'error': 'Missing parameters'}), 400
        
        # Fetch the RecipeIngredient row
        ri = db.session.get(RecipeIngredient, ri_id)
        if not ri:
            return jsonify({'success': False, 'error': 'Recipe ingredient link not found'}), 404
        
        # Verify the target ingredient exists
        new_ingredient = db.session.get(Ingredient, new_ing_id)
        if not new_ingredient:
            return jsonify({'success': False, 'error': 'Target ingredient not found'}), 404
        
        old_name = ri.ingredient.name
        ri.ingredient_id = new_ingredient.id
        db.session.commit()
        
        print(f"🔗 Relinked: '{old_name}' → '{new_ingredient.name}' (recipe_ingredient #{ri_id})")
        return jsonify({'success': True, 'old_name': old_name, 'new_name': new_ingredient.name})
        
    except Exception as e:
        db.session.rollback()
        print(f"Relink API Error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/suggest-substitutes', methods=['POST'])
@login_required
@admin_required
def suggest_substitutes_api():
    """Return top 3 pantry substitutes for a missing ingredient name."""
    try:
        data = request.get_json()
        name = data.get('name', '').strip()
        
        if not name:
            return jsonify({'success': True, 'suggestions': []})
        
        # Ensure pantry_map includes DB items (not just pantry.json)
        from ai_engine import set_pantry_memory
        slim_context = get_slim_pantry_context()
        set_pantry_memory(slim_context)
        
        
        # Get fuzzy suggestions (extra to account for filtered imports)
        suggestions = get_top_pantry_suggestions(name, top_n=6)
        
        # Enrich with DB data (image, full name casing, category)
        
        enriched = []
        for sug in suggestions:
            if len(enriched) >= 3:
                break
                
            ingredient = db.session.execute(
                db.select(Ingredient).where(Ingredient.food_id == sug['food_id'])
            ).scalars().first()
            
            if not ingredient:
                continue
            # Skip IMP-imported ingredients only (not all non-original)
            if (ingredient.main_category or '').lower() == 'imported':
                continue
            if ingredient.food_id.startswith('IMP-'):
                continue
            
            img = None
            if ingredient.image_url:
                if ingredient.image_url.startswith('http'):
                    img = ingredient.image_url
                else:
                    img = url_for('static', filename=ingredient.image_url)
            
            enriched.append({
                'id': ingredient.id,
                'name': ingredient.name,
                'food_id': ingredient.food_id,
                'category': ingredient.main_category or 'Uncategorized',
                'image_url': img,
                'score': sug['score']
            })
        
        return jsonify({'success': True, 'suggestions': enriched})
        
    except Exception as e:
        print(f"Suggest Substitutes API Error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/analyze-ingredient', methods=['POST'])
@login_required
@admin_required
def analyze_ingredient_api():
    try:
        data = request.get_json()
        prompt = data.get('prompt')
        
        if not prompt:
            return jsonify({'success': False, 'error': 'Prompt is required'})
            
        # Load validation constraints
        data_dir = os.path.join(app.root_path, 'data', 'constraints')
        with open(os.path.join(data_dir, 'categories.json'), 'r') as f:
            valid_categories = json.load(f)
            
        # Call AI Engine
        analysis = analyze_ingredient_ai(prompt, valid_categories)
        
        return jsonify({'success': True, 'data': analysis})
        
    except Exception as e:
        print(f"Analysis API Error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/extract-nutrients', methods=['POST'])
@login_required
@admin_required
def extract_nutrients_api():
    try:
        data = request.get_json()
        raw_text = data.get('raw_text', '').strip()
        ingredient_name = data.get('ingredient_name', '')

        if not raw_text:
            return jsonify({'success': False, 'error': 'No text provided'})

        # Call AI
        nutrients = extract_nutrients_from_text(raw_text, ingredient_name)
        
        return jsonify({'success': True, 'nutrients': nutrients})

    except Exception as e:
        print(f"Nutrient Extraction Error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/generate-ingredient-image', methods=['POST'])
@login_required
@admin_required
def generate_ingredient_image_api():
    try:
        data = request.get_json()
        prompt = data.get('prompt')
        if not prompt:
            return jsonify({'success': False, 'error': 'No prompt provided'})

        # Generate 4 Images
        images_list = generate_actual_image(prompt, number_of_images=4)
        
        results = []
        for img in images_list:
            filename = f"ing_temp_{uuid.uuid4().hex}.png"
            
            # Save to BytesIO
            img_io = io.BytesIO()
            img.save(img_io, format='PNG')
            img_io.seek(0)
            
            # Save via storage provider (Local or GCS)
            # This ensures 'temp' folder exists on the correct provider
            public_url = storage_provider.save(img_io.read(), filename, "temp")
            
            results.append({
                'url': public_url,
                'filename': filename
            })
        
        return jsonify({
            'success': True, 
            'images': results
        })
        
    except Exception as e:
        print(f"Image Gen Error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/ingredient/<int:id>', methods=['GET'])
def get_ingredient_details_api(id):
    try:
        ingredient = db.session.get(Ingredient, id)
        if not ingredient:
            return jsonify({'success': False, 'error': 'Ingredient not found'}), 404
            
        return jsonify({
            'success': True,
            'id': ingredient.id,
            'name': ingredient.name,
            'image_prompt': ingredient.image_prompt or "No prompt available.",
            'main_category': ingredient.main_category,
            'sub_category': ingredient.sub_category,
            'unit': ingredient.default_unit,
            'average_g_per_unit': ingredient.average_g_per_unit,
            'calories_per_100g': ingredient.calories_per_100g,
            'protein_per_100g': ingredient.protein_per_100g,
            'fat_per_100g': ingredient.fat_per_100g,
            'carbs_per_100g': ingredient.carbs_per_100g,
            'sugar_per_100g': ingredient.sugar_per_100g,
            'fiber_per_100g': ingredient.fiber_per_100g,
            'fat_saturated_per_100g': ingredient.fat_saturated_per_100g,
            'sodium_mg_per_100g': ingredient.sodium_mg_per_100g,
            'kj_per_100g': ingredient.kj_per_100g,
            # Sub-recipe link
            'sub_recipe_id': ingredient.sub_recipe_id,
            'sub_recipe_title': ingredient.sub_recipe.title if ingredient.sub_recipe else None,
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/ingredient/<int:id>', methods=['DELETE'])
@login_required
@admin_required
def delete_ingredient_api(id):
    try:
        ingredient = db.session.get(Ingredient, id)
        if not ingredient:
            return jsonify({'success': False, 'error': 'Ingredient not found'}), 404
            
        # Check usage in recipes
        if ingredient.recipe_ingredients:
            force = request.args.get('force') == 'true'
            if not force:
                recipes = [ri.recipe.title for ri in ingredient.recipe_ingredients]
                return jsonify({
                    'success': False, 
                    'requires_confirmation': True,
                    'message': f"Used in {len(recipes)} recipes: {', '.join(recipes)}. Delete anyway?",
                    'recipes': recipes
                }), 409

            # Explicitly delete associations if forcing
            for ri in ingredient.recipe_ingredients:
                db.session.delete(ri)
            
        db.session.delete(ingredient)
        db.session.commit()
        
        return jsonify({'success': True})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/update-ingredient-image', methods=['POST'])
@login_required
@admin_required
def update_ingredient_image_api():
    try:
        data = request.get_json()
        ing_id = data.get('id')
        temp_filename = data.get('temp_filename')
        image_prompt = data.get('image_prompt')
        
        if not ing_id or not temp_filename:
            return jsonify({'success': False, 'error': 'Missing ID or Image'}), 400
            
        ingredient = db.session.get(Ingredient, ing_id)
        if not ingredient:
            return jsonify({'success': False, 'error': 'Ingredient not found'}), 404

        # Create new unique name to bust cache
        new_filename = f"{ingredient.food_id}_{uuid.uuid4().hex[:8]}.png"
        
        # Use storage provider to move from temp to pantry
        # This works for both local and GCS storage
        try:
            new_url = storage_provider.move(temp_filename, "temp", new_filename, "pantry")
        except FileNotFoundError:
            return jsonify({'success': False, 'error': 'Temp image not found'}), 404
        
        # Update DB with the new image URL
        # For GCS, this will be the full public URL
        # For local, this will be /static/pantry/{filename}
        if new_url.startswith('http'):
            # GCS - store full URL
            ingredient.image_url = new_url
        else:
            # Local - store relative path
            ingredient.image_url = f"pantry/{new_filename}"
            
        if image_prompt:
            ingredient.image_prompt = image_prompt
            
        db.session.commit()
        
        return jsonify({
            'success': True,
            'new_image_url': new_url
        })

    except Exception as e:
        print(f"Update Image Error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/save-ingredient', methods=['POST'])
@login_required
@admin_required
def save_new_ingredient_api():
    try:
        data = request.get_json()
        
        # 1. Generate Unique ID
        all_ids = db.session.execute(db.select(Ingredient.food_id)).scalars().all()
        max_id = 0
        for fid in all_ids:
            if fid.isdigit():
                val = int(fid)
                if val > max_id:
                    max_id = val
        
        new_id_int = max_id + 1
        new_food_id = f"{new_id_int:06d}" 
        
        # 2. Handle Image
        image_url = None
        temp_filename = data.get('temp_image_filename')
        if temp_filename:
            # Move from temp to pantry
            src = os.path.join(app.root_path, 'static', 'temp', temp_filename)
            if os.path.exists(src):
                # We use the food_id for the filename: 000123.png
                new_filename = f"{new_food_id}.png"
                dst_dir = os.path.join(app.root_path, 'static', 'pantry')
                os.makedirs(dst_dir, exist_ok=True)
                
                dst = os.path.join(dst_dir, new_filename)
                shutil.move(src, dst) # Keep this line
                
                image_url = f"pantry/{new_filename}"

        new_ing = Ingredient(
            food_id=new_food_id,
            name=data.get('name'),
            main_category=data.get('main_category'),
            sub_category=data.get('sub_category'),
            default_unit=data.get('unit'),
            average_g_per_unit=data.get('average_g_per_unit'),

            # Nutrition
            calories_per_100g=data.get('calories_per_100g'),
            protein_per_100g=data.get('protein_per_100g'),
            fat_per_100g=data.get('fat_per_100g'),
            carbs_per_100g=data.get('carbs_per_100g'),
            sugar_per_100g=data.get('sugar_per_100g'),
            fiber_per_100g=data.get('fiber_per_100g'),
            sodium_mg_per_100g=data.get('sodium_mg_per_100g'),
            fat_saturated_per_100g=data.get('fat_saturated_per_100g'),

            # Metadata
            image_prompt=data.get('image_prompt'),
            image_url=image_url,
            created_at=datetime.datetime.now().isoformat(),

            # Sub-recipe link (Direction B)
            sub_recipe_id=data.get('sub_recipe_id') or None,
        )
        
        db.session.add(new_ing)
        db.session.commit()
        
        return jsonify({'success': True, 'id': new_ing.id})
        
    except Exception as e:
        db.session.rollback()
        print(f"Save Ingredient Error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/add-synonym', methods=['POST'])
@login_required
@admin_required
def add_synonym_api():
    try:
        data = request.get_json()
        name = data.get('name')
        food_id = data.get('food_id')
        
        if not name or not food_id:
            return jsonify({'success': False, 'error': 'Missing name or food_id'}), 400
            
        from ai_engine import add_synonym
        add_synonym(name, food_id)
        
        return jsonify({'success': True})
    except Exception as e:
        print(f"Synonym API Error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
        


@app.route('/api/quick-add-ingredient', methods=['POST'])
@login_required
@admin_required
def quick_add_ingredient_api():
    try:
        data = request.get_json()
        name = data.get('name')
        
        if not name:
            return jsonify({'success': False, 'error': 'Name is required'}), 400
            
        # 1. Load Categories via Constraints
        data_dir = os.path.join(app.root_path, 'data', 'constraints')
        with open(os.path.join(data_dir, 'categories.json'), 'r') as f:
            category_data = json.load(f)
            
        # 2. Analyze
        analysis = analyze_ingredient_ai(name, category_data)
        
        # 3. Generate Unique ID
        all_ids = db.session.execute(db.select(Ingredient.food_id)).scalars().all()
        max_id = 0
        for fid in all_ids:
             # Ensure we parse only numeric IDs
             if fid.isdigit():
                val = int(fid)
                if val > max_id:
                    max_id = val
        
        new_id_int = max_id + 1
        new_food_id = f"{new_id_int:06d}"
        
        # 4. Create Object (No Image for Quick Add - can regenerate later)
        new_ing = Ingredient(
            food_id=new_food_id,
            name=analysis.get('name', name), # Use analyzed name if available
            main_category=analysis.get('main_category'),
            sub_category=analysis.get('sub_category'),
            default_unit=analysis.get('unit'),
            average_g_per_unit=analysis.get('average_g_per_unit'),
            
            # Nutrition
            calories_per_100g=analysis.get('calories_per_100g'),
            protein_per_100g=analysis.get('protein_per_100g'),
            fat_per_100g=analysis.get('fat_per_100g'),
            carbs_per_100g=analysis.get('carbs_per_100g'),
            sugar_per_100g=analysis.get('sugar_per_100g'),
            fiber_per_100g=analysis.get('fiber_per_100g'),
            sodium_mg_per_100g=analysis.get('sodium_mg_per_100g'),
            fat_saturated_per_100g=analysis.get('fat_saturated_per_100g'),
            kj_per_100g=analysis.get('kj_per_100g'),
            
            # Metadata
            image_prompt=analysis.get('image_prompt'),
            created_at=datetime.datetime.now().isoformat()
        )
        
        db.session.add(new_ing)
        db.session.commit()
        
        # Update cache/map if needed?
        # Typically the app gets context from DB on request, 
        # but generate_recipe_ai uses a "slim_context" passed to it.
        # We assume the user RE-SUBMITS the generation request, which will fetch fresh context.
        
        return jsonify({
            'success': True, 
            'ingredient': {
                'id': new_ing.id,
                'name': new_ing.name
            }
        })

    except Exception as e:
        db.session.rollback()
        print(f"Quick Add Error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/update-ingredient-data', methods=['POST'])
@login_required
@admin_required
def update_ingredient_data_api():
    try:
        data = request.get_json()
        ing_id = data.get('id')
        
        if not ing_id:
             return jsonify({'success': False, 'error': 'ID is required'}), 400
             
        ingredient = db.session.get(Ingredient, ing_id)
        if not ingredient:
             return jsonify({'success': False, 'error': 'Ingredient not found'}), 404
             
        # Update Fields
        ingredient.name = data.get('name')
        ingredient.main_category = data.get('main_category')
        ingredient.sub_category = data.get('sub_category')
        ingredient.default_unit = data.get('unit')
        ingredient.average_g_per_unit = data.get('average_g_per_unit')
        
        ingredient.calories_per_100g = data.get('calories_per_100g')
        ingredient.kj_per_100g = data.get('kj_per_100g', 0)
        ingredient.protein_per_100g = data.get('protein_per_100g')
        ingredient.fat_per_100g = data.get('fat_per_100g')
        ingredient.carbs_per_100g = data.get('carbs_per_100g')
        ingredient.sugar_per_100g = data.get('sugar_per_100g')
        ingredient.fiber_per_100g = data.get('fiber_per_100g')
        ingredient.fat_saturated_per_100g = data.get('fat_saturated_per_100g')
        ingredient.sodium_mg_per_100g = data.get('sodium_mg_per_100g')
        
        if data.get('image_prompt'):
            ingredient.image_prompt = data.get('image_prompt')
            
        # Handle New Image if provided
        temp_filename = data.get('temp_image_filename')
        if temp_filename:
            src = os.path.join(app.root_path, 'static', 'temp', temp_filename)
            if os.path.exists(src):
                # Use existing food_id + random to bust cache
                new_filename = f"{ingredient.food_id}_{uuid.uuid4().hex[:6]}.png"
                dst_dir = os.path.join(app.root_path, 'static', 'pantry')
                os.makedirs(dst_dir, exist_ok=True)
                
                dst = os.path.join(dst_dir, new_filename)
                shutil.move(src, dst)
                
                ingredient.image_url = f"pantry/{new_filename}"
        
        # Sub-recipe link (Direction B)
        sub_recipe_id = data.get('sub_recipe_id')
        ingredient.sub_recipe_id = int(sub_recipe_id) if sub_recipe_id else None

        db.session.commit()
        return jsonify({'success': True})
        
    except Exception as e:
        db.session.rollback()
        print(f"Update Ing Data Error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500




@app.route('/api/admin/search-ingredients', methods=['GET'])
@login_required
def search_ingredients_admin_api():
    """Live-search endpoint for the recipe→ingredient link modal."""
    if not current_user.is_admin:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    q = request.args.get('q', '').strip()
    if len(q) < 2:
        return jsonify({'results': []})
    results = db.session.execute(
        db.select(Ingredient)
        .where(Ingredient.name.ilike(f'%{q}%'))
        .where(Ingredient.status != 'inactive')
        .order_by(Ingredient.name.asc())
        .limit(10)
    ).scalars().all()
    return jsonify({
        'results': [
            {
                'id': i.id,
                'name': i.name,
                'main_category': i.main_category or '',
                'sub_recipe_id': i.sub_recipe_id,
            }
            for i in results
        ]
    })



@app.route('/api/admin/set-pending-link/<int:ingredient_id>', methods=['GET'])
@login_required
def set_pending_link(ingredient_id: int):
    """Store ingredient_id in session so the next recipe save auto-links it."""
    if not current_user.is_admin:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    ing = db.session.get(Ingredient, ingredient_id)
    if not ing:
        return jsonify({'success': False, 'error': 'Ingredient not found'}), 404
    session['pending_link_ingredient_id'] = ingredient_id
    query_url = url_for('generate', query=ing.name)
    return jsonify({'success': True, 'redirect_url': query_url, 'ingredient_name': ing.name})


@app.route('/api/recipe/<int:recipe_id>/promote-to-ingredient', methods=['POST'])
@login_required
@admin_required
def promote_recipe_to_ingredient(recipe_id: int):
    """Direction A: take a recipe and link it to an existing matching ingredient
    (or create a minimal stub if none exists), then set ingredient.sub_recipe_id."""
    if not current_user.is_admin:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403

    recipe = db.session.get(Recipe, recipe_id)
    if not recipe:
        return jsonify({'success': False, 'error': 'Recipe not found'}), 404

    # Try to find an existing ingredient by exact name (case-insensitive)
    existing = db.session.execute(
        db.select(Ingredient)
        .where(db.func.lower(Ingredient.name) == recipe.title.lower())
        .limit(1)
    ).scalars().first()

    if existing:
        existing.sub_recipe_id = recipe_id
        db.session.commit()
        return jsonify({
            'success': True,
            'action': 'linked',
            'ingredient_id': existing.id,
            'ingredient_name': existing.name,
        })

    # No match — create a minimal stub with category = 'Prepared / Sauce'
    all_ids = db.session.execute(db.select(Ingredient.food_id)).scalars().all()
    max_id = max((int(fid) for fid in all_ids if fid.isdigit()), default=0)
    new_food_id = f"{max_id + 1:06d}"

    stub = Ingredient(
        food_id=new_food_id,
        name=recipe.title,
        main_category='Prepared',
        sub_category='sauce',
        default_unit='tbsp',
        image_url=get_recipe_image_url(recipe) if recipe.image_filename else None,
        sub_recipe_id=recipe_id,
        created_at=datetime.datetime.now().isoformat(),
        status='active',
    )
    db.session.add(stub)
    db.session.commit()
    return jsonify({
        'success': True,
        'action': 'created',
        'ingredient_id': stub.id,
        'ingredient_name': stub.name,
    })


@app.route('/api/merge-ingredients', methods=['POST'])
@login_required
@admin_required
def merge_ingredients_api():
    from services.ingredient_service import merge_ingredients
    try:
        data = request.get_json()
        source_id = data.get('source_id')  # the loser
        target_id = data.get('target_id')  # the winner
        
        if not source_id or not target_id:
            return jsonify({'success': False, 'error': 'Source and Target IDs required'}), 400

        result = merge_ingredients(winner_id=int(target_id), loser_id=int(source_id))
        
        if result['success']:
             return jsonify({'success': True, 'message': result['message']})
        else:
             return jsonify({'success': False, 'error': result['message']}), 400
             
    except Exception as e:
        db.session.rollback()
        print(f"Merge API Error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

def find_best_ingredient_match(name):
    """
    Tries to find the best existing ingredient for a given name.
    Uses the robust fuzzy matching from ai_engine.get_pantry_id,
    then resolves the food_id to a DB record.
    Returns an Ingredient ORM object or None.
    """
    from ai_engine import get_pantry_id
    
    food_id_str = get_pantry_id(name)
    if not food_id_str:
        return None
    
    return db.session.execute(
        db.select(Ingredient).where(Ingredient.food_id == food_id_str)
    ).scalars().first()






@app.route('/api/placeholder/ingredient/\u003cfood_id\u003e')
def ingredient_placeholder(food_id):
    """Generate a dynamic SVG placeholder for an ingredient without an image."""
    ingredient = db.session.execute(
        db.select(Ingredient).where(Ingredient.food_id == food_id)
    ).scalar_one_or_none()
    
    if ingredient:
        return generate_ingredient_placeholder(ingredient.name)
    else:
        return generate_ingredient_placeholder("Unknown")








if __name__ == '__main__':
    with app.app_context():
        db.create_all() # Ensure tables exist
    debug = os.environ.get('FLASK_DEBUG', '').lower() in ('1', 'true')
    app.run(host='0.0.0.0', debug=debug, port=8000)
