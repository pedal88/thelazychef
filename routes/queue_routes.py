"""
Queue Blueprint — Manages the user's personal 'Cook Next' queue.

Routes:
    GET  /next-recipes           — The queue management page.
    POST /api/queue/add/<id>     — Add a recipe to the user's queue (idempotent).
    POST /api/queue/reorder      — Persist a new drag-and-drop ordering.
    DELETE /api/queue/remove/<id>— Remove a recipe from the queue.
"""
from __future__ import annotations

import datetime

from flask import Blueprint, jsonify, render_template, request, abort
from flask_login import current_user, login_required
from sqlalchemy import func

from database.models import Recipe, UserQueue, db

queue_bp = Blueprint("queue", __name__)


# ---------------------------------------------------------------------------
# HTML Page
# ---------------------------------------------------------------------------

@queue_bp.route("/next-recipes")
@login_required
def next_recipes_view() -> str:
    """Legacy route: Redirects to the unified library view."""
    from flask import redirect, url_for
    return redirect(url_for('recipes_list', view='next'))


# ---------------------------------------------------------------------------
# API: Add
# ---------------------------------------------------------------------------

@queue_bp.route("/api/queue/add/<int:recipe_id>", methods=["POST"])
@login_required
def queue_add(recipe_id: int):
    """Toggle a recipe in the current user's queue.

    If the recipe is NOT in the queue it is added (appended to the end).
    If it IS already in the queue it is REMOVED — acting as a de-queue.

    Returns:
        JSON with keys: success (bool), action ('added' | 'removed').
    """
    recipe = db.session.get(Recipe, recipe_id)
    if not recipe:
        abort(404)

    existing = db.session.execute(
        db.select(UserQueue).where(
            UserQueue.user_id == current_user.id,
            UserQueue.recipe_id == recipe_id
        )
    ).scalars().first()

    if existing:
        # Already queued → remove it
        db.session.delete(existing)
        db.session.commit()
        return jsonify(success=True, action='removed')

    # Not queued → add at the end
    max_pos_result = db.session.execute(
        db.select(func.max(UserQueue.position)).where(UserQueue.user_id == current_user.id)
    ).scalar()
    next_position = (max_pos_result or 0) + 1

    entry = UserQueue(
        user_id=current_user.id,
        recipe_id=recipe_id,
        position=next_position,
        added_at=datetime.datetime.utcnow(),
    )
    db.session.add(entry)
    db.session.commit()

    return jsonify(success=True, action='added')


# ---------------------------------------------------------------------------
# API: Reorder
# ---------------------------------------------------------------------------

@queue_bp.route("/api/queue/reorder", methods=["POST"])
@login_required
def queue_reorder():
    """
    Persists a new drag-and-drop order for the user's queue.

    Accepts JSON body: {"ordered_ids": [recipe_id_1, recipe_id_2, ...]}.
    Iterates the list and assigns `position = index + 1` for each matching
    row. Only updates rows owned by the current user (security guard).

    Returns:
        JSON with key: success (bool).
    """
    payload = request.get_json(silent=True) or {}
    ordered_ids: list[int] = payload.get("ordered_ids", [])

    if not ordered_ids:
        return jsonify(success=False, error="No IDs provided"), 400

    # Fetch all the user's queue entries in a single query
    entries = {
        entry.recipe_id: entry
        for entry in db.session.execute(
            db.select(UserQueue).where(UserQueue.user_id == current_user.id)
        ).scalars().all()
    }

    for index, recipe_id in enumerate(ordered_ids):
        entry = entries.get(recipe_id)
        if entry:                           # Security: silently skip IDs we don't own
            entry.position = index + 1

    db.session.commit()
    return jsonify(success=True)


# ---------------------------------------------------------------------------
# API: Remove
# ---------------------------------------------------------------------------

@queue_bp.route("/api/queue/remove/<int:recipe_id>", methods=["DELETE"])
@login_required
def queue_remove(recipe_id: int):
    """
    Removes a recipe from the current user's queue.

    If the item doesn't exist, returns 200 (idempotent removal).

    Args:
        recipe_id: The primary key of the Recipe to remove.

    Returns:
        JSON with key: success (bool).
    """
    entry = db.session.execute(
        db.select(UserQueue).where(
            UserQueue.user_id == current_user.id,
            UserQueue.recipe_id == recipe_id
        )
    ).scalars().first()

    if entry:
        db.session.delete(entry)
        db.session.commit()

    return jsonify(success=True)
