"""Explore Blueprint: the D3 recipe and ingredient galaxies and the orbital graph."""
import json
import os

from flask import jsonify, render_template, url_for
from sqlalchemy import or_

from database.models import Ingredient, Recipe, db
from routes._flat import FlatBlueprint
from routes._shared import get_recipe_image_url

explore_bp = FlatBlueprint("explore", __name__)

graph_metadata_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'constraints', 'graph_metadata.json')
try:
    with open(graph_metadata_path, 'r') as f:
        GRAPH_METADATA = json.load(f)
except Exception as e:
    print(f"Warning: Could not load graph metadata: {e}")
    GRAPH_METADATA = {"cuisines": {}, "proteins": {}}

def get_node_image(group_type, name):
    if group_type == 'cuisine':
        code = GRAPH_METADATA.get('cuisines', {}).get(name) or GRAPH_METADATA.get('cuisines', {}).get('Other', 'un')
        return f"https://flagcdn.com/w80/{code}.png"
    elif group_type == 'protein':
        return GRAPH_METADATA.get('proteins', {}).get(name) or GRAPH_METADATA.get('proteins', {}).get('Other')
    return None


@explore_bp.route('/explore/galaxy')
def explore_galaxy():
    """Renders the full-screen interactive D3 graph of all recipes."""
    from services.concept_visual_service import get_concept_images_dict
    return render_template('explore_galaxy.html', concept_visuals=get_concept_images_dict())

@explore_bp.route('/api/graph/galaxy', methods=['GET'])
def get_global_galaxy_graph():
    """Returns nodes and links for ALL approved recipes linked to their cuisines & proteins."""
    recipes = db.session.execute(
        db.select(Recipe).where(Recipe.status == 'approved')
    ).scalars().all()
    
    nodes_dict = {}
    links = []
    
    for r in recipes:
        # Add the recipe node itself
        rec_id = f"recipe_{r.id}"
        nodes_dict[rec_id] = {
            'id': rec_id,
            'name': r.title,
            'group': 'recipe',
            'image': get_recipe_image_url(r) if r.image_filename else None,
            'url': url_for('recipe_detail', recipe_id=r.id)
        }
        
        # Determine attributes
        c_attr = r.cuisine
        p_attr = r.protein_type
        
        # Link to Cuisine
        if c_attr:
            c_id = f"attr_cuisine_{c_attr}"
            if c_id not in nodes_dict:
                nodes_dict[c_id] = {
                    'id': c_id, 'name': c_attr, 'group': 'cuisine',
                    'image': get_node_image('cuisine', c_attr)
                }
            links.append({'source': rec_id, 'target': c_id, 'weight': 1.0})
            
        # Link to Protein
        if p_attr:
            p_id = f"attr_protein_{p_attr}"
            if p_id not in nodes_dict:
                nodes_dict[p_id] = {
                    'id': p_id, 'name': p_attr, 'group': 'protein',
                    'image': get_node_image('protein', p_attr)
                }
            links.append({'source': rec_id, 'target': p_id, 'weight': 1.0})

    return jsonify({'nodes': list(nodes_dict.values()), 'links': links})

@explore_bp.route('/explore/ingredient-galaxy')
def explore_ingredient_galaxy():
    """Renders the full-screen interactive D3 graph of ingredients."""
    from services.concept_visual_service import get_concept_images_dict
    return render_template('explore_ingredient_galaxy.html', concept_visuals=get_concept_images_dict())

@explore_bp.route('/api/graph/ingredient-galaxy', methods=['GET'])
def get_global_ingredient_galaxy_graph():
    """Returns nodes and links for ingredients linked to main and sub categories."""
    ingredients = db.session.execute(
        db.select(Ingredient).where(Ingredient.status != 'inactive')
    ).scalars().all()
    
    nodes_dict = {}
    links = []
    
    for i in ingredients:
        ing_id = f"ing_{i.id}"
        nodes_dict[ing_id] = {
            'id': ing_id,
            'name': i.name,
            'group': 'ingredient',
            'image': i.image_url if i.image_url else None
        }
        
        main_cat = i.main_category or "Uncategorized"
        sub_cat = i.sub_category or "General"
        
        m_id = f"main_{main_cat}"
        if m_id not in nodes_dict:
            nodes_dict[m_id] = {
                'id': m_id, 'name': main_cat, 'group': 'main_cat'
            }
            
        # Add a sub-category node only if it differs from the main category
        # Sometimes sub_category empty, default to "General"
        if sub_cat and main_cat != sub_cat:
            s_id = f"sub_{sub_cat}"
            if s_id not in nodes_dict:
                nodes_dict[s_id] = {
                    'id': s_id, 'name': sub_cat, 'group': 'sub_cat'
                }
            links.append({'source': s_id, 'target': m_id, 'weight': 2.0})
            links.append({'source': ing_id, 'target': s_id, 'weight': 1.0})
        else:
            links.append({'source': ing_id, 'target': m_id, 'weight': 1.0})

    return jsonify({'nodes': list(nodes_dict.values()), 'links': links})

@explore_bp.route('/api/graph/orbital/<int:recipe_id>', methods=['GET'])
def get_orbital_graph(recipe_id):
    target = db.session.get(Recipe, recipe_id)
    if not target:
        return jsonify({'error': 'Recipe not found'}), 404
        
    nodes = []
    links = []
    
    # 1. Add center node (The Sun)
    nodes.append({
        'id': f"recipe_{target.id}",
        'name': target.title,
        'group': 'center',
        'image': get_recipe_image_url(target) if target.image_filename else None,
        'url': url_for('recipe_detail', recipe_id=target.id) 
    })
    
    c_attr = target.cuisine
    p_attr = target.protein_type
    
    # 2. Add Attribute Nodes (Planets)
    if c_attr:
        nodes.append({
            'id': f"attr_cuisine_{c_attr}", 'name': c_attr, 'group': 'cuisine',
            'image': get_node_image('cuisine', c_attr)
        })
        links.append({'source': f"attr_cuisine_{c_attr}", 'target': f"recipe_{target.id}", 'weight': 5.0}) 
        
    if p_attr:
        nodes.append({
            'id': f"attr_protein_{p_attr}", 'name': p_attr, 'group': 'protein',
            'image': get_node_image('protein', p_attr)
        })
        links.append({'source': f"attr_protein_{p_attr}", 'target': f"recipe_{target.id}", 'weight': 5.0}) 

    # 3. Discover Siblings (Moons)
    if c_attr or p_attr:
        conditions = []
        if c_attr: conditions.append(Recipe.cuisine == c_attr)
        if p_attr: conditions.append(Recipe.protein_type == p_attr)
        
        query = db.select(Recipe).where(
            Recipe.id != target.id,
            Recipe.status == 'approved',
            or_(*conditions)
        ).limit(10)
        
        siblings = db.session.execute(query).scalars().all()
        
        for sib in siblings:
            nodes.append({
                'id': f"recipe_{sib.id}",
                'name': sib.title,
                'group': 'sibling',
                'image': get_recipe_image_url(sib) if sib.image_filename else None,
                'url': url_for('recipe_detail', recipe_id=sib.id)
            })
            
            matches_c = (sib.cuisine == c_attr) and c_attr
            matches_p = (sib.protein_type == p_attr) and p_attr
            
            if matches_c and matches_p:
                links.append({'source': f"recipe_{sib.id}", 'target': f"attr_cuisine_{c_attr}", 'weight': 2.0})
                links.append({'source': f"recipe_{sib.id}", 'target': f"attr_protein_{p_attr}", 'weight': 2.0})
            else:
                if matches_c:
                    links.append({'source': f"recipe_{sib.id}", 'target': f"attr_cuisine_{c_attr}", 'weight': 1.0})
                if matches_p:
                    links.append({'source': f"recipe_{sib.id}", 'target': f"attr_protein_{p_attr}", 'weight': 1.0})

    return jsonify({'nodes': nodes, 'links': links})
