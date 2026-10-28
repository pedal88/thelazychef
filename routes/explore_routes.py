"""Explore Blueprint: the D3 recipe and ingredient galaxies and the orbital graph."""
import json
import os

from flask import jsonify, render_template, url_for
from sqlalchemy import or_

from database.models import ConceptVisual, Ingredient, Recipe, RecipeLine, db
from routes._flat import FlatBlueprint
from routes._shared import get_recipe_image_url

explore_bp = FlatBlueprint("explore", __name__)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _symbols():
    """The symbols of the recipe galaxy's planets, in the style of the ingredient symbols:
    {'cuisine': {name: url}, 'protein': {label: url}}.

    A cuisine shows the dish made for it (concept_visual "cuisine", scripts/category_symbols.py --kind cuisine).
    A protein shows the symbol of a typical pantry ingredient (main_protein.json "symbol_from"), so it is in the
    same style; concept_visual "main_protein" only fills in where no such ingredient has a symbol (older images of
    another style are kept there)."""
    visuals = {(v.concept_type, v.concept_name): v.image_url for v in db.session.execute(
        db.select(ConceptVisual).where(ConceptVisual.concept_type.in_(('cuisine', 'main_protein')),
                                       ConceptVisual.image_url.is_not(None))).scalars()}
    with open(os.path.join(ROOT, 'data', 'constraints', 'main_protein.json'), encoding='utf-8') as f:
        symbol_from = json.load(f).get('symbol_from', {})
    wanted = {name for names in symbol_from.values() for name in names}
    pictured = dict(db.session.execute(db.select(db.func.lower(Ingredient.name), Ingredient.image_url).where(
        db.func.lower(Ingredient.name).in_(wanted), Ingredient.status == 'active', Ingredient.image_url.is_not(None))).all())
    protein = {name: url for (kind, name), url in visuals.items() if kind == 'main_protein'}
    protein.update({label: url for label, names in symbol_from.items()
                    if (url := next((pictured[n] for n in names if n in pictured), None))})
    return {'cuisine': {name: url for (kind, name), url in visuals.items() if kind == 'cuisine'}, 'protein': protein}


@explore_bp.route('/explore/galaxy')
def explore_galaxy():
    """Renders the full-screen interactive D3 graph of all recipes."""
    from services.concept_visual_service import get_concept_images_dict
    return render_template('explore_galaxy.html', concept_visuals=get_concept_images_dict())

@explore_bp.route('/api/graph/galaxy', methods=['GET'])
def get_global_galaxy_graph():
    """Every approved recipe, linked to its cuisine and its main protein (services/recipe_v2/derive.main_protein).
    The planets show the symbols from _symbols()."""
    recipes = db.session.execute(
        db.select(Recipe).where(Recipe.status == 'approved')
    ).scalars().all()
    symbols = _symbols()
    
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
                    'image': symbols['cuisine'].get(c_attr)
                }
            links.append({'source': rec_id, 'target': c_id, 'weight': 1.0})
            
        # Link to Protein
        if p_attr:
            p_id = f"attr_protein_{p_attr}"
            if p_id not in nodes_dict:
                nodes_dict[p_id] = {
                    'id': p_id, 'name': p_attr, 'group': 'protein',
                    'image': symbols['protein'].get(p_attr)
                }
            links.append({'source': rec_id, 'target': p_id, 'weight': 1.0})

    return jsonify({'nodes': list(nodes_dict.values()), 'links': links})

@explore_bp.route('/explore/ingredient-galaxy')
def explore_ingredient_galaxy():
    """Renders the full-screen interactive D3 graph of ingredients."""
    from services.concept_visual_service import get_concept_images_dict
    return render_template('explore_ingredient_galaxy.html', concept_visuals=get_concept_images_dict())

def _clean(text):
    """A category name as one plain string: some were saved with non-breaking spaces ("canned\xa0fish")."""
    return ' '.join((text or '').replace('\xa0', ' ').split())


@explore_bp.route('/api/graph/ingredient-galaxy', methods=['GET'])
def get_global_ingredient_galaxy_graph():
    """Active ingredients linked to their sub category, and that to its main category (Ingredient.main_category and
    sub_category, two text columns checked against data/constraints/categories.json).

    A main category shows its own symbol (concept_visual "ingredient_category", made by scripts/category_symbols.py).
    A sub category shows the symbol of its most used ingredient in approved recipes, unless concept_visual
    "ingredient_subcategory" has one for it. A sub category is one node per main category, as it is stored: "juices"
    under fruit and under drinks are two. Each ingredient carries "uses", the number of approved recipes with it."""
    ingredients = db.session.execute(db.select(Ingredient).where(Ingredient.status == 'active')).scalars().all()
    uses = dict(db.session.execute(
        db.select(RecipeLine.ingredient_id, db.func.count(db.distinct(RecipeLine.recipe_id)))
        .join(Recipe, Recipe.id == RecipeLine.recipe_id).where(Recipe.status == 'approved')
        .group_by(RecipeLine.ingredient_id)).all())
    symbols = {(v.concept_type, v.concept_name): v.image_url for v in db.session.execute(
        db.select(ConceptVisual).where(ConceptVisual.concept_type.in_(('ingredient_category', 'ingredient_subcategory')),
                                       ConceptVisual.image_url.is_not(None))).scalars()}

    nodes, links, members = {}, [], {}
    for i in ingredients:
        ing_id = f"ing_{i.id}"
        nodes[ing_id] = {'id': ing_id, 'name': i.name, 'group': 'ingredient', 'image': i.image_url or None,
                         'uses': uses.get(i.id, 0)}
        main_cat = _clean(i.main_category) or 'Uncategorized'
        sub_cat = _clean(i.sub_category) or 'General'
        m_id = f"main_{main_cat}"
        if m_id not in nodes:
            nodes[m_id] = {'id': m_id, 'name': main_cat, 'group': 'main_cat',
                           'image': symbols.get(('ingredient_category', main_cat))}
        if main_cat != sub_cat:
            s_id = f"sub_{main_cat}|{sub_cat}"
            if s_id not in nodes:
                nodes[s_id] = {'id': s_id, 'name': sub_cat, 'group': 'sub_cat',
                               'image': symbols.get(('ingredient_subcategory', sub_cat))}
                links.append({'source': s_id, 'target': m_id, 'weight': 2.0})
            members.setdefault(s_id, []).append(nodes[ing_id])
            links.append({'source': ing_id, 'target': s_id, 'weight': 1.0})
        else:
            links.append({'source': ing_id, 'target': m_id, 'weight': 1.0})

    # A sub category without its own symbol shows its most used ingredient that has one
    for s_id, items in members.items():
        if not nodes[s_id]['image']:
            pictured = sorted((n for n in items if n['image']), key=lambda n: (-n['uses'], n['name']))
            nodes[s_id]['image'] = pictured[0]['image'] if pictured else None
        nodes[s_id]['uses'] = sum(n['uses'] for n in items)
    return jsonify({'nodes': list(nodes.values()), 'links': links})


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
    symbols = _symbols()

    # 2. Add Attribute Nodes (Planets)
    if c_attr:
        nodes.append({
            'id': f"attr_cuisine_{c_attr}", 'name': c_attr, 'group': 'cuisine',
            'image': symbols['cuisine'].get(c_attr)
        })
        links.append({'source': f"attr_cuisine_{c_attr}", 'target': f"recipe_{target.id}", 'weight': 5.0}) 
        
    if p_attr:
        nodes.append({
            'id': f"attr_protein_{p_attr}", 'name': p_attr, 'group': 'protein',
            'image': symbols['protein'].get(p_attr)
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
