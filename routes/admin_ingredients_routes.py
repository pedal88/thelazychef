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
    search_query           = request.args.get("search", "").strip()
    missing_images         = request.args.get("missing_images", "0") == "1"
    solid_backgrounds      = request.args.get("solid_backgrounds", "0") == "1"

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

    if search_query:
        stmt = stmt.where(Ingredient.name.ilike(f"%{search_query}%"))

    if missing_images:
        stmt = stmt.where(
            (Ingredient.image_url == None) | (Ingredient.image_url == "")
        )
        
    if solid_backgrounds:
        stmt = stmt.where(
            (Ingredient.image_url != None) & (Ingredient.image_url != "") & (Ingredient.has_transparent_image == False)
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
        search_query=search_query,
        missing_images=missing_images,
        solid_backgrounds=solid_backgrounds,
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
            "has_transparent_image": ing.has_transparent_image,
            "image_prompt": ing.image_prompt,
            "aliases": ing.aliases,
            "calories_per_100g": ing.calories_per_100g,
            "protein_per_100g": ing.protein_per_100g,
            "carbs_per_100g": ing.carbs_per_100g,
            "fat_per_100g": ing.fat_per_100g,
            "fiber_per_100g": ing.fiber_per_100g,
            "sugar_per_100g": ing.sugar_per_100g,
            "sodium_mg_per_100g": ing.sodium_mg_per_100g,
            "data_source": ing.data_source,
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

    prompt = ing.image_prompt or f"A professional studio food photography shot of {ing.name}, isolated on a stark white background, brightly lit with absolutely zero drop shadows, clean and appetising."

    storage_provider = get_storage_provider()
    generator = VertexImageGenerator(
        storage_provider=storage_provider,
        root_path=current_app.root_path,
    )

    result = generator.generate_candidate(ingredient_name=ing.name, prompt=prompt)

    if result.get("success"):
        # Persist the new URL directly to the ingredient record
        ing.image_url = result["image_url"]
        if "has_transparent_image" in result:
            ing.has_transparent_image = result["has_transparent_image"]
        db.session.commit()
        return jsonify({"success": True, "image_url": ing.image_url})

    return jsonify({"success": False, "error": result.get("error", "Unknown error")}), 500


@ingredients_bp.route("/api/<int:ing_id>/galaxy")
@login_required
@admin_required
def ingredient_galaxy(ing_id: int):
    """Returns ECharts JSON representing the ingredient's category tree and AI-similar siblings."""
    ing = db.session.get(Ingredient, ing_id)
    if not ing:
        return jsonify({"success": False, "error": "Ingredient not found"}), 404

    nodes = []
    links = []

    # 1. Add Current Ingredient (Large Center Node)
    main_symbol = f"image://{ing.image_url}" if ing.image_url else "circle"
    nodes.append({
        "id": f"ing_{ing.id}",
        "name": ing.name,
        "symbolSize": 50,
        "symbol": main_symbol,
        "category": 0,
        "itemStyle": {"color": "#4f46e5"}, # Fallback Indigo
        "label": {"show": True}
    })

    # 2. Add Category Nodes
    main_cat = ing.main_category or "Uncategorized"
    sub_cat = ing.sub_category or "General"
    
    nodes.append({
        "id": f"main_{main_cat}",
        "name": main_cat.title(),
        "symbolSize": 30,
        "category": 1,
        "itemStyle": {"color": "#4b5563"} # Dark Grey for categories
    })
    links.append({"source": f"ing_{ing.id}", "target": f"main_{main_cat}"})

    if main_cat != sub_cat:
        nodes.append({
            "id": f"sub_{sub_cat}",
            "name": sub_cat.title(),
            "symbolSize": 25,
            "category": 1,
            "itemStyle": {"color": "#9ca3af"} # Light Grey for sub-categories
        })
        links.append({"source": f"main_{main_cat}", "target": f"sub_{sub_cat}"})
        links.append({"source": f"ing_{ing.id}", "target": f"sub_{sub_cat}"})

    # 3. Add AI-Similar Integrations via Postgres pgvector (if embedding exists)
    if ing.embedding is not None:
        similar_ings = db.session.execute(
            db.select(Ingredient)
            .where(Ingredient.id != ing.id)
            .where(Ingredient.embedding != None)
            .order_by(Ingredient.embedding.cosine_distance(ing.embedding))
            .limit(5)
        ).scalars().all()

        for sim_ing in similar_ings:
            node_id = f"sim_{sim_ing.id}"
            sim_symbol = f"image://{sim_ing.image_url}" if sim_ing.image_url else "circle"
            nodes.append({
                "id": node_id,
                "name": sim_ing.name,
                "symbolSize": 35,
                "symbol": sim_symbol,
                "category": 2,
                "itemStyle": {"color": "#10b981"} # Fallback emerald
            })
            links.append({"source": f"ing_{ing.id}", "target": node_id, "lineStyle": {"type": "dashed"}})

    return jsonify({"success": True, "nodes": nodes, "links": links})


@ingredients_bp.route("/api/<int:ing_id>/strip-background", methods=["POST"])
@login_required
@admin_required
def strip_background(ing_id: int):
    """Downloads existing image, runs rembg, re-uploads, saves to db."""
    import requests
    import time
    from PIL import Image
    from io import BytesIO
    from rembg import remove
    from werkzeug.utils import secure_filename
    from services.storage_service import get_storage_provider

    ing = db.session.get(Ingredient, ing_id)
    if not ing or not ing.image_url:
        return jsonify({"success": False, "error": "Ingredient or image not found"}), 404

    # Handle legacy relative paths if any exist
    url = ing.image_url
    if not url.startswith('http'):
        url = f"https://storage.googleapis.com/thelazychef-assets/{url}"

    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200:
            return jsonify({"success": False, "error": "Could not download existing image"}), 400

        # Run rembg on the byte stream
        raw_bytes = resp.content
        out_bytes = remove(raw_bytes)
        
        # Convert to PNG to keep transparency
        img = Image.open(BytesIO(out_bytes))
        final_buf = BytesIO()
        img.save(final_buf, format="PNG")
        final_png = final_buf.getvalue()

        # Build new filename to bust cache
        ts = int(time.time())
        import re
        safe_name = re.sub(r'[^a-zA-Z0-9]', '_', ing.name.lower())
        safe_name = re.sub(r'_+', '_', safe_name).strip('_')
        filename = f"{safe_name}_{ts}.png"

        # Upload
        provider = get_storage_provider()
        public_url = provider.save(final_png, filename, "pantry/candidates")

        # Save to DB
        ing.image_url = public_url
        ing.has_transparent_image = True
        db.session.commit()

        return jsonify({"success": True, "image_url": public_url})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@ingredients_bp.route("/merge", methods=["GET"])
@login_required
@admin_required
def merge_ingredient_tool():
    """Render the standalone tool for merging duplicate ingredients."""
    return render_template('admin/ingredient_merge_tool.html')

@ingredients_bp.route("/api/<int:ing_id>/evaluate", methods=["POST"])
@login_required
@admin_required
def evaluate_ingredient(ing_id: int):
    """Trigger the LLM-as-a-Judge QA pipeline for a single ingredient.
    
    Returns the total_score of the evaluation.
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


@ingredients_bp.route("/api/unscored_ids", methods=["GET"])
@login_required
@admin_required
def get_unscored_ids():
    """Return a list of ingredient IDs that have no evaluation record."""
    from database.models import IngredientEvaluation
    
    # Select ingredients that don't have an evaluation record
    stmt = db.select(Ingredient.id).outerjoin(IngredientEvaluation).where(IngredientEvaluation.id == None)
    
    unscored = db.session.execute(stmt).scalars().all()
    
    return jsonify({
        "success": True,
        "unscored_ids": unscored
    })
