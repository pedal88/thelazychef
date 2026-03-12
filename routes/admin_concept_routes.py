from flask import Blueprint, jsonify, render_template, request, flash, redirect, url_for
from flask_login import login_required
from utils.decorators import admin_required
from database.models import db, ConceptVisual
from services.concept_visual_service import sync_concept_visuals
from services.vertex_image_service import VertexImageGenerator
from services.storage_service import get_storage_provider
import io
import uuid

admin_concept_bp = Blueprint('admin_concept', __name__, url_prefix='/admin/concept-visuals')

@admin_concept_bp.route('/', methods=['GET'])
@login_required
@admin_required
def dashboard():
    """Displays all concept visuals grouped by their type."""
    # Ensure they are synced at least once
    sync_concept_visuals()
    
    visuals = db.session.execute(
        db.select(ConceptVisual).order_by(ConceptVisual.concept_type, ConceptVisual.concept_name)
    ).scalars().all()
    
    grouped = {}
    for v in visuals:
        if v.concept_type not in grouped:
            grouped[v.concept_type] = []
        grouped[v.concept_type].append(v)
        
    return render_template('admin/concept_visuals.html', grouped_visuals=grouped)

@admin_concept_bp.route('/generate', methods=['POST'])
@login_required
@admin_required
def generate_visual():
    """Generates an icon image for the given conceptual metadata point."""
    data = request.get_json() or {}
    record_id = data.get('id')
    
    if not record_id:
        return jsonify({"success": False, "error": "Missing concept ID"}), 400
        
    record = db.session.get(ConceptVisual, record_id)
    if not record:
        return jsonify({"success": False, "error": "Concept not found"}), 404
        
    prompt = f"A clean, modern, minimalist culinary icon representing the {record.concept_type.replace('_', ' ')}: {record.concept_name}. Rendered on a pure solid white background, app UI style, high quality."
    
    try:
        image_bytes = VertexImageGenerator.generate_image(prompt)
        
        storage_provider = get_storage_provider()
        safe_name = "".join(c for c in f"{record.concept_type}_{record.concept_name}" if c.isalnum() or c in '_-')
        filename = f"concept_visuals/{safe_name}_{uuid.uuid4().hex[:8]}.png"
        
        url = storage_provider.upload_file(io.BytesIO(image_bytes), filename, content_type="image/png")
        
        record.image_url = url
        db.session.commit()
        
        return jsonify({"success": True, "image_url": url, "id": record.id})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
