from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify, session
from flask_login import login_required
from utils.decorators import admin_required
from database.models import db, VisualStyleGuide, StyleSandboxRun, StyleSandboxPreset
import logging

logger = logging.getLogger(__name__)

admin_style_center_bp = Blueprint('admin_style_center', __name__, url_prefix='/admin/style-center')

@admin_style_center_bp.route('/', methods=['GET'])
@login_required
@admin_required
def dashboard():
    import time
    
    styles = db.session.execute(
        db.select(VisualStyleGuide).order_by(VisualStyleGuide.scope)
    ).scalars().all()
    
    sandbox_runs_raw = db.session.execute(
        db.select(StyleSandboxRun).order_by(StyleSandboxRun.timestamp.asc())
    ).scalars().all()
    
    sandbox_runs = {}
    for r in sandbox_runs_raw:
        # Key by tuple: (scope, test_item, preset_name)
        sandbox_runs[(r.scope, r.test_item, r.preset_name)] = r

    all_presets = db.session.execute(db.select(StyleSandboxPreset).order_by(StyleSandboxPreset.order_index, StyleSandboxPreset.id)).scalars().all()
    
    # Auto-seed initial datasets if completely empty (first time only)
    if not all_presets:
        seed_data = [
            # Ingredients
            ("ingredient", "Isometric 3D", "A minimalist 3D isometric icon of {name} on a pure solid white background, highly detailed, perfect lighting, clean modern app ui design style."),
            ("ingredient", "Photorealistic Flatlay", "A photorealistic flatlay top-down shot of {name} isolated on a bright pristine white background, 8k resolution, professional food photography, natural studio lighting."),
            ("ingredient", "Vector Icon", "A flat vector art illustration of {name}, solid white background, vibrant colors, minimal shading, clean lines, dribbble style icon."),
            ("ingredient", "Studio Macro", "A hyper-detailed macro studio photograph of {name}, extreme close-up showing texture, dramatic studio rim lighting, pure white background."),
            ("ingredient", "Watercolor", "A beautiful watercolor painting of {name}, soft brushstrokes, isolated on a clean white paper background, artistic, elegant culinary illustration."),
            
            # Recipes
            ("recipe", "Cookbook", "Top-down view of {name}, natural window light, minimalist table setting, food photography, 8k resolution"),
            ("recipe", "Macro", "Extreme detailed macro shot of {name}, beautiful bokeh, warm appetizing lighting, professional plating"),
            ("recipe", "Remix/Social", "Vibrant, high contrast, saturated TikTok style food photo of {name}, moody aesthetic, visually striking"),

            # Taxonomy
            ("taxonomy", "Deep-Fried", "A photorealistic conceptual representation of {name} culinary method, professional studio lighting"),
            ("taxonomy", "Mexican", "A beautiful symbolic aesthetic representing {name} cuisine, minimalist, rich colors"),
            ("taxonomy", "Pescetarian", "A clean visual icon for {name} diet, isolated on white, modern aesthetic"),
            ("taxonomy", "Seafood", "A high-end raw ingredient shot representing {name} protein, hyper-detailed, clean lighting"),
            ("taxonomy", "One-Pot", "A cozy, ambient top-down shot representing {name} meal type, rustic but modern presentation"),

            # App Icons
            ("app_icons", "Isometric 3D", "A minimal isometric 3D icon representing {name}, clean white background, vibrant colors, premium app icon style."),
            ("app_icons", "Vector Icon", "A flat vector UI icon representing {name}, clean and modern, highly legible, solid background.")
        ]
        for scope, name, prompt in seed_data:
            db.session.add(StyleSandboxPreset(scope=scope, name=name, prompt=prompt))
        db.session.commit()
        db.session.commit()
        all_presets = db.session.execute(db.select(StyleSandboxPreset).order_by(StyleSandboxPreset.order_index, StyleSandboxPreset.id)).scalars().all()
    # Group presets by scope
    presets_by_scope = {'ingredient': [], 'recipe': [], 'taxonomy': [], 'app_icons': []}
    for p in all_presets:
        if p.scope in presets_by_scope:
            presets_by_scope[p.scope].append(p)

    test_items_by_scope = {
        'ingredient': ["Banana", "Chicken Filet", "Canned Coconut Milk", "Salmon Steak", "Fresh Basil"],
        'recipe': ["Greek Chicken Gyros with Protein Tzatziki", "Loaded Baked Potato Soup with Crispy Skin Dippers", "Marry Me Chicken"],
        'taxonomy': ["cooking method: Deep-Fried", "Cuisine: Mexican", "Diet: Pescetarian", "Main Protein: Seafood", "Meal Type: One-Pot"],
        'app_icons': ["time", "diet", "portions", "calories"]
    }

    from services.visual_orchestrator_service import get_taxonomy_contexts
    return render_template('admin/style_center.html', 
                           styles=styles, 
                           sandbox_runs=sandbox_runs,
                           presets_by_scope=presets_by_scope,
                           test_items_by_scope=test_items_by_scope,
                           taxonomy_contexts=get_taxonomy_contexts())

@admin_style_center_bp.route('/preset', methods=['POST'])
@login_required
@admin_required
def add_preset():
    data = request.json
    scope = data.get('scope', '').strip()
    name = data.get('name', '').strip()
    prompt = data.get('prompt', '').strip()
    
    if not scope or not name or not prompt:
        return jsonify({'success': False, 'error': 'All fields are required'})
        
    try:
        existing = db.session.execute(
            db.select(StyleSandboxPreset).where(StyleSandboxPreset.scope == scope, StyleSandboxPreset.name == name)
        ).scalars().first()
        
        if existing:
            existing.prompt = prompt
            db.session.commit()
            return jsonify({'success': True, 'preset_id': existing.id})
            
        new_preset = StyleSandboxPreset(scope=scope, name=name, prompt=prompt)
        db.session.add(new_preset)
        db.session.commit()
        return jsonify({'success': True, 'preset_id': new_preset.id})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

@admin_style_center_bp.route('/preset/<int:preset_id>', methods=['DELETE'])
@login_required
@admin_required
def delete_preset(preset_id):
    try:
        preset = db.session.get(StyleSandboxPreset, preset_id)
        if preset:
            db.session.delete(preset)
            db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

@admin_style_center_bp.route('/reorder-presets', methods=['POST'])
@login_required
@admin_required
def reorder_presets():
    data = request.get_json() or {}
    order_data = data.get('order', [])
    
    if not order_data:
        return jsonify({'success': False, 'error': 'No order provided'}), 400
        
    try:
        for idx, preset_id in enumerate(order_data):
            preset = db.session.get(StyleSandboxPreset, preset_id)
            if preset:
                preset.order_index = idx
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error reordering presets: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_style_center_bp.route('/suggest-prompt', methods=['POST'])
@login_required
@admin_required
def suggest_prompt():
    data = request.get_json() or {}
    scope = data.get('scope', 'ingredient')
    preset_name = data.get('preset_name')

    if not preset_name:
         return jsonify({'success': False, 'error': 'Preset name required'})

    try:
        from google import genai
        import os
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
             return jsonify({'success': False, 'error': 'Missing GOOGLE_API_KEY'})
             
        client = genai.Client(api_key=api_key)
        
        base_prompt = f"Given the style preset name '{preset_name}' for a '{scope}' image generation task.\n" \
                      f"Generate a robust image generation prompt keyword snippet for an AI image generator.\n"
        
        if scope == 'taxonomy':
             base_prompt += "Taxonomy terms are abstract (e.g. 'Mexican' cuisine, 'Deep-Fried', 'Pescetarian' diet). Crucially, explicitly append instructions to NEVER render text, words, or labels in the image. The prompt YOU generate MUST include three dynamic placeholder variables: `{name}`, `{taxonomy_group}`, and `{context}`.\n" \
                            "The system will automatically inject those tags later (e.g. {name} = 'Deep-Fried', {taxonomy_group} = 'cooking method', {context} = 'Used as an action-oriented icon...').\n" \
                            "You must design the prompt so that it seamlessly integrates all three placeholders to formulate a highly contextual prompt. Do not hardcode generic taxonomy string types. Instead, literally write `{taxonomy_group}` and `{context}` in your generated prompt string.\n"
             
        base_prompt += f"You MUST include an exact literal '{{name}}' in the text where the target subject is injected. Example: 'a high quality cinematic food photograph representing {{name}}, 8k resolution, highly detailed, no text in image'\n" \
                       f"Output raw prompt string only without any quotes or markdown."
                 
        res = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=base_prompt,
        )
        return jsonify({'success': True, 'suggestion': res.text.strip()})
    except Exception as e:
        logger.error(f"Error suggesting prompt: {e}")
        return jsonify({'success': False, 'error': str(e)})

@admin_style_center_bp.route('/<int:style_id>', methods=['POST'])
@login_required
@admin_required
def update_style(style_id):
    """Updates a visual style guide wrapper."""
    try:
        style = db.session.get(VisualStyleGuide, style_id)
        if not style:
            flash("Style not found.", "error")
            return redirect(url_for('admin_style_center.dashboard'))

        style.base_wrapper = request.form.get('base_wrapper', '').strip()
        style.negative_prompt = request.form.get('negative_prompt', '').strip() or None
        style.remove_background = request.form.get('remove_background') == 'on'
        
        db.session.commit()
        flash(f"Successfully updated style for scope: {style.scope}", "success")
        
    except Exception as e:
        logger.error(f"Error updating visual style {style_id}: {e}")
        db.session.rollback()
        flash(f"Error updating visual style: {e}", "error")
        
    return redirect(url_for('admin_style_center.dashboard'))


@admin_style_center_bp.route('/test-render', methods=['POST'])
@login_required
@admin_required
def test_render():
    """Generates a test payload using an unsaved prompt for a sample ingredient."""
    data = request.get_json() or {}
    base_wrapper = data.get('base_wrapper')
    negative_prompt = data.get('negative_prompt')
    ingredient_name = data.get('ingredient_name')
    remove_background = data.get('remove_background', False)
    preset_name = data.get('preset_name', 'Custom')
    scope = data.get('scope', 'ingredient')

    if not base_wrapper or not ingredient_name:
        return jsonify({'success': False, 'error': 'Missing parameters'}), 400

    try:
        from services.vertex_image_service import VertexImageGenerator
        from services.storage_service import get_storage_provider
        from google.genai import types
        import time
        from PIL import Image
        from io import BytesIO

        generator = VertexImageGenerator(get_storage_provider())
        
        if not generator.client:
            return jsonify({'success': False, 'error': "Google API Key missing."}), 400

        clean_name = ingredient_name
        
        # Inject standard wrapper placeholders
        prompt = base_wrapper
        
        if scope == 'taxonomy':
            category = None
            if '::' in clean_name:
                parts = clean_name.split('::', 1)
                category = parts[0].strip().lower().replace('_', ' ')
                val = parts[-1].strip()
            elif ':' in clean_name:
                parts = clean_name.split(':', 1)
                category = parts[0].strip().lower().replace('_', ' ')
                val = parts[-1].strip()
            
            if category:
                from services.visual_orchestrator_service import get_taxonomy_contexts
                context = get_taxonomy_contexts().get(category, f"Used as a categorical icon in a food app to represent the {category} category.")
                
                # If they explicitly used {taxonomy_group} and {context} inside their prompt string:
                if '{taxonomy_group}' in prompt or '{context}' in prompt:
                    prompt = prompt.replace('{taxonomy_group}', category.title())
                    prompt = prompt.replace('{context}', context)
                    clean_name = val # Just inject the raw name for {name}
                else: 
                    # Backwards compatibility: cram it all into {name} if they didn't map the variables
                    clean_name = f"{val} (Taxonomy Group: {category.title()}. App Context: {context})"
        else:
            if '::' in clean_name:
                clean_name = clean_name.split('::')[-1].strip()
            elif ':' in clean_name:
                clean_name = clean_name.split(':')[-1].strip()

        prompt = prompt.replace('{name}', clean_name)
        
        if negative_prompt:
             prompt = f"{prompt} DO NOT INCLUDE: {negative_prompt}"

        import re
        safe_name = re.sub(r'[^a-zA-Z0-9]', '_', ingredient_name)
        filename = f"sandbox_{safe_name}_{int(time.time())}.png"

        config = types.GenerateImagesConfig(
            number_of_images=1,
            aspect_ratio='1:1'
        )

        response, model_used = generator._generate_with_fallback(prompt, config)

        if response.generated_images:
            raw_image_bytes = response.generated_images[0].image.image_bytes
            if remove_background:
                from rembg import remove
                output_image_bytes = remove(raw_image_bytes)
            else:
                output_image_bytes = raw_image_bytes
            
            img = Image.open(BytesIO(output_image_bytes))
            final_buffer = BytesIO()
            img.save(final_buffer, format="PNG")
            
            url = generator.storage.save(final_buffer.getvalue(), filename, "sandbox")
            
            # Save the run to database
            new_run = StyleSandboxRun(
                scope=scope,
                preset_name=preset_name,
                test_item=ingredient_name,
                image_url=url,
                prompt_used=prompt,
                model_used=model_used
            )
            db.session.add(new_run)
            db.session.commit()
            
            return jsonify({
                'success': True, 
                'image_url': url,
                'prompt_used': prompt,
                'model_used': model_used
            })
        else:
            return jsonify({'success': False, 'error': 'API returned nothing'}), 500

    except Exception as e:
        logger.error(f"Error test rendering: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_style_center_bp.route('/taxonomy-context', methods=['POST'])
@login_required
@admin_required
def update_taxonomy_context():
    data = request.get_json() or {}
    old_category = data.get('old_category')
    new_category = data.get('new_category')
    category = data.get('category') # Backward compatibility
    text = data.get('text')
    
    target_category = new_category or category
    
    if not target_category or text is None:
        return jsonify({'success': False, 'error': 'Missing taxonomy category or text'}), 400
        
    try:
        from services.visual_orchestrator_service import set_taxonomy_context
        set_taxonomy_context(target_category, text, old_category=old_category)
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error updating taxonomy context: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_style_center_bp.route('/recipe-cards-style', methods=['GET'])
@login_required
@admin_required
def recipe_cards_lab():
    from database.models import ConceptVisual, Recipe
    from flask import request
    
    # Fetch live app icons and taxonomy images
    concept_visuals = db.session.execute(
        db.select(ConceptVisual).filter(ConceptVisual.image_url.is_not(None))
    ).scalars().all()
    
    icons_map = {}
    for cv in concept_visuals:
        # Normalize key for easy JS/Jinja access
        key = f"{cv.concept_type.lower()}_{cv.concept_name.lower().replace(' ', '_')}"
        icons_map[key] = cv.image_url

    # Fetch recent recipes for the dropdown (up to 1000 for searchability)
    recent_recipes = db.session.execute(
        db.select(Recipe).order_by(Recipe.id.desc()).limit(1000)
    ).scalars().all()

    selected_recipe_id = request.args.get('recipe_id')
    selected_recipe = None
    
    if selected_recipe_id:
        selected_recipe = db.session.get(Recipe, selected_recipe_id)
        
    if selected_recipe:
        active_recipe = {
            'id': selected_recipe.id,
            'title': selected_recipe.title,
            'cuisine': selected_recipe.cuisine or 'Unknown',
            'time_estimate': selected_recipe.prep_time_mins or 0,
            'difficulty': selected_recipe.difficulty or 'Medium',
            'calories': int(selected_recipe.total_calories) if getattr(selected_recipe, 'total_calories', 0) else 0,
            'diet': selected_recipe.diets_list[0] if getattr(selected_recipe, 'diets_list', None) and len(selected_recipe.diets_list) > 0 else 'None',
            'portions': f"{selected_recipe.base_servings or 1}",
            'protein': f"{getattr(selected_recipe, 'protein_g', 32)}g",
            'image_filename': selected_recipe.image_filename,
            'image_url': selected_recipe.image_filename if selected_recipe.image_filename and selected_recipe.image_filename.startswith('http') else None
        }
    else:
        # Add a mock recipe for the lab
        active_recipe = {
            'id': 'mock',
            'title': 'Loaded Baked Potato Soup with Crispy Skin Dippers',
            'cuisine': 'American',
            'time_estimate': 45,
            'difficulty': 'Medium',
            'calories': 650,
            'diet': 'Vegetarian',
            'portions': '4',
            'protein': '18g',
            'image_url': 'https://images.unsplash.com/photo-1547592180-85f173990554?auto=format&fit=crop&q=80&w=1200' 
        }

    sample_recipes = [active_recipe]
    for r in recent_recipes[:4]:
        if r.id != (active_recipe.get('id') if isinstance(active_recipe.get('id'), int) else None):
            sample_recipes.append({
                'id': r.id,
                'title': r.title,
                'cuisine': r.cuisine or 'Unknown',
                'time_estimate': r.prep_time_mins or 0,
                'difficulty': r.difficulty or 'Medium',
                'calories': int(r.total_calories) if getattr(r, 'total_calories', 0) else 0,
                'diet': r.diets_list[0] if getattr(r, 'diets_list', None) and len(r.diets_list) > 0 else 'None',
                'portions': f"{r.base_servings or 1}",
                'protein': f"{getattr(r, 'protein_g', 24)}g",
                'image_url': r.image_filename if r.image_filename and r.image_filename.startswith('http') else 'https://images.unsplash.com/photo-1546069901-ba9599a7e63c'
            })

    active_template = session.get('active_card_template', 'original')
    return render_template(
        'admin/recipe_cards_lab.html', 
        icons_map=icons_map, 
        recipe=active_recipe,
        sample_recipes=sample_recipes,
        recent_recipes=recent_recipes,
        selected_recipe_id=selected_recipe_id,
        active_template=active_template
    )

@admin_style_center_bp.route('/recipe-cards-style/set-active', methods=['POST'])
@login_required
@admin_required
def set_active_recipe_cards_style():
    data = request.get_json()
    if data and 'template_id' in data:
        session['active_card_template'] = data['template_id']
        return jsonify({'success': True, 'template_id': data['template_id']})
    return jsonify({'success': False}), 400
