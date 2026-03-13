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
        
    try:
        # Get storage provider to pass to generator
        storage_provider = get_storage_provider()
        generator = VertexImageGenerator(storage_provider)
        
        # We process concept visuals as "taxonomy" to get the 3D isometric icons
        result = generator.generate_candidate(
            ingredient_name=f"{record.concept_type}::{record.concept_name}",
            prompt=None,
            scope="taxonomy"
        )
        
        if result.get('success'):
            record.image_url = result['image_url']
            db.session.commit()
            return jsonify({"success": True, "image_url": result['image_url'], "id": record.id})
        else:
            return jsonify({"success": False, "error": result.get('error', 'Unknown generation error')}), 500
            
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
