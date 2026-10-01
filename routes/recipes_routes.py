"""Recipes Blueprint: landing page, recipe library, recipe detail and kitchen mode, recipe JSON APIs and public collections."""
import json
import os

from flask import abort, current_app, flash, jsonify, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required
from sqlalchemy import or_
from sqlalchemy.orm import joinedload

from database.models import (
    Ingredient,
    Instruction,
    Recipe,
    RecipeCollection,
    RecipeDiet,
    RecipeIngredient,
    RecipeMealType,
    UserRecipeInteraction,
    db,
)
from routes._flat import FlatBlueprint
from routes._shared import get_recipe_image_url, get_storage, load_json_option
from utils.decorators import admin_required

recipes_bp = FlatBlueprint("recipes", __name__)


@recipes_bp.route('/')
def discover():
    # Load Recent Recipes (approved only)
    recent_recipes = db.session.execute(db.select(Recipe).where(Recipe.status == 'approved').order_by(Recipe.id.desc()).limit(8)).scalars().all()
    
    resources = load_resources()
    active_template = session.get('active_card_template', 'original')
    return render_template('landing.html', recipes=recent_recipes, resources=resources, active_template=active_template)

def load_resources():
    try:
        data_dir = os.path.join(current_app.root_path, 'data')
        with open(os.path.join(data_dir, 'resources.json'), 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading resources: {e}")
        return []




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
    
    # Meal Types (Dict of Lists -> Flattened List)
    mt_data = load_json_option('constraints/meal_types.json', 'meal_classification')
    meal_type_options = []
    if isinstance(mt_data, dict):
        for category_list in mt_data.values():
            if isinstance(category_list, list):
                meal_type_options.extend(category_list)
    meal_type_options = sorted(list(set(meal_type_options)))

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
            clauses.append(Recipe.ingredients.any(
                RecipeIngredient.ingredient.has(Ingredient.name.ilike(f'%{p}%'))
            ))
        if clauses:
             stmt = stmt.where(or_(*clauses))

    if selected_meal_types and len(selected_meal_types) < len(meal_type_options):
        stmt = stmt.where(Recipe.meal_types.any(RecipeMealType.meal_type.in_(selected_meal_types)))

    # Fetch results
    results = db.session.execute(stmt).all()
    
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
                         selected_proteins=selected_proteins)


@recipes_bp.route('/api/recipe/<int:recipe_id>', methods=['GET'])
@login_required
def get_recipe_json(recipe_id):
    if not current_user.is_admin:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
    recipe = db.session.get(Recipe, recipe_id)
    if not recipe:
        return jsonify({'success': False, 'error': 'Recipe not found'}), 404
        
    try:
        # Construct JSON
        data = {
            'id': recipe.id,
            'title': recipe.title,
            'cuisine': recipe.cuisine,
            'diets': recipe.diets_list,
            'difficulty': recipe.difficulty,
            'protein_type': recipe.protein_type,
            'meal_types': recipe.meal_types_list,
            'chef_id': recipe.chef_id or 'gourmet',
            'taste_level': recipe.taste_level,
            'prep_time_mins': recipe.prep_time_mins,
            'cleanup_factor': recipe.cleanup_factor,
            'image_filename': recipe.image_filename,
            'nutrition': {
                'calories': recipe.total_calories,
                'protein': recipe.total_protein,
                'carbs': recipe.total_carbs,
                'fat': recipe.total_fat,
                'sugar': recipe.total_sugar,
                'fiber': recipe.total_fiber
            },
            'ingredients': [],
            'instructions': []
        }
        
        # Serialize Ingredients
        for ri in recipe.ingredients:
            data['ingredients'].append({
                'id': ri.id,
                'name': ri.ingredient.name,
                'prep_style': ri.prep_style,
                'amount': ri.amount,
                'unit': ri.unit,
                'gram_weight': ri.gram_weight,
                'component': ri.component,
                'food_id': ri.ingredient.food_id,
                'category': ri.ingredient.main_category
            })
            
        # Serialize Instructions
        sorted_instructions = sorted(recipe.instructions, key=lambda x: x.step_number)
        for step in sorted_instructions:
            data['instructions'].append({
                'step': step.step_number,
                'phase': step.phase,
                'text': step.text,
                'component': step.component
            })
            
        return jsonify({'success': True, 'recipe': data})
        
    except Exception as e:
        print(f"Error serializing recipe {recipe_id}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@recipes_bp.route('/api/sub-recipe/<int:recipe_id>', methods=['GET'])
def get_sub_recipe(recipe_id):
    """Public read-only endpoint for the sub-recipe modal viewer.
    Returns only approved recipes (or any recipe whose id is referenced as
    a sub_recipe_id — admin may link draft sub-recipes intentionally)."""
    recipe = db.session.get(Recipe, recipe_id)
    if not recipe:
        return jsonify({'success': False, 'error': 'Sub-recipe not found'}), 404

    # Build image URL helper (reuse existing context function)
    image_url = get_recipe_image_url(recipe) if recipe.image_filename else None

    # Ingredients grouped by component
    components: dict[str, list] = {}
    for ri in recipe.ingredients:
        comp = ri.component or 'Main'
        if comp not in components:
            components[comp] = []
        components[comp].append({
            'name': ri.ingredient.name,
            'amount': ri.amount,
            'unit': ri.unit,
            'gram_weight': ri.gram_weight,
            'image_url': ri.ingredient.image_url or None,
        })

    # Instructions grouped by component, sorted by step_number
    steps_by_comp: dict[str, list] = {}
    sorted_steps = sorted(recipe.instructions, key=lambda s: (s.component or '', s.step_number))
    for step in sorted_steps:
        comp = step.component or 'Main'
        if comp not in steps_by_comp:
            steps_by_comp[comp] = []
        steps_by_comp[comp].append({
            'step': step.step_number,
            'phase': step.phase,
            'text': step.text,
        })

    return jsonify({
        'success': True,
        'recipe': {
            'id': recipe.id,
            'title': recipe.title,
            'cuisine': recipe.cuisine,
            'image_url': image_url,
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
    if not recipe:
        flash("Recipe not found.", "error")
        return redirect(url_for('discover'))
    
    # Group instructions by phase for display
    instructions = Instruction.query.filter_by(recipe_id=recipe_id).order_by(Instruction.component, Instruction.phase, Instruction.step_number).all()
    
    steps_by_phase = {
        'Prep': [i for i in instructions if i.phase == 'Prep'],
        'Cook': [i for i in instructions if i.phase == 'Cook'],
        'Serve': [i for i in instructions if i.phase == 'Serve']
    }
    
    # NEW: Group instructions by component for multi-component display
    from itertools import groupby
    steps_by_component = []
    for component_name, steps in groupby(instructions, key=lambda x: x.component):
        steps_by_component.append((component_name, list(steps)))
    
    # Group ingredients by component
    ingredients_by_component = {}
    for recipe_ing in recipe.ingredients:
        comp = recipe_ing.component
        if comp not in ingredients_by_component:
            ingredients_by_component[comp] = []
        ingredients_by_component[comp].append(recipe_ing)
    
    # DEFENSIVE: Reconcile mismatched component names
    # If ingredient components don't match instruction components,
    # ingredients become invisible in the template. Fix by redistributing.
    instruction_comp_names = {name for name, _ in steps_by_component}
    ingredient_comp_names = set(ingredients_by_component.keys())
    orphaned_comps = ingredient_comp_names - instruction_comp_names
    
    if orphaned_comps:
        print(f"⚠️  Component name mismatch for recipe {recipe_id}:")
        print(f"   Instruction components: {instruction_comp_names}")
        print(f"   Ingredient components:  {ingredient_comp_names}")
        print(f"   Orphaned:               {orphaned_comps}")
        
        # Collect all orphaned ingredients
        orphaned_ingredients = []
        for comp in orphaned_comps:
            orphaned_ingredients.extend(ingredients_by_component.pop(comp))
        
        if len(steps_by_component) == 1:
            comp_names = [name for name, _ in steps_by_component]
            ingredients_by_component[comp_names[0]] = orphaned_ingredients
        elif len(steps_by_component) > 1:
            comp_names = [name for name, _ in steps_by_component]
            per_comp = max(1, len(orphaned_ingredients) // len(comp_names))
            for idx, comp_name in enumerate(comp_names):
                start = idx * per_comp
                end = start + per_comp if idx < len(comp_names) - 1 else len(orphaned_ingredients)
                ingredients_by_component[comp_name] = orphaned_ingredients[start:end]
        else:
            # Some matched, some didn't — attach orphans to "Other Ingredients"
            ingredients_by_component["Other Ingredients"] = orphaned_ingredients
            # Also add a pseudo-component for display if not already in steps
            if not any(name == "Other Ingredients" for name, _ in steps_by_component):
                steps_by_component.append(("Other Ingredients", []))
    # NEW: Chronological Sequence (Parallel Dashboard)
    has_chronological_data = False
    chrono_steps = []
    component_meta = {}
    
    if len(instructions) > 0:
        has_chronological_data = all(i.global_order_index is not None for i in instructions)
        if has_chronological_data:
            chrono_steps = sorted(instructions, key=lambda x: x.global_order_index)
            
            # Phase 1: Backend metadata for sandbox Views
            unique_components = []
            for step in chrono_steps:
                if step.component not in unique_components:
                    unique_components.append(step.component)
                    
            themes = [
                {'color': 'bg-blue-50 text-blue-800', 'border': 'border-blue-200', 'indent': 'ml-0 md:ml-0'},
                {'color': 'bg-rose-50 text-rose-800', 'border': 'border-rose-200', 'indent': 'ml-4 md:ml-12'},
                {'color': 'bg-emerald-50 text-emerald-800', 'border': 'border-emerald-200', 'indent': 'ml-8 md:ml-24'},
                {'color': 'bg-amber-50 text-amber-800', 'border': 'border-amber-200', 'indent': 'ml-12 md:ml-36'},
                {'color': 'bg-purple-50 text-purple-800', 'border': 'border-purple-200', 'indent': 'ml-16 md:ml-48'},
            ]
            
            for index, comp in enumerate(unique_components):
                if index < len(themes):
                    component_meta[comp] = themes[index]
                else:
                    component_meta[comp] = themes[-1]

    # ------------------------------------------------------------------ #
    # SMART SUBSTITUTION ENGINE                                            #
    # For each ingredient that has a sub_category, find up to 3 alts from #
    # the same sub_category (excluding itself), sorted staples-first.     #
    # Also ask Gemini for a one-sentence Chef's Tip per ingredient.       #
    # ------------------------------------------------------------------ #
    substitutes: dict[int, dict] = {}  # keyed by RecipeIngredient.id

    for ri in recipe.ingredients:
        ing = ri.ingredient
        if not ing or not ing.sub_category:
            continue

        alts = db.session.execute(
            db.select(Ingredient)
            .where(
                Ingredient.sub_category == ing.sub_category,
                Ingredient.id != ing.id,
                Ingredient.status == 'active',
            )
            .order_by(Ingredient.is_staple.desc(), Ingredient.name.asc())
            .limit(3)
        ).scalars().all()

        if not alts:
            continue

        # Ask Gemini for a Chef's Tip — keep it cheap: single sentence, flash model
        chef_tip = ""
        try:
            from ai_engine import client as ai_client
            tip_prompt = (
                f"Give a single short sentence (max 20 words) chef's tip about substituting "
                f"{ing.name} in a {recipe.title} recipe. Be practical and specific."
            )
            tip_resp = ai_client.models.generate_content(
                model='gemini-2.0-flash-lite',
                contents=tip_prompt,
            )
            chef_tip = tip_resp.text.strip().rstrip('.')
        except Exception:
            pass  # Tip is non-critical; silently skip on error

        substitutes[ri.id] = {
            'original': ing,
            'alts': alts,
            'tip': chef_tip,
        }

    # Load current user's interaction for the feedback drawer
    user_interaction = None
    if current_user.is_authenticated:
        user_interaction = db.session.execute(
            db.select(UserRecipeInteraction).where(
                UserRecipeInteraction.user_id == current_user.id,
                UserRecipeInteraction.recipe_id == recipe_id,
            )
        ).scalars().first()

    # Check if any ingredient already points to this recipe as a sub-recipe
    linked_ingredient = db.session.execute(
        db.select(Ingredient).where(Ingredient.sub_recipe_id == recipe_id)
    ).scalars().first()

    return render_template('recipe.html',
                            recipe=recipe,
                            steps_by_phase=steps_by_phase,
                            ingredients_by_component=ingredients_by_component,
                            steps_by_component=steps_by_component,
                            has_chronological_data=has_chronological_data,
                            chrono_steps=chrono_steps,
                            component_meta=component_meta,
                            substitutes=substitutes,
                            user_interaction=user_interaction,
                            linked_ingredient=linked_ingredient)

@recipes_bp.route('/recipe/<int:recipe_id>/swap-image', methods=['POST'])
@login_required
@admin_required
def swap_recipe_image(recipe_id):
    """Swaps the AI generated image with the source video thumbnail (if available)."""
    recipe = db.session.get(Recipe, recipe_id)
    if not recipe or not recipe.source_image_filename:
        return jsonify({"success": False, "error": "No source thumbnail available for this recipe."}), 400
        
    temp = recipe.image_filename
    recipe.image_filename = recipe.source_image_filename
    recipe.source_image_filename = temp
    db.session.commit()
    
    return jsonify({"success": True, "new_image": get_recipe_image_url(recipe)})


@recipes_bp.route('/recipe/<int:recipe_id>/kitchen')
def recipe_kitchen_mode(recipe_id):
    """A highly isolated, 1-screen landscape view for cooking on tablets."""
    query = db.select(Recipe).where(Recipe.id == recipe_id).options(
        joinedload(Recipe.ingredients).joinedload(RecipeIngredient.ingredient),
        joinedload(Recipe.instructions)
    )
    recipe = db.session.execute(query).unique().scalar_one_or_none()

    if not recipe:
        flash("Recipe not found.", "error")
        return redirect(url_for('index'))

    return render_template('kitchen_mode.html', recipe=recipe)

@recipes_bp.route('/api/recipe/<int:recipe_id>/generate-components', methods=['POST'])
@login_required
@admin_required
def generate_component_images(recipe_id):
    recipe = db.session.get(Recipe, recipe_id)
    if not recipe:
        return jsonify({'success': False, 'error': 'Recipe not found'}), 404
        
    try:
        from io import BytesIO
        import uuid
        
        # Ensure dictionary exists
        if recipe.component_images is None:
            recipe.component_images = {}
            
        new_images = dict(recipe.component_images)
        components = {i.component for i in recipe.instructions if i.component}
        
        from services.photographer_service import generate_actual_image
        
        generated_count = 0
        for comp in components:
            if comp not in new_images:
                prompt_text = f"A clean, minimalist 4k product photo of just {comp} alone, explicitly isolated on a pure solid white background. Strictly NO other components, NO distracting plates or utensils, NO background clutter, highly appetizing."
                try:
                    images = generate_actual_image(prompt_text, number_of_images=1)
                    if images and len(images) > 0:
                        img = images[0]
                        filename = f"comp_{recipe_id}_{uuid.uuid4().hex[:8]}.png"
                        
                        img_byte_arr = BytesIO()
                        img.save(img_byte_arr, format='PNG')
                        
                        # Save directly to recipes folder
                        get_storage().save(img_byte_arr.getvalue(), filename, "recipes")
                        
                        new_images[comp] = filename
                        generated_count += 1
                except Exception as e:
                    print(f"Failed to generate image for component {comp}: {e}")
                    
        if generated_count > 0:
            recipe.component_images = new_images
            from sqlalchemy.orm.attributes import flag_modified
            flag_modified(recipe, "component_images")
            db.session.commit()
            
        return jsonify({'success': True, 'generated': generated_count})
        
    except Exception as e:
        print(f"Gen Error in generate-components: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


# ---------------------------------------------------------------------------
# Public Collection Routes
# ---------------------------------------------------------------------------

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
