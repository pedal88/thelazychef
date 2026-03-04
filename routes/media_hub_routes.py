"""
routes/media_hub_routes.py — API bridge for the Media Hub Sidecar

Blueprint: /admin/media-hub
  GET  /                          → Dashboard UI (recipe grid)
  GET  /overview                  → Developer workbench (process map, IDE links, logs)
  GET  /api/recipes               → Recipe list with social post statuses
  POST /generate                  → Trigger async generation
  GET  /api/status/<recipe_id>    → Poll generation status
  GET  /api/logs                  → Recent activity log lines
  GET  /api/workbench             → Scanned templates & config files
"""

import os
import threading
import logging
import collections
from flask import Blueprint, jsonify, request, render_template, current_app
from flask_login import login_required
from utils.decorators import admin_required
from database.models import db, Recipe, SocialMediaPost
from sqlalchemy.orm import joinedload

logger = logging.getLogger(__name__)

media_hub_bp = Blueprint("media_hub", __name__, url_prefix="/admin/media-hub")

# ---------------------------------------------------------------------------
# In-memory ring buffer for Media Hub activity logs (last 200 lines)
# ---------------------------------------------------------------------------
MEDIA_HUB_LOG_BUFFER: collections.deque[str] = collections.deque(maxlen=200)


class MediaHubLogHandler(logging.Handler):
    """Captures Media Hub log records into an in-memory ring buffer."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            MEDIA_HUB_LOG_BUFFER.append(msg)
        except Exception:
            self.handleError(record)


def _install_log_handler() -> None:
    """Attach the ring-buffer handler to media_hub loggers (idempotent)."""
    handler = MediaHubLogHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s  %(levelname)-5s  %(message)s", datefmt="%H:%M:%S"))

    for logger_name in ("media_hub.orchestrator", "media_hub.video_engine", __name__):
        log = logging.getLogger(logger_name)
        # Don't double-install
        if not any(isinstance(h, MediaHubLogHandler) for h in log.handlers):
            log.addHandler(handler)
            log.setLevel(logging.DEBUG)


_install_log_handler()


# ---------------------------------------------------------------------------
# Routes — Dashboard & Overview
# ---------------------------------------------------------------------------

@media_hub_bp.route("/")
@login_required
@admin_required
def media_hub_dashboard():
    """Render the Global Media Studio dashboard."""
    return render_template("admin/media_hub.html")


@media_hub_bp.route("/overview")
@login_required
@admin_required
def media_hub_overview():
    """Render the developer workbench / overview dashboard."""
    return render_template("admin/media_hub_overview.html")


# ---------------------------------------------------------------------------
# Routes — Workbench API (template scanning)
# ---------------------------------------------------------------------------

@media_hub_bp.route("/api/workbench", methods=["GET"])
@login_required
@admin_required
def workbench_info():
    """
    Scans data/prompts/social/ for persona templates and checks
    data/constraints/graph_metadata.json.

    Returns:
    {
      "templates": [
        {"filename": "tiktok_persona.jinja2", "path": "social/tiktok_persona.jinja2",
         "ide_url": "/admin/prompts/", "size_bytes": 1234},
        ...
      ],
      "config": {
        "filename": "graph_metadata.json",
        "exists": true,
        "ide_url": "/admin/prompts/",
        "size_bytes": 975
      }
    }
    """
    root = os.getcwd()
    social_dir = os.path.join(root, "data", "prompts", "social")
    config_path = os.path.join(root, "data", "constraints", "graph_metadata.json")

    # Scan social templates
    templates = []
    if os.path.isdir(social_dir):
        for fname in sorted(os.listdir(social_dir)):
            if fname.endswith(".jinja2"):
                fpath = os.path.join(social_dir, fname)
                templates.append({
                    "filename": fname,
                    "path": f"social/{fname}",
                    "ide_url": "/admin/prompts/",
                    "size_bytes": os.path.getsize(fpath),
                    "modified": os.path.getmtime(fpath),
                })

    # Check graph_metadata config
    config_exists = os.path.isfile(config_path)
    config_info = {
        "filename": "graph_metadata.json",
        "exists": config_exists,
        "path": "../constraints/graph_metadata.json",
        "ide_url": "/admin/prompts/",
        "size_bytes": os.path.getsize(config_path) if config_exists else 0,
    }

    return jsonify({"templates": templates, "config": config_info})


# ---------------------------------------------------------------------------
# Routes — Activity Log API
# ---------------------------------------------------------------------------

@media_hub_bp.route("/api/logs", methods=["GET"])
@login_required
@admin_required
def get_activity_logs():
    """
    Returns the last N lines from the Media Hub in-memory log buffer.
    Query param: ?lines=20 (default 20, max 200)
    """
    n = min(int(request.args.get("lines", 20)), 200)
    lines = list(MEDIA_HUB_LOG_BUFFER)[-n:]
    return jsonify({"lines": lines, "total": len(MEDIA_HUB_LOG_BUFFER)})


# ---------------------------------------------------------------------------
# Routes — Recipe API & Generation
# ---------------------------------------------------------------------------

@media_hub_bp.route("/api/recipes", methods=["GET"])
@login_required
@admin_required
def list_recipes_with_status():
    """
    Returns all approved recipes with their SocialMediaPost statuses.

    Response shape:
    [
      {
        "id": 1,
        "title": "...",
        "image_url": "...",
        "cuisine": "...",
        "statuses": {
          "tiktok": "ready" | "generating" | "failed" | null,
          "instagram": "ready" | "generating" | "failed" | null,
        }
      },
      ...
    ]
    """
    recipes = db.session.execute(
        db.select(Recipe)
        .where(Recipe.status == "approved")
        .options(joinedload(Recipe.social_posts))
        .order_by(Recipe.id.desc())
    ).unique().scalars().all()

    from services.storage_service import GoogleCloudStorageProvider
    storage_provider = media_hub_bp.storage_provider

    result = []
    for r in recipes:
        # Build status map
        statuses: dict[str, str | None] = {"tiktok": None, "instagram": None}
        for post in r.social_posts:
            if post.platform in statuses:
                statuses[post.platform] = post.status

        # Resolve image URL
        image_url = None
        if r.image_filename:
            if isinstance(storage_provider, GoogleCloudStorageProvider):
                image_url = f"https://storage.googleapis.com/{storage_provider.bucket_name}/recipes/{r.image_filename}"
            else:
                image_url = f"/static/recipes/{r.image_filename}"

        result.append({
            "id": r.id,
            "title": r.title,
            "image_url": image_url,
            "cuisine": r.cuisine,
            "statuses": statuses,
        })

    return jsonify(result)


@media_hub_bp.route("/generate", methods=["POST"])
@login_required
@admin_required
def trigger_generation():
    """
    Triggers async generation of a Studio Pack for a recipe × platform.

    JSON body:
      { "recipe_id": int, "platform": "tiktok" | "instagram" }

    Returns 202 Accepted immediately; poll /api/status/<recipe_id> for updates.
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "JSON body required"}), 400

    recipe_id = data.get("recipe_id")
    platform = data.get("platform", "tiktok")

    if not recipe_id:
        return jsonify({"error": "recipe_id is required"}), 400

    if platform not in ("tiktok", "instagram"):
        return jsonify({"error": f"Unsupported platform: {platform}"}), 400

    # Verify recipe exists
    recipe = db.session.get(Recipe, int(recipe_id))
    if not recipe:
        return jsonify({"error": f"Recipe {recipe_id} not found"}), 404

    # Fire-and-forget in background thread
    app = current_app._get_current_object()
    storage_provider = media_hub_bp.storage_provider

    def _run():
        from media_hub.orchestrator import generate_studio_pack
        generate_studio_pack(recipe_id, platform, storage_provider, app)

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()

    logger.info(f"[MediaHub] Generation triggered for recipe {recipe_id} ({platform})")
    return jsonify({"status": "accepted", "recipe_id": recipe_id, "platform": platform}), 202


@media_hub_bp.route("/api/status/<int:recipe_id>", methods=["GET"])
@login_required
@admin_required
def get_generation_status(recipe_id: int):
    """
    Returns the current SocialMediaPost statuses for a recipe.

    Response:
    {
      "tiktok":    {"status": "ready", "video_url": "...", "error": null},
      "instagram": {"status": "generating", "video_url": null, "error": null},
    }
    """
    posts = db.session.execute(
        db.select(SocialMediaPost).where(SocialMediaPost.recipe_id == recipe_id)
    ).scalars().all()

    result: dict = {}
    for post in posts:
        result[post.platform] = {
            "status": post.status,
            "video_url": post.video_url,
            "error": post.error_message,
            "script": post.voiceover_script,
        }

    return jsonify(result)
