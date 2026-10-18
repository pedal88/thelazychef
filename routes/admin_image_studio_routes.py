"""Admin Image Studio Blueprint: the photographer studio and recipe image generation."""
import uuid
from io import BytesIO

from flask import flash, jsonify, redirect, render_template, request, url_for
from flask_login import login_required

from database.models import Recipe, db
from routes._flat import FlatBlueprint
from routes._shared import get_storage
from services.photographer_service import (
    generate_actual_image,
    generate_image_variation,
    generate_visual_prompt,
    generate_visual_prompt_from_image,
    load_photographer_config,
)
from utils.decorators import admin_required
from utils.prompt_manager import load_prompt

image_studio_bp = FlatBlueprint("image_studio", __name__)


@image_studio_bp.route('/admin/studio', methods=['GET', 'POST'])
@login_required
@admin_required
def studio_view():
    prompt = None
    recipe_text = ""
    recipe_id = None
    ingredients_list = ""
    
    config = load_photographer_config()
    
    # Check if we were sent here from a recipe page
    if request.args.get('recipe_text'):
        recipe_text = request.args.get('recipe_text')
    
    if request.args.get('recipe_id'):
        recipe_id = request.args.get('recipe_id')

    if request.args.get('ingredients_list'):
        ingredients_list = request.args.get('ingredients_list')
    
    if request.method == 'POST':
        recipe_text = request.form.get('recipe_text')
        recipe_id = request.form.get('recipe_id')
        ingredients_list = request.form.get('ingredients_list')
        
        # Check for Image Upload (Option 1B)
        if 'reference_image' in request.files and request.files['reference_image'].filename != '':
            file = request.files['reference_image']
            image_bytes = file.read()
            prompt = generate_visual_prompt_from_image(image_bytes)
            
        # Fallback to Text (Option 1A)
        elif recipe_text:
            prompt = generate_visual_prompt(recipe_text, ingredients_list)
            
            
    return render_template('studio.html', 
                         config=config, 
                         prompt=prompt, 
                         recipe_text=recipe_text,
                         recipe_id=recipe_id,
                         ingredients_list=ingredients_list)

@image_studio_bp.route('/admin/studio/snap', methods=['POST'])
@login_required
@admin_required
def studio_snap():
    prompt = request.form.get('visual_prompt')
    recipe_text = request.form.get('recipe_text') # Retrieve context
    recipe_id = request.form.get('recipe_id')
    ingredients_list = request.form.get('ingredients_list')
    config = load_photographer_config()

    if not prompt:
        return redirect(url_for('studio_view'))
        
    try:
        # Generate the Image
        img = generate_actual_image(prompt)
        
        # Save to Temp via Storage Provider
        filename = f"temp_{uuid.uuid4().hex}.png"
        
        # Convert PIL to Bytes
        img_byte_arr = BytesIO()
        img.save(img_byte_arr, format='PNG')
        img_bytes = img_byte_arr.getvalue()
        
        public_url = get_storage().save(img_bytes, filename, "temp")
        
        # Render template with the image filename/URL AND context
        # Note: 'temp_image' variable now expects just the filename for some logic 
        # OR the URL? The template uses `url_for('static', filename='temp/'+temp_image)` usually.
        # If we return a URL from GCS, we can't wrap it in `url_for('static')`.
        # We need to pass the FULL URL.
        # But let's check studio.html usage later. unique filename is safer for now if local.
        # If local, storage.save returns "/static/temp/filename.png"
        # If GCS, it returns "https://..."
        
        # Let's pass the full URL to the template as 'temp_image_url' and update template?
        # OR keep 'temp_image' as filename, and 'temp_image_full_url' as the public url.
        
        return render_template('studio.html', 
                             config=config, 
                             prompt=prompt, 
                             recipe_text=recipe_text,
                             recipe_id=recipe_id,
                             ingredients_list=ingredients_list,
                             temp_image=filename,
                             temp_image_url=public_url) # New variable
                             
    except Exception as e:
        flash(f"Error generating image: {str(e)}", "error")
        # Log the full error
        print(f"Error generating image: {e}")
        return render_template('studio.html', 
                             config=config, 
                             prompt=prompt, 
                             recipe_text=recipe_text,
                             recipe_id=recipe_id,
                             ingredients_list=ingredients_list)

@image_studio_bp.route('/admin/studio/save', methods=['POST'])
@login_required
@admin_required
def save_recipe_image():
    filename = request.form.get('filename')
    recipe_id = request.form.get('recipe_id')
    
    if not filename or not recipe_id:
        flash("Missing data to save image", "error")
        return redirect(url_for('discover'))
        
    try:
        # Move file from temp to recipes
        # Use simple storage abstraction
        new_filename = f"recipe_{recipe_id}_{uuid.uuid4().hex[:8]}.png"
        
        # Move: Temp -> Recipes
        get_storage().move(filename, "temp", new_filename, "recipes")
        
        # Update DB
        recipe = db.session.get(Recipe, int(recipe_id))
        if recipe:
            recipe.image_filename = new_filename
            db.session.commit()
            flash("Image saved to recipe!", "success")
            return redirect(url_for('recipe_detail', recipe_id=recipe_id))
        else:
             flash("Recipe not found", "error")
             return redirect(url_for('discover'))

    except Exception as e:
        print(f"DEBUG SAVE ERROR: {e}")
        flash(f"Error saving image: {str(e)}", "error")
        return redirect(url_for('discover')) 


@image_studio_bp.route('/admin/studio/analyze', methods=['POST'])
@login_required
@admin_required
def studio_analyze():
    try:
        # A1: Text Input -> Generate Prompt
        text_a1 = request.form.get('text_a1', '')
        prompt_b1 = ""
        if text_a1:
            prompt_b1 = generate_visual_prompt(text_a1)
        
        # A2: Image Input (for Image-to-Prompt)
        prompt_a2 = ""
        if 'image_a2' in request.files and request.files['image_a2'].filename != '':
            file = request.files['image_a2']
            image_bytes = file.read()
            prompt_a2 = generate_visual_prompt_from_image(image_bytes)
            
        # A3: Image Input (for Remix) - We just confirm it's valid/received, 
        # but the prompt is fixed.
        # Maybe we could do a quick check? 
        
        # Get Fixed Prompt from Config
        config = load_photographer_config()
        # Create a specific "Enhancer" prompt or just use the system prompt
        # User requested: "Cookbook Style" with Template
        prompt_b3 = load_prompt('recipe_image/style_remix.jinja2', ingredient_name='[Ingredient Name]')

        return jsonify({
            'success': True,
            'row1': prompt_b1, 
            'row2': prompt_a2,
            'row3': prompt_b3
        })

    except Exception as e:
        print(f"Analyze Error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@image_studio_bp.route('/admin/studio/generate', methods=['POST'])
@login_required
@admin_required
def studio_generate():
    try:
        # B1: Text-to-Image
        prompt_b1 = request.form.get('prompt_b1')
        img_c1_url = None
        if prompt_b1:
            img = generate_actual_image(prompt_b1)[0]
            filename = f"studio_a_{uuid.uuid4().hex}.png"
            
            # Save via Storage
            img_byte_arr = BytesIO()
            img.save(img_byte_arr, format='PNG')
            img_c1_url = get_storage().save(img_byte_arr.getvalue(), filename, "temp")

        # B2: Image-to-Prompt-to-Image
        prompt_b2 = request.form.get('prompt_b2')
        img_c2_url = None
        if prompt_b2:
            img = generate_actual_image(prompt_b2)[0]
            filename = f"studio_b_{uuid.uuid4().hex}.png"
            
            # Save via Storage
            img_byte_arr = BytesIO()
            img.save(img_byte_arr, format='PNG')
            img_c2_url = get_storage().save(img_byte_arr.getvalue(), filename, "temp")
            
        # B3: Mix (Image + Fixed Prompt)
        prompt_b3 = request.form.get('prompt_b3')
        img_c3_url = None
        
        # We need the image from A3 again. 
        # NOTE: Ideally we would have saved it to a temp path in /analyze and passed the path.
        # But for this stateless implementation, we expect the frontend to re-send the file 
        # OR we rely on the file being present in request.files if the user selected it.
        if 'image_a3' in request.files and request.files['image_a3'].filename != '' and prompt_b3:
            file = request.files['image_a3']
            image_bytes = file.read()
            # Variation Generation
            img = generate_image_variation(image_bytes, prompt_b3)[0]
            filename = f"studio_c_{uuid.uuid4().hex}.png"
            
            # Save via Storage
            img_byte_arr = BytesIO()
            img.save(img_byte_arr, format='PNG')
            img_c3_url = get_storage().save(img_byte_arr.getvalue(), filename, "temp")

        return jsonify({
            'success': True,
            'image_c1': img_c1_url,
            'image_c2': img_c2_url,
            'image_c3': img_c3_url
        })

    except Exception as e:
        print(f"Generate Error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# RECIPE IMAGE GENERATION FLOW
@image_studio_bp.route('/recipe-image-generation')
@login_required
@admin_required
def recipe_image_generation_view():
    recipe_id = request.args.get('recipe_id')
    if not recipe_id:
        flash("Recipe ID required", "error")
        return redirect(url_for('discover'))
    
    recipe = db.session.get(Recipe, int(recipe_id))
    if not recipe:
        flash("Recipe not found", "error")
        return redirect(url_for('discover'))
        
    return render_template('recipe_photographer.html', recipe=recipe)

@image_studio_bp.route('/recipe-image-generation/prompt', methods=['POST'])
@login_required
@admin_required
def recipe_image_generation_prompt():
    try:
        data = request.get_json()
        recipe_id = data.get('recipe_id')
        recipe = db.session.get(Recipe, int(recipe_id))
        
        if not recipe:
            return jsonify({'success': False, 'error': 'Recipe not found'})
            
        # Reconstruct Context for AI
        ingredients_list = ", ".join([ri.ingredient.name for ri in recipe.ingredients])
        
        recipe_text = f"Title: {recipe.title}\n"
        recipe_text += f"Cuisine: {recipe.cuisine}\n"
        recipe_text += f"Diets: {', '.join(recipe.diets_list)}\n"
        
        # Generate Prompt
        prompt = generate_visual_prompt(recipe_text, ingredients_list)
        
        return jsonify({'success': True, 'prompt': prompt})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@image_studio_bp.route('/recipe-image-generation/generate', methods=['POST'])
@login_required
@admin_required
def recipe_image_generation_create():
    try:
        data = request.get_json()
        prompt = data.get('prompt')
        
        if not prompt:
            return jsonify({'success': False, 'error': 'Prompt required'})
            
        # Generate Image
        try:
            # Check if using Vertex or Photographer Service
            # For now, assuming generate_actual_image returns a list of PIL images
            images = generate_actual_image(prompt)
            if not images:
                 return jsonify({'success': False, 'error': 'No image generated'})
            img = images[0]
        except Exception as e:
             print(f"Error calling AI generation: {e}")
             return jsonify({'success': False, 'error': f"Generation failed: {str(e)}"})
             
        # Save to Temp
        filename = f"temp_{uuid.uuid4().hex}.png"
        
        # Save via Storage
        img_byte_arr = BytesIO()
        img.save(img_byte_arr, format='PNG')
        file_url = get_storage().save(img_byte_arr.getvalue(), filename, "temp")
        
        return jsonify({'success': True, 'filename': filename, 'url': file_url})
        
    except Exception as e:
        print(f"Gen Error: {e}")
        return jsonify({'success': False, 'error': str(e)})

@image_studio_bp.route('/recipe-image-generation/save', methods=['POST'])
@login_required
@admin_required
def recipe_image_generation_save():
    try:
        data = request.get_json()
        filename = data.get('filename')
        recipe_id = data.get('recipe_id')
        
        if not filename or not recipe_id:
            return jsonify({'success': False, 'error': 'Missing data'})
            
        # Move file using Storage Provider (Abstracts Local vs Cloud)
        new_filename = f"recipe_{recipe_id}_{uuid.uuid4().hex[:8]}.png"
        
        try:
            # Move from 'temp' to 'recipes'
            get_storage().move(filename, "temp", new_filename, "recipes")
            
            # Update DB
            recipe = db.session.get(Recipe, int(recipe_id))
            recipe.image_filename = new_filename
            db.session.commit()
            
            return jsonify({'success': True})
            
        except FileNotFoundError:
             return jsonify({'success': False, 'error': 'Temp file not found or expired'})
            
    except Exception as e:
        print(f"Save Logic Error: {e}")
        return jsonify({'success': False, 'error': str(e)})
