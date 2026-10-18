"""Admin Recipes Blueprint: recipe management, QA evaluation, status, cloning, deletion and bulk generation."""
from urllib.parse import urlencode

from flask import jsonify, render_template, request
from flask_login import login_required
from sqlalchemy import func, or_
from sqlalchemy.orm import joinedload

from ai_engine import load_controlled_vocabularies
from database.models import (
    Recipe,
    RecipeDiet,
    RecipeEvaluation,
    RecipeMealType,
    db,
)
from routes._flat import FlatBlueprint
from services.recipe_service import delete_recipes
from utils.decorators import admin_required

admin_recipes_bp = FlatBlueprint("admin_recipes", __name__)


@admin_recipes_bp.route('/admin/recipes-management')
@login_required
@admin_required
def admin_recipes_management():
    # Sorting & pagination parameters
    sort_col = request.args.get('sort', 'id')
    sort_dir = request.args.get('dir', 'desc')
    page = request.args.get('page', 1, type=int)
    search_term = request.args.get('search', '').lower().strip()
    per_page = 50

    # Filter parameters
    selected_cuisines = request.args.getlist('cuisine')
    selected_diets = request.args.getlist('diet')
    selected_meal_types = request.args.getlist('meal_type')
    selected_proteins = request.args.getlist('protein')
    selected_difficulties = request.args.getlist('difficulty')
    selected_statuses = request.args.getlist('status')

    # Load Vocabs for filters
    vocab = load_controlled_vocabularies()
    cuisine_options = vocab.get('cuisines', [])
    diet_options = vocab.get('diets', [])
    meal_type_options = vocab.get('meal_types', [])
    protein_options = vocab.get('proteins', [])
    difficulty_options = vocab.get('difficulties', [])
    status_options = ['draft', 'approved', 'rejected']

    # Base query — LEFT JOIN so recipes with no evaluation still appear
    # Ensure optimal DB queries for diets and evaluations
    stmt = db.select(Recipe).outerjoin(Recipe.evaluation).options(
        joinedload(Recipe.diets),
        joinedload(Recipe.evaluation),
        joinedload(Recipe.meal_types)
    )

    if search_term:
        stmt = stmt.where(
            or_(
                func.lower(Recipe.title).contains(search_term),
                func.lower(Recipe.cuisine).contains(search_term)
            )
        )

    # Apply Filters
    if selected_cuisines:
        stmt = stmt.where(Recipe.cuisine.in_(selected_cuisines))
    if selected_proteins:
        stmt = stmt.where(Recipe.protein_type.in_(selected_proteins))
    if selected_difficulties:
        stmt = stmt.where(Recipe.difficulty.in_(selected_difficulties))
    if selected_statuses:
        stmt = stmt.where(Recipe.status.in_(selected_statuses))
    if selected_diets:
        stmt = stmt.where(Recipe.diets.any(RecipeDiet.diet.in_(selected_diets)))
    if selected_meal_types:
        stmt = stmt.where(Recipe.meal_types.any(RecipeMealType.meal_type.in_(selected_meal_types)))

    # Apply sorting
    valid_cols = {
        'id': Recipe.id,
        'title': Recipe.title,
        'cuisine': Recipe.cuisine,
        'difficulty': Recipe.difficulty,
        'total_score': RecipeEvaluation.total_score,
        'score_name': RecipeEvaluation.score_name,
        'score_ingredients': RecipeEvaluation.score_ingredients,
        'score_components': RecipeEvaluation.score_components,
        'score_amounts': RecipeEvaluation.score_amounts,
        'score_steps': RecipeEvaluation.score_steps,
        'score_image': RecipeEvaluation.score_image,
        'total_calories': Recipe.total_calories,
        'total_protein': Recipe.total_protein,
        'total_fat': Recipe.total_fat,
        'total_carbs': Recipe.total_carbs
    }
    sort_attr = valid_cols.get(sort_col, Recipe.id)
    stmt = stmt.order_by(sort_attr.asc() if sort_dir == 'asc' else sort_attr.desc())

    # Paginate — fetches only `per_page` rows from DB per request
    pagination = db.paginate(stmt, page=page, per_page=per_page, error_out=False)

    return render_template(
        'admin/recipes_management.html',
        recipes=pagination.items,
        pagination=pagination,
        current_sort=sort_col,
        current_dir=sort_dir,
        current_search=search_term,
        cuisine_options=cuisine_options,
        diet_options=diet_options,
        meal_type_options=meal_type_options,
        protein_options=protein_options,
        difficulty_options=difficulty_options,
        status_options=status_options,
        selected_cuisines=selected_cuisines,
        selected_diets=selected_diets,
        selected_meal_types=selected_meal_types,
        selected_proteins=selected_proteins,
        selected_difficulties=selected_difficulties,
        selected_statuses=selected_statuses,
        urlencode=lambda args: urlencode(args, doseq=True)
    )

@admin_recipes_bp.route('/admin/recipes/<int:recipe_id>/evaluate', methods=['POST'])
@login_required
@admin_required
def evaluate_recipe_api(recipe_id):
    from services.evaluation_service import evaluate_recipe
    try:
        result = evaluate_recipe(recipe_id)
        return jsonify(result)
    except Exception as e:
        print(f"Error evaluating recipe: {e}")
        return jsonify({'status': 'error', 'error': str(e)}), 500


@admin_recipes_bp.route('/admin/recipes/<int:recipe_id>/status', methods=['POST'])
@login_required
@admin_required
def update_recipe_status(recipe_id: int):
    """Async endpoint to update a recipe's publishing status."""
    VALID_STATUSES = {'draft', 'approved', 'rejected'}
    try:
        data = request.get_json()
        new_status = data.get('status', '').strip().lower()
        if new_status not in VALID_STATUSES:
            return jsonify({'success': False, 'error': f'Invalid status. Must be one of: {VALID_STATUSES}'}), 400

        recipe = db.session.get(Recipe, recipe_id)
        if not recipe:
            return jsonify({'success': False, 'error': 'Recipe not found'}), 404

        recipe.status = new_status
        db.session.commit()
        print(f"Status update: Recipe #{recipe_id} -> '{new_status}'")
        return jsonify({'success': True, 'new_status': recipe.status})

    except Exception as e:
        db.session.rollback()
        print(f"Status update error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_recipes_bp.route('/admin/api/recipes/<int:recipe_id>/clone', methods=['POST'])
@login_required
@admin_required
def clone_recipe_api(recipe_id: int):
    """Admin endpoint to deep-clone a recipe with ingredient overrides."""
    from services.recipe_service import clone_recipe
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No JSON payload provided'}), 400
            
        new_title = data.get('new_title')
        if not new_title:
            return jsonify({'success': False, 'error': 'new_title is required'}), 400
            
        ingredient_overrides = data.get('ingredient_overrides', {})
        
        # Perform the deep clone using our new Python utility
        new_recipe_id = clone_recipe(recipe_id, new_title, ingredient_overrides, db.session)
        
        return jsonify({
            'success': True, 
            'new_recipe_id': new_recipe_id,
            'message': 'Recipe cloned successfully!'
        })

    except Exception as e:
        db.session.rollback()
        print(f"Error cloning recipe: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_recipes_bp.route('/api/delete-recipe/<int:recipe_id>', methods=['DELETE'])
@login_required
@admin_required
def delete_recipe_api(recipe_id):
    try:
        recipe = db.session.get(Recipe, recipe_id)
        if not recipe:
             return jsonify({'success': False, 'error': 'Recipe not found'}), 404
             
        delete_recipes([recipe_id])

        return jsonify({'success': True, 'message': f"Recipe {recipe_id} deleted successfully."})
        
    except Exception as e:
        db.session.rollback()
        print(f"Delete Recipe Error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_recipes_bp.route('/api/delete-recipes/bulk', methods=['POST'])
@login_required
@admin_required
def delete_bulk_recipes():
    """Permanently delete one or more recipes and all their child records."""
    data = request.get_json(silent=True) or {}
    recipe_ids = data.get('recipe_ids', [])

    if not recipe_ids or not isinstance(recipe_ids, list):
        return jsonify({'success': False, 'error': 'No valid recipe IDs provided'}), 400

    try:
        recipe_ids = [int(rid) for rid in recipe_ids]
    except (ValueError, TypeError) as e:
        return jsonify({'success': False, 'error': f'Invalid recipe ID: {e}'}), 400

    if not recipe_ids:
        return jsonify({'success': False, 'error': 'No valid integer IDs after parsing'}), 400

    try:
        deleted_count = delete_recipes(recipe_ids)
        print(f"[Bulk Delete] Deleted {deleted_count} recipes: {recipe_ids}")
        return jsonify({'success': True, 'count': deleted_count,
                        'message': f"Deleted {deleted_count} recipes."})

    except Exception as e:
        db.session.rollback()
        import traceback
        print(f"[Bulk Delete ERROR] {e}\n{traceback.format_exc()}")
        return jsonify({'success': False, 'error': str(e)}), 500
