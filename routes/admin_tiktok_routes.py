from flask import Blueprint, jsonify, render_template, request, current_app
from flask_login import login_required
from utils.decorators import admin_required
from database.models import db, TikTokSource, Recipe
from services.tiktok_ingestion_service import TikTokIngestionService
from services.recipe_service import create_recipe_from_extracted_json

tiktok_bp = Blueprint('tiktok_sidecar', __name__, url_prefix='/admin/tiktok-sidecar')

@tiktok_bp.route('/', methods=['GET'])
@login_required
@admin_required
def sidecar_dashboard():
    """Render the main TikTok Sidecar dashboard with all ingested sources."""
    # List sources. Exclude things that are fully imported (unless we want to show a history).
    # Since they are for bulk processing, newest first.
    sources = db.session.execute(
        db.select(TikTokSource).order_by(TikTokSource.created_at.desc())
    ).scalars().all()
    
    # Pre-fetch recipe ID mappings securely to avoid N+1 queries in the template
    urls = [s.tiktok_url for s in sources]
    recipe_matches = db.session.execute(
        db.select(Recipe.source_input, Recipe.id).where(Recipe.source_input.in_(urls))
    ).all()
    
    recipe_map = {row.source_input: row.id for row in recipe_matches}
    
    return render_template('admin/tiktok_sidecar.html', sources=sources, recipe_map=recipe_map)

@tiktok_bp.route('/api/ingest', methods=['POST'])
@login_required
@admin_required
def ingest_url():
    """Ingests a TikTok URL asynchronously."""
    data = request.get_json()
    url = data.get('url')
    if not url:
        return jsonify({"success": False, "error": "URL is required"}), 400
        
    result = TikTokIngestionService.classify_and_extract(url)
    
    if result.get("status") in ["success", "skipped"]:
         return jsonify({"success": True, "data": result})
    else:
         return jsonify({"success": False, "error": result.get("reason", "Unknown error")}), 400

@tiktok_bp.route('/api/pre-flight', methods=['POST'])
@login_required
@admin_required
def pre_flight_check():
    """Checks an array of URLs for duplicates before processing."""
    data = request.get_json()
    urls = data.get('urls', [])
    if not urls:
        return jsonify({"success": False, "error": "No URLs provided"}), 400
        
    valid_urls = []
    rejected = []
    
    # Deduplicate the raw input list first
    unique_urls = list(set(urls))
    
    for url in unique_urls:
        existing_source = db.session.execute(
            db.select(TikTokSource).where(TikTokSource.tiktok_url == url)
        ).scalar_one_or_none()
        
        if existing_source:
            if existing_source.status == "IMPORTED":
                rejected.append({"url": url, "reason": "Already imported to Live App"})
            else:
                rejected.append({"url": url, "reason": "Already in Sidecar Queue"})
            continue
            
        existing_recipe = db.session.execute(
            db.select(Recipe).where(Recipe.source_input == url)
        ).scalar_one_or_none()
        
        if existing_recipe:
            rejected.append({"url": url, "reason": "Already exists as Recipe ID " + str(existing_recipe.id)})
            continue
            
        valid_urls.append(url)
        
    return jsonify({
        "success": True,
        "valid_urls": valid_urls,
        "rejected": rejected
    })

@tiktok_bp.route('/api/upload', methods=['POST'])
@login_required
@admin_required
def upload_file():
    """Handles parsing of a TikTok Like List.txt file to extract URLs."""
    if 'file' not in request.files:
        return jsonify({"success": False, "error": "No file part"}), 400
        
    file = request.files['file']
    if file.filename == '':
        return jsonify({"success": False, "error": "No selected file"}), 400
        
    if file:
        try:
            content = file.read().decode('utf-8')
            urls = TikTokIngestionService.parse_tiktok_file(content)
            return jsonify({"success": True, "urls": urls})
        except Exception as e:
            import traceback; traceback.print_exc()
            return jsonify({"success": False, "error": f"Failed to parse file: {str(e)}"}), 500


@tiktok_bp.route('/api/import/<int:source_id>', methods=['POST'])
@login_required
@admin_required
def import_to_recipe(source_id):
    """Takes a curated TikTokSource 'Cheat Sheet' and feeds it into the Recipe generator Pipeline."""
    source = db.session.get(TikTokSource, source_id)
    if not source:
        return jsonify({"success": False, "error": "Source not found"}), 404
        
    if source.entity_type != "RECIPE":
         return jsonify({"success": False, "error": f"Cannot import entity type '{source.entity_type}' as a Recipe."}), 400
         
    if source.status == "IMPORTED":
         # Look it up
         existing = db.session.execute(db.select(Recipe).where(Recipe.source_input == source.tiktok_url)).scalar_one_or_none()
         if existing:
              return jsonify({"success": True, "recipe_id": existing.id, "message": "Already imported"})

    try:
        # Deep Extraction!
        from services.social_media_service import SocialMediaExtractor
        from ai_engine import generate_recipe_from_video
        from services.recipe_service import process_recipe_workflow
        from services.pantry_service import get_slim_pantry_context
        
        extract_result = SocialMediaExtractor.download_video(source.tiktok_url)
        video_path = extract_result['video_path']
        caption = extract_result.get('caption', getattr(source, 'raw_caption', ''))
        
        try:
            pantry_context = get_slim_pantry_context()
            clean_context = pantry_context

            # Generate via video pipeline
            recipe_data = generate_recipe_from_video(video_path, caption, clean_context)
            
            # Use raw URL to trigger frontend link display instead of caption dump
            result = process_recipe_workflow(
                recipe_data, 
                query_context=source.tiktok_url, 
                chef_id='gourmet',
                source_thumbnail_path=extract_result.get('thumbnail_path')
            )
            
            if result.get('status') == 'SUCCESS':
                 source.status = "IMPORTED"
                 db.session.commit()
                 return jsonify({"success": True, "recipe_id": result['recipe_id']})
                 
            elif result.get('status') == "MISSING_INGREDIENTS":
                 missing_names = [m['name'] for m in result.get('missing_ingredients', [])]
                 return jsonify({
                     "success": False, 
                     "error": f"Missing constraints or ingredients: {', '.join(missing_names)}"
                 }), 400
                 
        finally:
            SocialMediaExtractor.cleanup(video_path, extract_result.get('thumbnail_path'))

    except Exception as e:
        db.session.rollback()
        import traceback; traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500

@tiktok_bp.route('/api/inspect/<int:source_id>', methods=['GET'])
@login_required
@admin_required
def inspect_source(source_id):
    """Fetches the raw scraped text for a specific TikTok source."""
    source = db.session.get(TikTokSource, source_id)
    if not source:
        return jsonify({"success": False, "error": "Not found"}), 404
        
    return jsonify({
        "success": True, 
        "data": source.raw_caption or "No caption found."
    })

@tiktok_bp.route('/api/deep-scan/<int:source_id>', methods=['POST'])
@login_required
@admin_required
def deep_scan_source(source_id):
    """Downloads the video to definitively update the dish name and format type."""
    from services.social_media_service import SocialMediaExtractor
    from ai_engine import client, types
    import json
    
    source = db.session.get(TikTokSource, source_id)
    if not source:
        return jsonify({"success": False, "error": "Source not found"}), 404
        
    try:
        extract_result = SocialMediaExtractor.download_video(source.tiktok_url)
        video_path = extract_result['video_path']
        
        try:
            file_ref = client.files.upload(file=video_path)
            
            import time
            while True:
                file_info = client.files.get(name=file_ref.name)
                if file_info.state == "ACTIVE":
                    break
                elif file_info.state == "FAILED":
                    raise ValueError("Video processing failed inside Gemini")
                time.sleep(2)
            
            system_prompt = f"""
            Watch this media carefully. 
            CRITICAL: You MUST return a JSON object with EXACTLY this structure:
            {{
                "entity_type": "RECIPE" | "RESOURCE" | "NO_MATCH",
                "dish_name": "The precise name of the food/dish shown, be descriptive but concise",
                "format_type": "VIDEO" | "CAROUSEL_IMAGE"
            }}
            Step 1: If the video demonstrates how to make a specific dish, classify as "RECIPE". If it shares cooking knowledge/techniques without a dish, classify as "RESOURCE". If unrelated to food, classify as "NO_MATCH".
            Step 2: If it looks like a compilation of still photos (a slideshow), answer CAROUSEL_IMAGE. Otherwise, if it is a standard continuous video, answer VIDEO.
            """
            
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=[file_ref, system_prompt],
                config=types.GenerateContentConfig(response_mime_type="application/json")
            )
            
            res_json = json.loads(response.text)
            source.entity_type = res_json.get('entity_type', source.entity_type)
            source.dish_name = res_json.get('dish_name', source.dish_name)
            source.format_type = res_json.get('format_type', 'VIDEO')
            db.session.commit()
            
            return jsonify({
                "success": True, 
                "entity_type": source.entity_type,
                "dish_name": source.dish_name, 
                "format_type": source.format_type
            })
            
        finally:
            SocialMediaExtractor.cleanup(video_path)
            
    except Exception as e:
        db.session.rollback()
        import traceback; traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500

@tiktok_bp.route('/api/delete/<int:source_id>', methods=['DELETE'])
@login_required
@admin_required
def delete_source(source_id):
    """Deletes/Ignores a TikTok source"""
    source = db.session.get(TikTokSource, source_id)
    if not source:
         return jsonify({"success": False, "error": "Not found"}), 404
    
    try:
        db.session.delete(source)
        db.session.commit()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
