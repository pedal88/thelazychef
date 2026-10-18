"""Admin Chefs Blueprint: view and edit the chef personas (stored in the chef table)."""
from flask import jsonify, render_template, request
from flask_login import login_required

from database.models import db
from routes._flat import FlatBlueprint
from routes._shared import load_json_option
from services.chef_service import get_chefs, update_chefs
from utils.decorators import admin_required

admin_chefs_bp = FlatBlueprint("admin_chefs", __name__)


@admin_chefs_bp.route('/admin/chefs')
@login_required
@admin_required
def chefs_list():
    diets_data = load_json_option('diets_tag.json', 'diets')
    
    # Load Cooking Methods (Grouped)
    methods_data_raw = load_json_option('cooking_methods.json', 'cooking_methods')
    grouped_methods = {}
    for m in methods_data_raw:
        cat = m['category']
        if cat not in grouped_methods:
            grouped_methods[cat] = []
        grouped_methods[cat].append(m['method'])
    
    # Sort keys
    grouped_methods = dict(sorted(grouped_methods.items()))
    
    return render_template('chefs.html', chefs=get_chefs(), diets_list=diets_data, grouped_methods=grouped_methods)

@admin_chefs_bp.route('/admin/chefs/save', methods=['POST'])
@login_required
@admin_required
def save_chefs_json():
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or not isinstance(data.get('chefs'), list):
        return jsonify({'success': False, 'error': 'Invalid JSON structure'}), 400

    try:
        missing = update_chefs(data['chefs'])
    except Exception as e:
        db.session.rollback()
        print(f"Error saving chefs: {e}")
        return jsonify({'success': False, 'error': 'Could not save the chefs. Please try again.'}), 500

    if missing:
        return jsonify({'success': False, 'error': f"Unknown chef id(s): {', '.join(map(str, missing))}"}), 404
    return jsonify({'success': True})
