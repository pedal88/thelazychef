"""Admin Blueprint: Curated Collections management + JSON API for the Builder UI."""
from __future__ import annotations

import datetime

from flask import Blueprint, abort, jsonify, redirect, render_template, request, url_for, flash
from flask_login import login_required
from slugify import slugify
from sqlalchemy import or_

from database.models import CollectionItem, Recipe, RecipeCollection, db
from utils.decorators import admin_required

collections_bp = Blueprint("collections", __name__, url_prefix="/admin/collections")


# ---------------------------------------------------------------------------
# HTML Pages
# ---------------------------------------------------------------------------

@collections_bp.route("/", methods=["GET"])
@login_required
@admin_required
def collections_list() -> str:
    """List all collections with quick-links to the builder."""
    collections = (
        db.session.execute(
            db.select(RecipeCollection).order_by(RecipeCollection.created_at.desc())
        )
        .scalars()
        .all()
    )
    return render_template("admin/collections_list.html", collections=collections)


@collections_bp.route("/new", methods=["POST"])
@login_required
@admin_required
def collections_create():
    """Create a blank collection and redirect to the builder."""
    title = request.form.get("title", "").strip()
    if not title:
        flash("Title is required.", "error")
        return redirect(url_for("collections.collections_list"))

    slug = slugify(title)

    # Ensure slug uniqueness
    existing = db.session.execute(
        db.select(RecipeCollection).where(RecipeCollection.slug == slug)
    ).scalar_one_or_none()
    if existing:
        slug = f"{slug}-{datetime.datetime.utcnow().strftime('%Y%m%d%H%M%S')}"

    collection = RecipeCollection(title=title, slug=slug)
    db.session.add(collection)
    db.session.commit()

    flash(f'Collection "{title}" created.', "success")
    return redirect(url_for("collections.collection_builder", collection_id=collection.id))


@collections_bp.route("/<int:collection_id>/builder", methods=["GET"])
@login_required
@admin_required
def collection_builder(collection_id: int) -> str:
    """Render the drag-and-drop collection builder UI."""
    collection = db.session.get(RecipeCollection, collection_id)
    if not collection:
        abort(404)
    return render_template("admin/collection_builder.html", collection=collection)


@collections_bp.route("/<int:collection_id>/update", methods=["POST"])
@login_required
@admin_required
def collection_update(collection_id: int):
    """Update collection metadata (title, description, published state)."""
    collection = db.session.get(RecipeCollection, collection_id)
    if not collection:
        abort(404)

    collection.title = request.form.get("title", collection.title).strip()
    collection.description = request.form.get("description", "").strip() or None
    collection.is_published = request.form.get("is_published") == "on"

    # Re-slug only if title changed substantially
    new_slug = slugify(collection.title)
    if new_slug != collection.slug:
        conflict = db.session.execute(
            db.select(RecipeCollection).where(
                RecipeCollection.slug == new_slug,
                RecipeCollection.id != collection_id,
            )
        ).scalar_one_or_none()
        if not conflict:
            collection.slug = new_slug

    db.session.commit()
    flash("Collection updated.", "success")
    return redirect(url_for("collections.collection_builder", collection_id=collection_id))


# ---------------------------------------------------------------------------
# JSON API — consumed by the builder's vanilla JS
# ---------------------------------------------------------------------------

@collections_bp.route("/api/recipes/search", methods=["GET"])
@login_required
@admin_required
def api_recipe_search():
    """Return up to 20 approved recipes matching the query string."""
    q = request.args.get("q", "").strip()
    stmt = db.select(Recipe).where(Recipe.status == "approved")
    if q:
        stmt = stmt.where(
            or_(
                Recipe.title.ilike(f"%{q}%"),
                Recipe.cuisine.ilike(f"%{q}%"),
            )
        )
    stmt = stmt.order_by(Recipe.title).limit(20)
    recipes = db.session.execute(stmt).scalars().all()

    return jsonify(
        [
            {
                "id": r.id,
                "title": r.title,
                "cuisine": r.cuisine or "",
                "diet": r.diet or "",
                "image_filename": r.image_filename,
            }
            for r in recipes
        ]
    )


@collections_bp.route(
    "/<int:collection_id>/add/<int:recipe_id>", methods=["POST"]
)
@login_required
@admin_required
def api_collection_add(collection_id: int, recipe_id: int):
    """Link a recipe to a collection. Idempotent — no error if already linked."""
    collection = db.session.get(RecipeCollection, collection_id)
    if not collection:
        return jsonify({"error": "Collection not found"}), 404

    recipe = db.session.get(Recipe, recipe_id)
    if not recipe:
        return jsonify({"error": "Recipe not found"}), 404

    existing = db.session.get(CollectionItem, (collection_id, recipe_id))
    if existing:
        return jsonify({"status": "already_exists"}), 200

    item = CollectionItem(collection_id=collection_id, recipe_id=recipe_id)
    db.session.add(item)
    db.session.commit()

    return jsonify(
        {
            "status": "added",
            "recipe": {
                "id": recipe.id,
                "title": recipe.title,
                "cuisine": recipe.cuisine or "",
                "diet": recipe.diet or "",
                "image_filename": recipe.image_filename,
            },
        }
    ), 201


@collections_bp.route(
    "/<int:collection_id>/remove/<int:recipe_id>", methods=["DELETE"]
)
@login_required
@admin_required
def api_collection_remove(collection_id: int, recipe_id: int):
    """Unlink a recipe from a collection."""
    item = db.session.get(CollectionItem, (collection_id, recipe_id))
    if not item:
        return jsonify({"error": "Link not found"}), 404

    db.session.delete(item)
    db.session.commit()
    return jsonify({"status": "removed"}), 200
