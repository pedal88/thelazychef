"""Recipes Blueprint: landing page, recipe library, the recipe page, recipe JSON APIs and public collections."""
from flask import abort, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import or_
from sqlalchemy.orm import selectinload

from database.models import (
    Ingredient,
    Recipe,
    RecipeCollection,
    RecipeDiet,
    RecipeLine,
    RecipeMealType,
    UserRecipeInteraction,
    db,
)
from routes._flat import FlatBlueprint
from routes._shared import DIFFICULTY_LABELS, get_recipe_image_url, load_json_option, viewer_is_admin
from services.chef_service import get_chefs
from services.recipe_v2.derive import HEAT_LABELS

recipes_bp = FlatBlueprint("recipes", __name__)


@recipes_bp.route('/')
def discover():
    """One dish at a time to save or pass on; the cards come from /api/feed/recipes."""
    return render_template('landing.html')


@recipes_bp.route('/recipes')
def recipes_list():
    # 1. Load Filter Data Options
    # Use global load_json_option helper

    cuisine_options = load_json_option('post_processing/cuisines.json', 'cuisines')
    diet_options = load_json_option('constraints/diets.json', 'diets')
    difficulty_options = load_json_option('constraints/difficulty.json', 'difficulty')
    
    # Protein Types (List of Dicts -> List of Strings)
    pt_data = load_json_option('constraints/main_protein.json', 'protein_types')
    protein_options = []
    for p in pt_data:
        if 'examples' in p:
            protein_options.extend(p['examples'])
    protein_options = sorted(list(set(protein_options)))
    
    # Meal types: one list, in the order of the file
    meal_type_options = list(dict.fromkeys(load_json_option('constraints/meal_types.json', 'meal_types')))

    # 2. Handle Query Params (multi-select)
    # Default to ALL options if not specified (First load behavior)
    selected_cuisines = request.args.getlist('cuisine')
    if not selected_cuisines and 'cuisine' not in request.args:
        selected_cuisines = cuisine_options
        
    selected_diets = request.args.getlist('diet')
    if not selected_diets and 'diet' not in request.args:
        selected_diets = diet_options

    selected_meal_types = request.args.getlist('meal_type')
    if not selected_meal_types and 'meal_type' not in request.args:
        selected_meal_types = meal_type_options
    
    selected_difficulties = request.args.getlist('difficulty')
    selected_proteins = request.args.getlist('protein_type')
    # What the dish is finished in (v2, services/recipe_v2/derive.py). Only filters when chosen.
    heat_source_options = list(HEAT_LABELS)
    selected_heat_sources = request.args.getlist('heat_source')

    # 3. Handle View Mode & Base Query
    view_mode = request.args.get('view', 'discover')
    
    # Session Persistence for View Style
    if 'style' in request.args:
        from flask import session
        session['view_style'] = request.args.get('style')
        
    # Get current style from session or default to grid
    from flask import session
    view_style = session.get('view_style', 'grid')

    if view_mode == 'saved' and current_user.is_authenticated:
        # Base query for Saved Recipes
        stmt = (
            db.select(Recipe, UserRecipeInteraction)
            .join(UserRecipeInteraction)
            .where(
                UserRecipeInteraction.user_id == current_user.id,
                UserRecipeInteraction.status == 'favorite',
                Recipe.status == 'approved'
            )
            .order_by(
                UserRecipeInteraction.is_super_like.desc(),
                UserRecipeInteraction.timestamp.desc()
            )
        )
    elif view_mode == 'made' and current_user.is_authenticated:
        # Base query for Made recipes
        stmt = (
            db.select(Recipe, UserRecipeInteraction)
            .join(UserRecipeInteraction)
            .where(
                UserRecipeInteraction.user_id == current_user.id,
                UserRecipeInteraction.is_made == True,
                Recipe.status == 'approved'
            )
            .order_by(UserRecipeInteraction.timestamp.desc())
        )
    elif view_mode == 'next' and current_user.is_authenticated:
        # Base query for Queue
        from database.models import UserQueue
        stmt = (
            db.select(Recipe, UserQueue)
            .join(UserQueue)
            .where(
                UserQueue.user_id == current_user.id,
                Recipe.status == 'approved'
            )
            .order_by(UserQueue.position.asc())
        )
    else:
        # Default Discover query
        view_mode = 'discover'
        stmt = db.select(Recipe).where(Recipe.status == 'approved').order_by(Recipe.id.desc())

    # 4. Apply Filters — only when the user has chosen a STRICT SUBSET of the available options.
    # The default "select all" state should not restrict results at all.
    # Using .any() with a full option list would exclude recipes that have NO tags,
    # which is incorrect for newly added recipes that lack meal_types or diets.
    if selected_cuisines and len(selected_cuisines) < len(cuisine_options):
        stmt = stmt.where(Recipe.cuisine.in_(selected_cuisines))

    if selected_diets and len(selected_diets) < len(diet_options):
        stmt = stmt.where(Recipe.diets.any(RecipeDiet.diet.in_(selected_diets)))

    if selected_difficulties:
        stmt = stmt.where(Recipe.difficulty.in_(selected_difficulties))

    if selected_proteins:
        clauses = []
        for p in selected_proteins:
            # the derived main protein, or any line with that ingredient
            clauses.append(Recipe.protein_type == p)
            clauses.append(Recipe.lines.any(RecipeLine.ingredient.has(Ingredient.name.ilike(f'%{p}%'))))
        if clauses:
             stmt = stmt.where(or_(*clauses))

    if selected_heat_sources and len(selected_heat_sources) < len(heat_source_options):
        stmt = stmt.where(Recipe.heat_source.in_(selected_heat_sources))

    if selected_meal_types and len(selected_meal_types) < len(meal_type_options):
        stmt = stmt.where(Recipe.meal_types.any(RecipeMealType.meal_type.in_(selected_meal_types)))

    # Fetch results, with each card's diets and meal types in one query each rather than one per card
    results = db.session.execute(stmt.options(selectinload(Recipe.diets), selectinload(Recipe.meal_types))).all()
    
    recipes = []
    if view_mode in ['saved', 'made', 'next']:
        for item in results:
            r = item[0]
            # Attach interaction data to recipe object for template
            if view_mode in ('saved', 'made'):
                interaction = item[1]
                r.is_super_liked = getattr(interaction, 'is_super_like', False)
                r.interaction = interaction
            elif view_mode == 'next':
                queue_item = item[1]
                r.queue_position = queue_item.position
            recipes.append(r)
    else:
        recipes = [item[0] for item in results]

    return render_template('recipes_list.html', 
                         recipes=recipes,
                         current_view=view_mode,
                         view_style=view_style,
                         cuisine_options=sorted(cuisine_options),
                         diet_options=sorted(diet_options),
                         difficulty_options=difficulty_options,
                         protein_options=sorted(protein_options),
                         meal_type_options=meal_type_options,
                         # Selected State
                         selected_cuisines=selected_cuisines,
                         selected_diets=selected_diets,
                         selected_meal_types=selected_meal_types,
                         selected_difficulties=selected_difficulties,
                         selected_proteins=selected_proteins,
                         difficulty_labels=DIFFICULTY_LABELS,
                         heat_source_options=heat_source_options,
                         heat_source_labels=HEAT_LABELS,
                         selected_heat_sources=selected_heat_sources)


def _v2_lines_and_steps(recipe):
    """The recipe's lines and its steps in source order, as plain data: each step's text with its {iN} written as the
    ingredient's name. For the inspector and the sub-recipe viewer."""
    from services.recipe_v2.view import PLACEHOLDER

    names = {line.local_id: line.name for line in recipe.lines}
    lines = [{'id': line.id, 'name': line.name, 'prep_style': line.prep_style, 'amount': line.amount, 'unit': line.unit,
              'gram_weight': line.gram_weight, 'component': line.component.name if line.component else None,
              'food_id': line.ingredient.food_id if line.ingredient else None,
              'category': line.ingredient.main_category if line.ingredient else None,
              'image_url': line.ingredient.image_url if line.ingredient else None} for line in recipe.lines]
    steps = [{'step': n, 'phase': step.phase, 'short': step.short,
              'text': PLACEHOLDER.sub(lambda m: names.get(m.group(1), m.group(0)), step.text or ''),
              'component': step.component.name if step.component else None}
             for n, step in enumerate(recipe.steps, 1)]
    return lines, steps


@recipes_bp.route('/api/recipe/<int:recipe_id>', methods=['GET'])
@login_required
def get_recipe_json(recipe_id):
    """A recipe as data for the inspector (components/modals/recipe_inspector.html). Admins only."""
    if not current_user.is_admin:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    recipe = db.session.get(Recipe, recipe_id)
    if not recipe or recipe.schema_version != 2:
        return jsonify({'success': False, 'error': 'Recipe not found'}), 404
    lines, steps = _v2_lines_and_steps(recipe)
    return jsonify({'success': True, 'recipe': {
        'id': recipe.id, 'title': recipe.title, 'cuisine': recipe.cuisine, 'diets': recipe.diets_list,
        'difficulty': recipe.difficulty, 'protein_type': recipe.protein_type, 'meal_types': recipe.meal_types_list,
        'chef_id': recipe.chef_id, 'status': recipe.status, 'prep_time_mins': recipe.prep_time_mins,
        'image_filename': recipe.image_filename,
        'nutrition': {'calories': recipe.total_calories, 'protein': recipe.total_protein, 'carbs': recipe.total_carbs,
                      'fat': recipe.total_fat, 'sugar': recipe.total_sugar, 'fiber': recipe.total_fiber},
        'ingredients': lines, 'instructions': steps,
    }})


@recipes_bp.route('/api/sub-recipe/<int:recipe_id>', methods=['GET'])
def get_sub_recipe(recipe_id):
    """Public read-only endpoint for the sub-recipe modal viewer.
    Returns only approved recipes (or any recipe whose id is referenced as
    a sub_recipe_id — admin may link draft sub-recipes intentionally)."""
    recipe = db.session.get(Recipe, recipe_id)
    linked = recipe is not None and db.session.execute(
        db.select(Ingredient.id).where(Ingredient.sub_recipe_id == recipe.id).limit(1)
    ).first() is not None
    if not recipe or recipe.schema_version != 2 or (recipe.status != 'approved' and not linked and not viewer_is_admin()):
        return jsonify({'success': False, 'error': 'Sub-recipe not found'}), 404

    lines, steps = _v2_lines_and_steps(recipe)
    components, steps_by_comp = {}, {}
    for line in lines:
        components.setdefault(line['component'] or 'Main', []).append(
            {k: line[k] for k in ('name', 'amount', 'unit', 'gram_weight', 'image_url')})
    for step in steps:
        steps_by_comp.setdefault(step['component'] or 'Main', []).append({k: step[k] for k in ('step', 'phase', 'text')})
    return jsonify({
        'success': True,
        'recipe': {
            'id': recipe.id,
            'title': recipe.title,
            'cuisine': recipe.cuisine,
            'image_url': get_recipe_image_url(recipe) if recipe.image_filename else None,
            'base_servings': recipe.base_servings,
            'components': list(components.keys()),
            'ingredients_by_component': components,
            'steps_by_component': steps_by_comp,
        }
    })


@recipes_bp.route('/api/search-recipes', methods=['GET'])
@login_required
def search_recipes_api():
    """Live-search endpoint for the sub-recipe picker on the ingredient form."""
    if not current_user.is_admin:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    q = request.args.get('q', '').strip()
    if len(q) < 2:
        return jsonify({'results': []})
    results = db.session.execute(
        db.select(Recipe.id, Recipe.title, Recipe.cuisine, Recipe.status)
        .where(Recipe.title.ilike(f'%{q}%'))
        .order_by(Recipe.title.asc())
        .limit(10)
    ).all()
    return jsonify({
        'results': [
            {'id': r.id, 'title': r.title, 'cuisine': r.cuisine or '', 'status': r.status}
            for r in results
        ]
    })


@recipes_bp.route('/recipe/<int:recipe_id>')
def recipe_detail(recipe_id):
    recipe = db.session.get(Recipe, recipe_id)
    if not recipe or (recipe.status != 'approved' and not viewer_is_admin()):
        flash("Recipe not found.", "error")
        return redirect(url_for('discover'))

    # The old recipes (model v1) are retired: archived, and their page is gone (scripts/retire_v1.py)
    if recipe.schema_version != 2:
        abort(404)
    from services.recipe_v2.view import page
    view = page(recipe, servings=request.args.get('servings', type=int), plan=request.args.get('plan', 'calm'))
    admin = {}
    if viewer_is_admin():
        # The dish and all its versions by chef personas, and the chefs that can make one
        root = recipe.base_recipe or recipe
        admin = {'family': [root] + sorted(root.versions, key=lambda r: r.id), 'chefs': get_chefs()}
    # One page: the overview, and prep and cooking together (#prep, #cook)
    return render_template('recipe_v2_make.html', recipe=recipe, v=view, admin=admin)


# The addresses of the tabs the recipe page had until 27.10.2026, kept for links already shared: they open the recipe
# page at its part, Prep with the bowls and Cook with the steps (static/js/steps.js).
@recipes_bp.route('/recipe/<int:recipe_id>/get-ready')
@recipes_bp.route('/recipe/<int:recipe_id>/prep')
def recipe_prep(recipe_id):
    return redirect(url_for('recipe_detail', recipe_id=recipe_id, **request.args) + '#prep')


@recipes_bp.route('/recipe/<int:recipe_id>/cook')
def recipe_cook(recipe_id):
    return redirect(url_for('recipe_detail', recipe_id=recipe_id, **request.args) + '#cook')


@recipes_bp.route('/recipe/<int:recipe_id>/make')
def recipe_make(recipe_id):
    return redirect(url_for('recipe_detail', recipe_id=recipe_id, **request.args))


@recipes_bp.route('/recipe/<int:recipe_id>/print')
def recipe_print(recipe_id):
    """The river delta on one A4 sheet, portrait or landscape. Opens the print dialog unless ?auto=0."""
    recipe = db.session.get(Recipe, recipe_id)
    if not recipe or (recipe.status != 'approved' and not viewer_is_admin()):
        flash("Recipe not found.", "error")
        return redirect(url_for('discover'))
    if recipe.schema_version != 2:
        return redirect(url_for('recipe_detail', recipe_id=recipe_id))
    from services.recipe_v2.view import page
    view = page(recipe, servings=request.args.get('servings', type=int))
    if not view['delta']:
        return redirect(url_for('recipe_detail', recipe_id=recipe_id))
    orient = 'landscape' if request.args.get('orient') == 'landscape' else 'portrait'
    return render_template('recipe_print.html', recipe=recipe, v=view, orient=orient,
                           autoprint=request.args.get('auto') != '0')


@recipes_bp.route('/collections')
def collections_index():
    """Public index of all published collections, with their approved recipes pre-loaded."""
    raw = (
        db.session.execute(
            db.select(RecipeCollection)
            .where(RecipeCollection.is_published.is_(True))
            .order_by(RecipeCollection.created_at.desc())
        )
        .scalars()
        .all()
    )
    # Build (collection, [recipe, ...]) pairs — filter approved at route level
    rows = [
        (col, [item.recipe for item in col.items if item.recipe.status == 'approved'])
        for col in raw
    ]
    return render_template('collections_index.html', rows=rows)


@recipes_bp.route('/collections/<slug>')
def collection_detail(slug: str):
    """Public detail page for a single published collection."""
    collection = db.session.execute(
        db.select(RecipeCollection).where(RecipeCollection.slug == slug)
    ).scalar_one_or_none()

    if not collection or not collection.is_published:
        abort(404)

    # Filter only approved recipes at the route level (belt-and-suspenders)
    recipes = [
        item.recipe
        for item in collection.items
        if item.recipe.status == 'approved'
    ]

    return render_template('collection_detail.html', collection=collection, recipes=recipes)
