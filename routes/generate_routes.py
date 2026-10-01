"""Generate Blueprint: create recipes from a prompt, a web page, pasted text or a video."""
import json
import os

from flask import current_app, flash, jsonify, redirect, render_template, request, session, url_for
from flask_login import login_required

from ai_engine import chefs_data, generate_recipe_ai, generate_recipe_from_video, generate_recipe_from_web_text
from database.models import Ingredient, Recipe, db
from routes._flat import FlatBlueprint
from services.pantry_service import get_slim_pantry_context
from services.recipe_service import STATUS_MISSING, process_recipe_workflow
from services.social_media_service import SocialMediaExtractor
from services.web_scraper_service import WebScraper
from utils.ai_errors import friendly_ai_error
from utils.decorators import admin_required

generate_bp = FlatBlueprint("generate", __name__)


@generate_bp.route('/new-recipe', methods=['GET', 'POST'])
@login_required
@admin_required
def new_recipe():
    if request.method == 'POST':
        query = request.form.get('query')
        chef_id = request.form.get('chef_id', 'gourmet')
        if query:
            return redirect(url_for('generate', query=query, chef_id=chef_id))
    
    # Get recent recipes (approved only for public display)
    recent_recipes = db.session.execute(db.select(Recipe).where(Recipe.status == 'approved').order_by(Recipe.id.desc()).limit(10)).scalars().all()
    return render_template('index.html', recipes=recent_recipes, chefs=chefs_data)


# ---------------------------------------------------------------------------
# Helper: Handle the result dict from process_recipe_workflow
# ---------------------------------------------------------------------------
def _handle_workflow_result(result: dict, query_context: str, chef_id: str):
    """Shared response handler for all generation routes."""
    is_ajax = 'application/json' in request.headers.get('Accept', '')

    if result['status'] == STATUS_MISSING:
        if is_ajax:
            missing_names = [m['name'] for m in result.get('missing_ingredients', [])]
            return jsonify({
                'success': False, 
                'error': f"Missing ingredients: {', '.join(missing_names)}"
            })
            
        data_dir = os.path.join(current_app.root_path, 'data', 'constraints')
        with open(os.path.join(data_dir, 'categories.json'), 'r') as f:
            cat_data = json.load(f)
        return render_template(
            'missing_ingredients_resolution.html',
            missing_items=result['missing_ingredients'],
            query=query_context,
            chef_id=chef_id,
            main_categories=cat_data.get('main_categories', []),
            sub_categories_map=cat_data.get('sub_categories', {}),
        )
    # STATUS_SUCCESS
    recipe_id = result['recipe_id']

    # ── Pending sub-recipe link (from ingredient → generate flow) ──────────
    pending_ing_id = session.pop('pending_link_ingredient_id', None)
    if pending_ing_id:
        try:
            pending_ing = db.session.get(Ingredient, int(pending_ing_id))
            if pending_ing:
                pending_ing.sub_recipe_id = recipe_id
                db.session.commit()
                flash(f'Recipe automatically linked to ingredient "{pending_ing.name}".', 'success')
        except Exception:
            pass  # Non-fatal; user can link manually

    if is_ajax:
        return jsonify({'success': True, 'recipe_id': recipe_id})
    return redirect(url_for('recipe_detail', recipe_id=recipe_id))


@generate_bp.route('/generate/web', methods=['POST'])
@login_required
@admin_required
def generate_web_recipe():
    blog_url = request.form.get('blog_url')
    if not blog_url:
        return redirect(url_for('discover'))

    try:
        # 1. Scrape content
        scraper = WebScraper()
        scraped_data = scraper.scrape_url(blog_url)
        if not scraped_data or not scraped_data['text']:
            return "Could not extract text from this URL", 400

        # 2. Build clean pantry context (no IMP duplicates)
        slim_context = get_slim_pantry_context()
        clean_context = slim_context

        # 3. Call AI
        recipe_data = generate_recipe_from_web_text(
            scraped_data['text'],
            source_url=blog_url,
            slim_context=clean_context,
        )
        if not recipe_data:
            return "AI could not extract a valid recipe from the page.", 400

        # 4. Unified persistence pipeline
        result = process_recipe_workflow(recipe_data, query_context=blog_url, chef_id='gourmet')
        return _handle_workflow_result(result, query_context=blog_url, chef_id='gourmet')

    except Exception as e:
        db.session.rollback()
        print(f"Web Import Error: {e}")
        import traceback; traceback.print_exc()
        message = friendly_ai_error(e, fallback="Could not import a recipe from this URL. Please try again.")
        if 'application/json' in request.headers.get('Accept', ''):
            return jsonify({'success': False, 'error': message}), 500
        return message, 500

@generate_bp.route('/generate/text', methods=['POST'])
@login_required
@admin_required
def generate_from_text():
    """Generate a recipe from raw pasted text (free-form text dump)."""
    raw_text = request.form.get('raw_text', '').strip()
    if not raw_text:
        flash("Please paste some recipe text.", "error")
        return redirect(url_for('new_recipe'))

    try:
        # 1. Build clean pantry context (no IMP duplicates)
        slim_context = get_slim_pantry_context()
        clean_context = slim_context

        # 2. Call AI — reuse web-text extractor (handles noisy input)
        recipe_data = generate_recipe_from_web_text(
            raw_text,
            source_url="Manual Text Input",
            slim_context=clean_context,
        )
        if not recipe_data:
            flash("AI could not extract a valid recipe from the text.", "error")
            return redirect(url_for('new_recipe'))

        # 3. Unified persistence pipeline
        query_context = raw_text[:200]  # truncated for display on resolution page
        result = process_recipe_workflow(recipe_data, query_context=query_context, chef_id='gourmet')
        return _handle_workflow_result(result, query_context=query_context, chef_id='gourmet')

    except Exception as e:
        db.session.rollback()
        import traceback; traceback.print_exc()
        message = friendly_ai_error(e, fallback="Could not create a recipe from this text. Please try again.")
        if 'application/json' in request.headers.get('Accept', ''):
            return jsonify({'success': False, 'error': message}), 500
        flash(message, "error")
        return redirect(url_for('new_recipe'))


@generate_bp.route('/generate')
@login_required
@admin_required
def generate():
    query = request.args.get('query')
    chef_id = request.args.get('chef_id', 'gourmet')
    if not query:
        return redirect(url_for('discover'))

    try:
        # 1. Build clean pantry context (no IMP duplicates)
        pantry_context = get_slim_pantry_context()
        clean_context = pantry_context

        # 2. Call AI
        recipe_data = generate_recipe_ai(query, clean_context, chef_id=chef_id)

        # 3. Unified persistence pipeline
        result = process_recipe_workflow(recipe_data, query_context=query, chef_id=chef_id)
        return _handle_workflow_result(result, query_context=query, chef_id=chef_id)

    except ValueError as ve:
        print(f"Generation Validation Error: {ve}")
        flash(friendly_ai_error(ve, fallback=f"Validation Error: {str(ve)}"), "error")
        return redirect(url_for('discover'))
    except Exception as e:
        db.session.rollback()
        import traceback; traceback.print_exc()
        message = friendly_ai_error(e)
        if 'application/json' in request.headers.get('Accept', ''):
            return jsonify({'success': False, 'error': message}), 500
        flash(message, "error")
        return redirect(url_for('new_recipe'))


@generate_bp.route('/generate/video', methods=['POST'])
@login_required
@admin_required
def generate_from_video():
    video_url = request.form.get('video_url')
    if not video_url:
        flash("Please provide a video URL", "error")
        return redirect(url_for('discover'))

    try:
        # 1. Download video
        extract_result = SocialMediaExtractor.download_video(video_url)
        video_path = extract_result['video_path']
        caption = extract_result.get('caption', '')

        try:
            # 2. Build clean pantry context (no IMP duplicates)
            pantry_context = get_slim_pantry_context()
            clean_context = pantry_context

            # 3. Call AI (video analysis)
            recipe_data = generate_recipe_from_video(video_path, caption, clean_context)

            # 4. Unified persistence pipeline
            query_context = caption or f"Video Import: {video_url}"
            result = process_recipe_workflow(recipe_data, query_context=query_context, chef_id='gourmet')
            return _handle_workflow_result(result, query_context=query_context, chef_id='gourmet')

        finally:
            # Always cleanup the video file
            SocialMediaExtractor.cleanup(video_path)

    except Exception as e:
        db.session.rollback()
        import traceback; traceback.print_exc()
        message = friendly_ai_error(e, fallback="Could not create a recipe from this video. Please check the link and try again.")
        if 'application/json' in request.headers.get('Accept', ''):
            return jsonify({'success': False, 'error': message}), 500
        flash(message, "error")
        return redirect(url_for('discover'))
