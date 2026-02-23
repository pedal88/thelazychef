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
    Priority 1: LLM-provided pantry_id (reject IMP-).
    Priority 2: Fuzzy name match via get_pantry_id.
    Returns the Ingredient ORM object or None.
    """
    pre_id = _extract_pre_resolved_id(ing)

    # Priority 1: Pre-resolved ID (reject IMP duplicates)
    if pre_id and not str(pre_id).startswith('IMP-'):
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
                    is_original=False,
                    is_basic_ingredient=False,
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

    # ── Step 3: Create Recipe record ──────────────────────────────────────
    new_recipe = Recipe(
        title=recipe_data.title,
        cuisine=getattr(recipe_data, 'cuisine', None),
        # diet is stored in recipe_diet join table — see Step 4a below
        difficulty=getattr(recipe_data, 'difficulty', None),
        protein_type=getattr(recipe_data, 'protein_type', None),
        chef_id=valid_chef_id,
        taste_level=getattr(recipe_data, 'taste_level', None),
        prep_time_mins=getattr(recipe_data, 'prep_time_mins', None),
        cleanup_factor=getattr(recipe_data, 'cleanup_factor', None) or 3,
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

            db.session.add(RecipeIngredient(
                recipe_id=new_recipe.id,
                ingredient_id=ingredient_record.id,
                amount=amount,
                unit=unit,
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

            db.session.add(Instruction(
                recipe_id=new_recipe.id,
                phase=phase,
                component=comp_name,
                step_number=step_num,
                text=text,
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
