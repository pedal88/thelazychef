"""
Recipe Service — Unified persistence pipeline for all recipe generation vectors.

Every generation route (Idea, Web, Video) calls process_recipe_workflow()
with the AI-produced RecipeObj.  This module owns:
  • Ingredient validation (strict — never auto-creates)
  • DB persistence (Recipe, RecipeMealType, RecipeIngredient, Instruction)
  • Post-processing (nutrition, standardized AI image generation)
"""

import os
import uuid
import json

from database.models import (
    db, Recipe, RecipeIngredient, RecipeMealType, RecipeDiet,
    Instruction, Ingredient, Chef
)
from ai_engine import get_pantry_id
from services.nutrition_service import calculate_nutritional_totals
from utils.unit_helpers import normalize_unit
from services.photographer_service import generate_visual_prompt, generate_actual_image


# ---------------------------------------------------------------------------
# Return contract
# ---------------------------------------------------------------------------
STATUS_SUCCESS = "SUCCESS"
STATUS_MISSING = "MISSING_INGREDIENTS"


def _extract_pre_resolved_id(ing) -> str | None:
    """Safely extract the LLM-provided pantry_id from an ingredient object."""
    if hasattr(ing, 'pantry_id'):
        return getattr(ing, 'pantry_id', None)
    if isinstance(ing, dict):
        return ing.get('pantry_id')
    return None


def _resolve_ingredient(ing) -> Ingredient | None:
    """
    Try to resolve an ingredient to a DB record.
    Priority 1: LLM-provided pantry_id.
    Priority 2: Fuzzy name match via get_pantry_id.
    Returns the Ingredient ORM object or None.
    """
    pre_id = _extract_pre_resolved_id(ing)

    # Priority 1: Pre-resolved ID (must exist in DB)
    if pre_id:
        record = db.session.execute(
            db.select(Ingredient).where(Ingredient.food_id == pre_id)
        ).scalars().first()
        if record:
            return record

    # Priority 2: Fuzzy match by name
    name = ing.name if hasattr(ing, 'name') else ing.get('name', '')
    food_id = get_pantry_id(name)
    if food_id:
        record = db.session.execute(
            db.select(Ingredient).where(Ingredient.food_id == food_id)
        ).scalars().first()
        if record:
            return record

    return None


def sanitize_ai_ingredients(recipe_data) -> None:
    """
    Interrogates the AI payload and deterministically forcibly overwrites matched
    basic utility ingredients (e.g. 'salt', 'water') with their exact database 
    'food_id' constants to prevent lexical drift or LLM hallucination mapping.
    Modifies recipe_data in place.
    """
    # Dynamically fetch map of all basic ingredients from DB
    basics_stmt = db.select(Ingredient.name, Ingredient.food_id).where(Ingredient.is_staple == True)
    basics_results = db.session.execute(basics_stmt).all()
    basic_overrides = {row.name.strip().lower(): row.food_id for row in basics_results if row.name}

    # Add manual synonym aliases for common utilities that cause Lexical Drift
    if 'water' in basic_overrides:
        water_id = basic_overrides['water']
        for w in ['hot water', 'cold water', 'boiling water', 'warm water', 'pasta water', 'ice water', 'tap water']:
            basic_overrides[w] = water_id
            
    if 'salt' in basic_overrides:
        salt_id = basic_overrides['salt']
        for s in ['sea salt', 'kosher salt', 'table salt', 'flaky sea salt', 'pinch of salt']:
            basic_overrides[s] = salt_id

    if 'black pepper' in basic_overrides:
        bp_id = basic_overrides['black pepper']
        for p in ['pepper', 'ground black pepper', 'freshly ground black pepper', 'cracked black pepper']:
            basic_overrides[p] = bp_id

    if not basic_overrides:
        return

    for group in getattr(recipe_data, 'ingredient_groups', []):
        for ing in getattr(group, 'ingredients', []):
            name = ing.name.strip().lower() if hasattr(ing, 'name') else ing.get('name', '').strip().lower()
            if name in basic_overrides:
                correct_id = basic_overrides[name]
                if hasattr(ing, 'pantry_id'):
                    ing.pantry_id = correct_id
                elif isinstance(ing, dict):
                    ing['pantry_id'] = correct_id
                else:
                    setattr(ing, 'pantry_id', correct_id)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------
def process_recipe_workflow(recipe_data, query_context: str, chef_id: str) -> dict:
    """
    Unified recipe persistence pipeline.

    Args:
        recipe_data:    RecipeObj returned by any AI generation function.
        query_context:  Original query/URL/caption — used as context for the
                        missing-ingredients resolution page and image prompt.
        chef_id:        Chef persona ID to assign (validated against DB).

    Returns:
        dict with:
            status:  STATUS_SUCCESS | STATUS_MISSING
            recipe_id:  (int) — only when status == SUCCESS
            missing_ingredients:  (list[dict]) — only when status == MISSING
    """

    # ── Step 0: Sanitize Lexical Drift ────────────────────────────────────
    sanitize_ai_ingredients(recipe_data)

    # ── Step 1: Pre-resolve and create missing ingredients ────────────────
    import datetime

    for group in recipe_data.ingredient_groups:
        for ing in group.ingredients:
            record = _resolve_ingredient(ing)
            if not record:
                name = ing.name if hasattr(ing, 'name') else ing.get('name', 'Unknown')
                
                # Create pending ingredient gracefully
                new_food_id = f"pending-{uuid.uuid4().hex[:8]}"
                record = Ingredient(
                    food_id=new_food_id,
                    name=name,
                    status='pending',
                    is_staple=False,
                    default_unit='g',
                    calories_per_100g=0,
                    kj_per_100g=0,
                    protein_per_100g=0,
                    carbs_per_100g=0,
                    fat_per_100g=0,
                    fat_saturated_per_100g=0,
                    sugar_per_100g=0,
                    fiber_per_100g=0,
                    sodium_mg_per_100g=0,
                    created_at=datetime.datetime.utcnow().isoformat()
                )
                db.session.add(record)
                db.session.flush()
                
                # Attach to 'ing' so Step 5 finds it easily
                if hasattr(ing, 'pantry_id'):
                    ing.pantry_id = new_food_id
                elif isinstance(ing, dict):
                    ing['pantry_id'] = new_food_id
                else:
                    setattr(ing, 'pantry_id', new_food_id)

    # ── Step 2: Validate Chef ID ──────────────────────────────────────────
    valid_chef_id = None
    target_chef = getattr(recipe_data, 'chef_id', None) or chef_id
    if target_chef:
        if db.session.get(Chef, target_chef):
            valid_chef_id = target_chef
        elif db.session.get(Chef, 'gourmet'):
            print(f"⚠️  Chef '{target_chef}' not found — falling back to 'gourmet'")
            valid_chef_id = 'gourmet'

    # ── Step 3: Source Tracking Sniffing ──────────────────────────────────
    source_type = 'description'
    query_lower = (query_context or '').lower()
    if 'tiktok.com' in query_lower or 'instagram.com' in query_lower:
        source_type = 'social'
    elif query_lower.startswith('http'):
        source_type = 'web'

    # ── Step 4: Create Recipe record ──────────────────────────────────────
    new_recipe = Recipe(
        title=recipe_data.title,
        cuisine=getattr(recipe_data, 'cuisine', None),
        # diet is stored in recipe_diet join table — see Step 4a below
        difficulty=getattr(recipe_data, 'difficulty', None),
        protein_type=getattr(recipe_data, 'protein_type', None),
        chef_id=valid_chef_id,
        base_servings=getattr(recipe_data, 'servings', 4) if getattr(recipe_data, 'servings', None) is not None else recipe_data.get('servings', 4) if isinstance(recipe_data, dict) else 4,
        taste_level=getattr(recipe_data, 'taste_level', None),
        prep_time_mins=getattr(recipe_data, 'prep_time_mins', None),
        cleanup_factor=getattr(recipe_data, 'cleanup_factor', None) or 3,
        source_input=(query_context or '')[:500],
        source_type=source_type,
    )
    db.session.add(new_recipe)
    db.session.flush()  # get new_recipe.id

    # ── Step 4: Save Meal Types ───────────────────────────────────────────
    meal_types = getattr(recipe_data, 'meal_types', None)
    if meal_types:
        for mt in meal_types:
            db.session.add(RecipeMealType(recipe_id=new_recipe.id, meal_type=mt))

    # ── Step 4a: Save Diets ─────────────────────────────────────────────────
    raw_diets = getattr(recipe_data, 'diet', None)
    if raw_diets:
        # Normalise: the AI should return a list, but guard against a legacy string
        diet_list: list[str] = raw_diets if isinstance(raw_diets, list) else [raw_diets]
        for d in diet_list:
            db.session.add(RecipeDiet(recipe_id=new_recipe.id, diet=d))

    # ── Step 5: Save Ingredients (all validated — no auto-creation) ───────
    for group in recipe_data.ingredient_groups:
        for ing in group.ingredients:
            ingredient_record = _resolve_ingredient(ing)
            if not ingredient_record:
                # Should never happen — we validated above
                raise ValueError(
                    f"System error: Ingredient '{getattr(ing, 'name', ing)}' "
                    f"passed validation but not found in DB."
                )

            amount = ing.amount if hasattr(ing, 'amount') else ing.get('amount', 0)
            unit = ing.unit if hasattr(ing, 'unit') else ing.get('unit', '')
            component = group.component if hasattr(group, 'component') else group.get('component', 'Main Dish')
            
            # Smart Fallback: AI Estimate vs Physics Override
            ai_gram_estimate = float(ing.get('gram_weight_estimate', 0.0)) if isinstance(ing, dict) else float(getattr(ing, 'gram_weight_estimate', 0.0))
            final_gram_weight = ai_gram_estimate
            
            # Rule A: The Override
            if ingredient_record.average_g_per_unit and ingredient_record.default_unit:
                if normalize_unit(str(unit)) == normalize_unit(str(ingredient_record.default_unit)):
                     final_gram_weight = float(amount) * float(ingredient_record.average_g_per_unit)

            db.session.add(RecipeIngredient(
                recipe_id=new_recipe.id,
                ingredient_id=ingredient_record.id,
                amount=amount,
                unit=unit,
                gram_weight=final_gram_weight,
                component=component,
            ))

    # ── Step 6: Save Instructions ─────────────────────────────────────────
    for comp in recipe_data.components:
        comp_name = comp.name if hasattr(comp, 'name') else comp.get('name', 'Main Dish')
        steps = comp.steps if hasattr(comp, 'steps') else comp.get('steps', [])
        for step in steps:
            phase = step.phase if hasattr(step, 'phase') else step.get('phase', 'Prep')
            step_num = step.step_number if hasattr(step, 'step_number') else step.get('step_number', 1)
            text = step.text if hasattr(step, 'text') else step.get('text', '')
            estimated_minutes = step.estimated_minutes if hasattr(step, 'estimated_minutes') else step.get('estimated_minutes', 0)
            global_order_index = step.global_order_index if hasattr(step, 'global_order_index') else step.get('global_order_index', 0)

            db.session.add(Instruction(
                recipe_id=new_recipe.id,
                phase=phase,
                component=comp_name,
                step_number=step_num,
                text=text,
                estimated_minutes=estimated_minutes,
                global_order_index=global_order_index,
            ))

    # ── Step 7: Commit ────────────────────────────────────────────────────
    db.session.commit()

    # ── Step 8: Post-processing (non-blocking) ────────────────────────────
    # 8a. Nutrition
    try:
        calculate_nutritional_totals(new_recipe.id)
    except Exception as e:
        print(f"⚠️  Nutrition calculation failed (non-critical): {e}")

    # 8b. Standardized AI Image Generation
    try:
        print(f"🎨 Auto-generating image for: {recipe_data.title}")
        visual_context = f"{recipe_data.title} - {getattr(recipe_data, 'cuisine', 'International')} cuisine"
        visual_prompt = generate_visual_prompt(visual_context)
        images = generate_actual_image(visual_prompt)

        if images:
            img = images[0]
            unique_suffix = str(uuid.uuid4())[:8]
            filename = f"recipe_{new_recipe.id}_{unique_suffix}.png"

            from io import BytesIO
            buf = BytesIO()
            img.save(buf, 'PNG')
            img_bytes = buf.getvalue()

            from services.storage_service import get_storage_provider
            storage = get_storage_provider()
            storage.save(img_bytes, filename, 'recipes')

            new_recipe.image_filename = filename
            db.session.commit()
            print(f"✅ Image saved: {filename}")

    except Exception as img_err:
        print(f"⚠️  Image generation failed (non-critical): {img_err}")

    return {
        'status': STATUS_SUCCESS,
        'recipe_id': new_recipe.id,
    }

def recalculate_recipe_nutrition(recipe_id: int, db_session) -> None:
    """
    Recalculates macroscopic nutrition properties directly from the gram weight approximations 
    attached to physical RecipeIngredients. Overwrites existing recipe totals in place.
    """
    recipe = db_session.get(Recipe, recipe_id)
    if not recipe:
        return
        
    recipe.total_calories = 0.0
    recipe.total_protein = 0.0
    recipe.total_carbs = 0.0
    recipe.total_fat = 0.0
    recipe.total_saturated_fat = 0.0
    recipe.total_fiber = 0.0
    recipe.total_sugar = 0.0
    recipe.total_cholesterol_mg = 0.0
    recipe.total_sodium_mg = 0.0
    recipe.total_calcium_mg = 0.0
    recipe.total_potassium_mg = 0.0
    
    for r_ing in recipe.ingredients:
        base_item = r_ing.ingredient
        if not base_item or r_ing.gram_weight is None or r_ing.gram_weight <= 0:
            continue
            
        multiplier = r_ing.gram_weight / 100.0
        
        if base_item.calories_per_100g: recipe.total_calories += (base_item.calories_per_100g * multiplier)
        if base_item.protein_per_100g: recipe.total_protein += (base_item.protein_per_100g * multiplier)
        if base_item.carbs_per_100g: recipe.total_carbs += (base_item.carbs_per_100g * multiplier)
        if base_item.fat_per_100g: recipe.total_fat += (base_item.fat_per_100g * multiplier)
        if base_item.fat_saturated_per_100g: recipe.total_saturated_fat += (base_item.fat_saturated_per_100g * multiplier)
        if base_item.fiber_per_100g: recipe.total_fiber += (base_item.fiber_per_100g * multiplier)
        if base_item.sugar_per_100g: recipe.total_sugar += (base_item.sugar_per_100g * multiplier)
        if base_item.cholesterol_mg_per_100g: recipe.total_cholesterol_mg += (base_item.cholesterol_mg_per_100g * multiplier)
        if base_item.sodium_mg_per_100g: recipe.total_sodium_mg += (base_item.sodium_mg_per_100g * multiplier)
        if base_item.calcium_mg_per_100g: recipe.total_calcium_mg += (base_item.calcium_mg_per_100g * multiplier)
        if base_item.potassium_mg_per_100g: recipe.total_potassium_mg += (base_item.potassium_mg_per_100g * multiplier)

    db_session.add(recipe)
    db_session.flush()

def clone_recipe(original_recipe_id: int, new_title: str, ingredient_overrides: dict, db_session) -> int:
    """
    Performs a deep relational clone of a target recipe, including all instructions and ingredients.
    Injects overridden ingredient math into the clone dynamically, allowing Admin tweaks.
    """
    original = db_session.get(Recipe, original_recipe_id)
    if not original:
        raise ValueError(f"Recipe ID {original_recipe_id} not found.")

    # 1. Base Clone
    new_recipe = Recipe(
        title=new_title,
        cuisine=original.cuisine,
        difficulty=original.difficulty,
        protein_type=original.protein_type,
        chef_id=original.chef_id,
        taste_level=original.taste_level,
        prep_time_mins=original.prep_time_mins,
        cleanup_factor=original.cleanup_factor,
        base_servings=original.base_servings,
        image_filename=original.image_filename,
        component_images=original.component_images.copy() if original.component_images else {},
        status='draft' # Always start clones in stealth 
    )
    db_session.add(new_recipe)
    db_session.flush()

    # 2. Join Relationships
    for mt in original.meal_types:
        db_session.add(RecipeMealType(recipe_id=new_recipe.id, meal_type=mt.meal_type))
    for diet in original.diets:
        db_session.add(RecipeDiet(recipe_id=new_recipe.id, diet=diet.diet))

    # 3. Instruction Clones
    for instr in original.instructions:
        db_session.add(Instruction(
            recipe_id=new_recipe.id,
            component=instr.component,
            phase=instr.phase,
            step_number=instr.step_number,
            text=instr.text,
            estimated_minutes=instr.estimated_minutes,
            global_order_index=instr.global_order_index,
        ))

    # 4. Ingredient Clones (With Overrides)
    for r_ing in original.ingredients:
        # Default fallback variables
        target_amt = r_ing.amount
        target_unit = r_ing.unit
        target_gw = r_ing.gram_weight

        override_key = str(r_ing.id)
        if override_key in ingredient_overrides:
            override_obj = ingredient_overrides[override_key]
            
            if 'amount' in override_obj: target_amt = override_obj['amount']
            if 'unit' in override_obj: target_unit = override_obj['unit']
            if 'gram_weight' in override_obj: target_gw = override_obj['gram_weight']

        new_r_ing = RecipeIngredient(
            recipe_id=new_recipe.id,
            ingredient_id=r_ing.ingredient_id,
            component=r_ing.component,
            amount=target_amt,
            unit=target_unit,
            gram_weight=target_gw
        )
        db_session.add(new_r_ing)

    # 5. Flush and Math Trigger
    db_session.flush()
    recalculate_recipe_nutrition(new_recipe.id, db_session)
    db_session.commit()

    return new_recipe.id

