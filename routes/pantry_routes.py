"""Pantry Blueprint: the ingredient library, new-ingredient workflow and ingredient APIs."""
import datetime
import io
import json
import os
import shutil
import uuid

from flask import current_app, jsonify, render_template, request, session, url_for
from flask_login import current_user, login_required

from ai_engine import analyze_ingredient_ai, extract_nutrients_from_text
from database.models import Ingredient, Recipe, db
from routes._flat import FlatBlueprint
from routes._shared import get_storage, viewer_is_admin
from services.photographer_service import generate_actual_image
from utils.decorators import admin_required
from utils.image_helpers import generate_ingredient_placeholder

pantry_bp = FlatBlueprint("pantry", __name__)


@pantry_bp.route('/ingredients')
def pantry_management():
    # Fetch all ingredients sorted by Category then Name
    query = db.select(Ingredient).order_by(Ingredient.main_category, Ingredient.name)
    if not viewer_is_admin():
        query = query.where(Ingredient.status == 'active')
    ingredients = db.session.execute(query).scalars().all()
    
    # Load constraints for dependent filtering
    data_dir = os.path.join(current_app.root_path, 'data', 'constraints')
    sub_categories_map = {}
    try:
        with open(os.path.join(data_dir, 'categories.json'), 'r') as f:
            data = json.load(f)
            sub_categories_map = data.get('sub_categories', {})
    except Exception as e:
        print(f"Error loading categories: {e}")

    return render_template('pantry_management.html', ingredients=ingredients, sub_categories_map=sub_categories_map)

@pantry_bp.route('/api/ingredient/<int:id>/link-recipe', methods=['PATCH'])
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


@pantry_bp.route('/api/ingredient/<int:id>/toggle_basic', methods=['POST'])
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

@pantry_bp.route('/new-ingredient', methods=['GET'])
@login_required
@admin_required
def new_ingredient_view():
    # Load categories for the dropdown in the template (manually or via API)
    # We can pass them to the template
    data_dir = os.path.join(current_app.root_path, 'data', 'constraints')
    with open(os.path.join(data_dir, 'categories.json'), 'r') as f:
        category_data = json.load(f)
        
    return render_template('new_ingredient.html', 
                         main_categories=category_data.get('main_categories', []),
                         sub_categories_map=category_data.get('sub_categories', {}))

@pantry_bp.route('/api/search-ingredients', methods=['POST'])
def search_ingredients_api():
    try:
        data = request.get_json()
        query = data.get('query', '').strip()
        
        if not query or len(query) < 2:
            return jsonify({'success': True, 'results': []})
            
        # Search for name matches (ILIKE)
        search = db.select(Ingredient).where(Ingredient.name.ilike(f"%{query}%"))
        if not viewer_is_admin():
            search = search.where(Ingredient.status == 'active')
        results = db.session.execute(search.order_by(Ingredient.name).limit(10)).scalars().all()
        
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

@pantry_bp.route('/api/analyze-ingredient', methods=['POST'])
@login_required
@admin_required
def analyze_ingredient_api():
    try:
        data = request.get_json()
        prompt = data.get('prompt')
        
        if not prompt:
            return jsonify({'success': False, 'error': 'Prompt is required'})
            
        # Load validation constraints
        data_dir = os.path.join(current_app.root_path, 'data', 'constraints')
        with open(os.path.join(data_dir, 'categories.json'), 'r') as f:
            valid_categories = json.load(f)
            
        # Call AI Engine
        analysis = analyze_ingredient_ai(prompt, valid_categories)
        
        return jsonify({'success': True, 'data': analysis})
        
    except Exception as e:
        print(f"Analysis API Error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@pantry_bp.route('/api/extract-nutrients', methods=['POST'])
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

@pantry_bp.route('/api/generate-ingredient-image', methods=['POST'])
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
            public_url = get_storage().save(img_io.read(), filename, "temp")
            
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

@pantry_bp.route('/api/ingredient/<int:id>', methods=['GET'])
def get_ingredient_details_api(id):
    try:
        ingredient = db.session.get(Ingredient, id)
        if not ingredient or (ingredient.status != 'active' and not viewer_is_admin()):
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

@pantry_bp.route('/api/ingredient/<int:id>', methods=['DELETE'])
@login_required
@admin_required
def delete_ingredient_api(id):
    """Delete an ingredient no recipe uses. One that recipe lines use is merged into another instead (the lines move
    with it); deleting it would leave them without their pantry row."""
    try:
        ingredient = db.session.get(Ingredient, id)
        if not ingredient:
            return jsonify({'success': False, 'error': 'Ingredient not found'}), 404
        used = sorted({line.recipe.title for line in ingredient.recipe_lines})
        if used:
            return jsonify({'success': False, 'recipes': used,
                            'error': f"Used in {len(used)} recipes: {', '.join(used)}. Merge it into another ingredient instead."}), 409
        db.session.delete(ingredient)
        db.session.commit()
        return jsonify({'success': True})
    except Exception:
        db.session.rollback()
        current_app.logger.exception('Deleting ingredient %s failed', id)
        return jsonify({'success': False, 'error': 'Could not delete the ingredient.'}), 500


@pantry_bp.route('/api/update-ingredient-image', methods=['POST'])
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
            new_url = get_storage().move(temp_filename, "temp", new_filename, "pantry")
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

@pantry_bp.route('/api/save-ingredient', methods=['POST'])
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
            src = os.path.join(current_app.root_path, 'static', 'temp', temp_filename)
            if os.path.exists(src):
                # We use the food_id for the filename: 000123.png
                new_filename = f"{new_food_id}.png"
                dst_dir = os.path.join(current_app.root_path, 'static', 'pantry')
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

@pantry_bp.route('/api/add-synonym', methods=['POST'])
@login_required
@admin_required
def add_synonym_api():
    try:
        data = request.get_json()
        name = data.get('name')
        food_id = data.get('food_id')
        
        if not name or not food_id:
            return jsonify({'success': False, 'error': 'Missing name or food_id'}), 400
            
        ingredient = db.session.execute(
            db.select(Ingredient).where(Ingredient.food_id == food_id)
        ).scalars().first()
        if not ingredient:
            return jsonify({'success': False, 'error': 'Ingredient not found'}), 404

        from services.ingredient_service import add_alias
        added = add_alias(ingredient, name)
        db.session.commit()
        return jsonify({'success': True, 'added': added})
    except Exception as e:
        print(f"Synonym API Error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
        


@pantry_bp.route('/api/update-ingredient-data', methods=['POST'])
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
            src = os.path.join(current_app.root_path, 'static', 'temp', temp_filename)
            if os.path.exists(src):
                # Use existing food_id + random to bust cache
                new_filename = f"{ingredient.food_id}_{uuid.uuid4().hex[:6]}.png"
                dst_dir = os.path.join(current_app.root_path, 'static', 'pantry')
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




@pantry_bp.route('/api/admin/search-ingredients', methods=['GET'])
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



@pantry_bp.route('/api/admin/set-pending-link/<int:ingredient_id>', methods=['GET'])
@login_required
def set_pending_link(ingredient_id: int):
    """Store ingredient_id in session so the next recipe save auto-links it."""
    if not current_user.is_admin:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    ing = db.session.get(Ingredient, ingredient_id)
    if not ing:
        return jsonify({'success': False, 'error': 'Ingredient not found'}), 404
    session['pending_link_ingredient_id'] = ingredient_id  # routes/recipe_v2_routes.py start() links the recipe made next
    return jsonify({'success': True, 'redirect_url': url_for('recipe_v2.new_recipe', source=ing.name), 'ingredient_name': ing.name})


@pantry_bp.route('/api/merge-ingredients', methods=['POST'])
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


@pantry_bp.route('/api/placeholder/ingredient/\u003cfood_id\u003e')
def ingredient_placeholder(food_id):
    """Generate a dynamic SVG placeholder for an ingredient without an image."""
    ingredient = db.session.execute(
        db.select(Ingredient).where(Ingredient.food_id == food_id)
    ).scalar_one_or_none()
    
    if ingredient:
        return generate_ingredient_placeholder(ingredient.name)
    else:
        return generate_ingredient_placeholder("Unknown")
