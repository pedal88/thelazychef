"""Admin Blueprint: Ingredients Management Dashboard."""
from __future__ import annotations

from flask import Blueprint, abort, jsonify, render_template, request
from flask_login import login_required

from database.models import Ingredient, IngredientEvaluation, RecipeIngredient, db
from services.storage_service import get_storage_provider
from services.vertex_image_service import VertexImageGenerator
from utils.decorators import admin_required
import os

ingredients_bp = Blueprint(
    "ingredients_mgmt",
    __name__,
    url_prefix="/admin/ingredients-management",
)

VALID_STATUSES = {"active", "inactive", "pending"}

# ---------------------------------------------------------------------------
# HTML Page
# ---------------------------------------------------------------------------

@ingredients_bp.route("/", methods=["GET"])
@login_required
@admin_required
def dashboard() -> str:
    """Paginated ingredients management table with column-level filters."""
    from sqlalchemy import distinct, true

    page = request.args.get("page", 1, type=int)
    per_page = 50

    # ── Collect active filter selections from query string ──────────
    selected_statuses      = request.args.getlist("status")
    selected_categories    = request.args.getlist("category")
    selected_sub_cats      = request.args.getlist("sub_category")
    selected_basic         = request.args.getlist("basic")   # "yes" | "no"
    missing_images         = request.args.get("missing_images", "0") == "1"

    # ── Build query ─────────────────────────────────────────────────
    stmt = db.select(Ingredient).order_by(Ingredient.main_category, Ingredient.name)

    if selected_statuses:
        stmt = stmt.where(Ingredient.status.in_(selected_statuses))

    if selected_categories:
        stmt = stmt.where(Ingredient.main_category.in_(selected_categories))

    if selected_sub_cats:
        stmt = stmt.where(Ingredient.sub_category.in_(selected_sub_cats))

    if selected_basic:
        if "yes" in selected_basic and "no" not in selected_basic:
            stmt = stmt.where(Ingredient.is_staple == True)
        elif "no" in selected_basic and "yes" not in selected_basic:
            stmt = stmt.where(Ingredient.is_staple == False)

    if missing_images:
        stmt = stmt.where(
            (Ingredient.image_url == None) | (Ingredient.image_url == "")
        )

    pagination = db.paginate(stmt, page=page, per_page=per_page, error_out=False)

    # ── Fetch distinct values for filter menus ──────────────────────
    category_options = sorted(filter(None, [
        r[0] for r in db.session.execute(
            db.select(distinct(Ingredient.main_category))
        ).all()
    ]))
    sub_category_options = sorted(filter(None, [
        r[0] for r in db.session.execute(
            db.select(distinct(Ingredient.sub_category))
        ).all()
    ]))

    return render_template(
        "admin/ingredients_management.html",
        ingredients=pagination.items,
        pagination=pagination,
        # filter options
        category_options=category_options,
        sub_category_options=sub_category_options,
        # selected states (to pre-tick checkboxes)
        selected_statuses=selected_statuses,
        selected_categories=selected_categories,
        selected_sub_cats=selected_sub_cats,
        selected_basic=selected_basic,
        missing_images=missing_images,
    )


# ---------------------------------------------------------------------------
# JSON API
# ---------------------------------------------------------------------------

@ingredients_bp.route("/api/<int:ing_id>/status", methods=["POST"])
@login_required
@admin_required
def update_status(ing_id: int):
    """Toggle ingredient between active / inactive / pending."""
    data = request.get_json(silent=True) or {}
    new_status = data.get("status", "").strip().lower()

    if new_status not in VALID_STATUSES:
        return jsonify({"success": False, "error": f"Invalid status. Must be one of: {VALID_STATUSES}"}), 400

    ing = db.session.get(Ingredient, ing_id)
    if not ing:
        return jsonify({"success": False, "error": "Ingredient not found"}), 404

    ing.status = new_status
    db.session.commit()
    return jsonify({"success": True, "new_status": ing.status})


@ingredients_bp.route("/api/<int:ing_id>", methods=["DELETE"])
@login_required
@admin_required
def delete_ingredient(ing_id: int):
    """
    Smart delete:
    - If ingredient is linked to ≥1 recipe  → set status='inactive' (archive).
    - If ingredient is unused               → hard delete from DB.
    """
    ing = db.session.get(Ingredient, ing_id)
    if not ing:
        return jsonify({"success": False, "error": "Ingredient not found"}), 404

    # Check for any recipe linkage
    linked_count: int = db.session.execute(
        db.select(db.func.count(RecipeIngredient.id)).where(
            RecipeIngredient.ingredient_id == ing_id
        )
    ).scalar_one()

    if linked_count > 0:
        # Safe archive — do not destroy FK relationships
        ing.status = "inactive"
        db.session.commit()
        return jsonify({
            "success": True,
            "action": "archived",
            "message": f"Ingredient is used in {linked_count} recipe(s) — archived as 'inactive' instead of deleted.",
            "new_status": "inactive",
        })

    # Truly unused — safe to hard delete
    db.session.delete(ing)
    db.session.commit()
    return jsonify({"success": True, "action": "deleted"})


@ingredients_bp.route("/api/<int:ing_id>/inspect", methods=["GET"])
@login_required
@admin_required
def inspect_ingredient(ing_id: int):
    """Return raw ingredient data as JSON for the debug inspector modal."""
    ing = db.session.get(Ingredient, ing_id)
    if not ing:
        return jsonify({"success": False, "error": "Ingredient not found"}), 404

    # Count recipes using this ingredient
    recipe_count: int = db.session.execute(
        db.select(db.func.count(RecipeIngredient.id)).where(
            RecipeIngredient.ingredient_id == ing_id
        )
    ).scalar_one()

    return jsonify({
        "success": True,
        "ingredient": {
            "id": ing.id,
            "food_id": ing.food_id,
            "name": ing.name,
            "status": ing.status,
            "main_category": ing.main_category,
            "sub_category": ing.sub_category,
            "default_unit": ing.default_unit,
            "average_g_per_unit": ing.average_g_per_unit,
            "is_staple": ing.is_staple,
            "image_url": ing.image_url,
            "image_prompt": ing.image_prompt,
            "aliases": ing.aliases,
            "calories_per_100g": ing.calories_per_100g,
            "protein_per_100g": ing.protein_per_100g,
            "carbs_per_100g": ing.carbs_per_100g,
            "fat_per_100g": ing.fat_per_100g,
            "fiber_per_100g": ing.fiber_per_100g,
            "sugar_per_100g": ing.sugar_per_100g,
            "sodium_mg_per_100g": ing.sodium_mg_per_100g,
            "recipe_count": recipe_count,
        },
    })


@ingredients_bp.route("/api/<int:ing_id>/regenerate-image", methods=["POST"])
@login_required
@admin_required
def regenerate_image(ing_id: int):
    """Trigger Vertex AI image generation and persist the result to the ingredient record."""
    from flask import current_app
    ing = db.session.get(Ingredient, ing_id)
    if not ing:
        return jsonify({"success": False, "error": "Ingredient not found"}), 404

    prompt = ing.image_prompt or f"A professional studio food photography shot of {ing.name}, isolated on a white background, clean and appetising."

    storage_provider = get_storage_provider()
    generator = VertexImageGenerator(
        storage_provider=storage_provider,
        root_path=current_app.root_path,
    )

    result = generator.generate_candidate(ingredient_name=ing.name, prompt=prompt)

    if result.get("success"):
        # Persist the new URL directly to the ingredient record
        ing.image_url = result["image_url"]
        db.session.commit()
        return jsonify({"success": True, "image_url": ing.image_url})

    return jsonify({"success": False, "error": result.get("error", "Unknown error")}), 500


@ingredients_bp.route("/api/<int:ing_id>/evaluate", methods=["POST"])
@login_required
@admin_required
def evaluate_ingredient(ing_id: int):
    """Trigger the LLM-as-a-Judge QA pipeline for a single ingredient.

    Returns the total_score and whether the ingredient was auto-promoted from
    'pending' to 'active' (score >= 85).
    """
    # Lazy import avoids circular dependency at module load time
    from services.ingredient_evaluation_service import evaluate_ingredient as run_qa

    ing = db.session.get(Ingredient, ing_id)
    if not ing:
        return jsonify({"success": False, "error": "Ingredient not found"}), 404

    try:
        result = run_qa(ing_id)
        return jsonify({
            "success": True,
            "total_score": result["total_score"],
            "auto_promoted": result["auto_promoted"],
        })
    except ValueError as exc:
        return jsonify({"success": False, "error": str(exc)}), 500

