"""Admin Chefs Blueprint: view and edit the chef personas."""
import json
import os

from flask import jsonify, render_template, request
from flask_login import login_required

from ai_engine import chefs_data
from routes._flat import FlatBlueprint
from routes._shared import load_json_option
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
    
    return render_template('chefs.html', chefs=chefs_data, diets_list=diets_data, grouped_methods=grouped_methods)

@admin_chefs_bp.route('/admin/chefs/save', methods=['POST'])
@login_required
@admin_required
def save_chefs_json():
    try:
        data = request.get_json()
        if not data or 'chefs' not in data:
            return jsonify({'success': False, 'error': 'Invalid JSON structure'}), 400
        
        new_chefs = data['chefs']
        
        # Validate/Persist
        json_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "chefs.json")
        
        # We replace the entire list with the new data from UI
        # But we should preserve structure wrappers if any
        full_data = {"chefs": new_chefs}
        
        with open(json_path, 'w') as f:
            json.dump(full_data, f, indent=2)
            
        # Update the shared list in place, so app.py, this module and ai_engine
        # (which all imported the same chefs_data object) see the new chefs
        import ai_engine
        chefs_data[:] = new_chefs
        ai_engine.chef_map = {c['id']: c for c in new_chefs}

        return jsonify({'success': True})
        
    except Exception as e:
        print(f"Error saving chefs: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
