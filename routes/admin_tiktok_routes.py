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
    
    # We also want to quickly highlight if they are already in the Recipe DB's source_input
    # but the deduplication handles that.
    
    return render_template('admin/tiktok_sidecar.html', sources=sources)

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
        # The Bridge!
        result = create_recipe_from_extracted_json(source.extracted_json, source_url=source.tiktok_url)
        
        if result['status'] == "SUCCESS":
             # Mark as imported
             source.status = "IMPORTED"
             db.session.commit()
             return jsonify({"success": True, "recipe_id": result['recipe_id']})
             
        elif result['status'] == "MISSING_INGREDIENTS":
             missing_names = [m['name'] for m in result.get('missing_ingredients', [])]
             return jsonify({
                 "success": False, 
                 "error": f"Missing constraints or ingredients: {', '.join(missing_names)}"
             }), 400
             
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
