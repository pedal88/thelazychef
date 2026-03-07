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
import json
import threading
import logging
import collections
from flask import Blueprint, jsonify, request, render_template, current_app
from flask_login import login_required
from utils.decorators import admin_required
from database.models import db, Recipe, Ingredient, SocialMediaPost
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
    """Redirect to the management dashboard (new primary entry point)."""
    return render_template("admin/media_hub_management.html")


@media_hub_bp.route("/legacy")
@login_required
@admin_required
def media_hub_legacy():
    """Legacy card-grid dashboard (kept for reference)."""
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
        podcast_status: str | None = None
        podcast_has_audio: bool = False
        podcast_post_id: int | None = None
        for post in r.social_posts:
            if post.platform in statuses:
                statuses[post.platform] = post.status
            elif post.platform == "podcast":
                podcast_status = post.status
                podcast_post_id = post.id
                podcast_has_audio = bool(post.video_url and post.video_url.endswith(".mp3"))

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
            "status": r.status,
            "statuses": statuses,
            "knowledge": {
                "has_article": r.primary_resource_id is not None,
                "has_podcast": podcast_status in ("ready", "rendering"),
                "has_audio": podcast_has_audio,
                "has_video": statuses.get("tiktok") == "ready" or statuses.get("instagram") == "ready",
                "primary_resource_id": r.primary_resource_id,
                "podcast_post_id": podcast_post_id,
            },
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
            "id": post.id,
            "status": post.status,
            "video_url": post.video_url,
            "error": post.error_message,
            "script": post.voiceover_script,
        }

    return jsonify(result)


# ---------------------------------------------------------------------------
# Routes — Podcast Preview & Audio Rendering
# ---------------------------------------------------------------------------

@media_hub_bp.route("/api/podcast/<int:recipe_id>", methods=["GET"])
@login_required
@admin_required
def get_podcast_data(recipe_id: int):
    """
    Returns the podcast script and audio URL for a recipe.

    Response:
    {
      "post_id": 42,
      "status": "ready",
      "has_audio": true,
      "audio_url": "https://...",
      "script": { "episode_title": "...", "dialogue": [...] },
    }
    """
    post = db.session.execute(
        db.select(SocialMediaPost).where(
            SocialMediaPost.recipe_id == recipe_id,
            SocialMediaPost.platform == "podcast",
        )
    ).scalar()

    if not post:
        return jsonify({"status": "none", "has_audio": False, "script": None})

    # Parse script JSON
    script_data = None
    if post.voiceover_script:
        try:
            script_data = json.loads(post.voiceover_script)
        except (json.JSONDecodeError, TypeError):
            script_data = {"raw": post.voiceover_script}

    has_audio = bool(post.video_url and post.video_url.endswith(".mp3"))

    return jsonify({
        "post_id": post.id,
        "status": post.status,
        "has_audio": has_audio,
        "audio_url": post.video_url if has_audio else None,
        "script": script_data,
        "error": post.error_message,
    })


@media_hub_bp.route("/render-podcast-audio", methods=["POST"])
@login_required
@admin_required
def trigger_podcast_audio_render():
    """
    Phase 2: Render an existing podcast script to audio via TTS.

    JSON body:
      { "post_id": int }
    """
    data = request.get_json()
    if not data or not data.get("post_id"):
        return jsonify({"error": "post_id is required"}), 400

    post_id = int(data["post_id"])
    force = data.get("force", False)
    app = current_app._get_current_object()
    storage_provider = media_hub_bp.storage_provider

    def _run():
        from media_hub.podcast_engine import render_podcast_audio
        render_podcast_audio(post_id, app, storage_provider, force=force)

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()

    logger.info(f"[PodcastEngine] Audio rendering triggered for post {post_id} (force={force})")
    return jsonify({"status": "accepted", "post_id": post_id}), 202


# ---------------------------------------------------------------------------
# Routes — Fragment Snapshotter (Lego Building Blocks)
# ---------------------------------------------------------------------------

@media_hub_bp.route("/preview-fragments", methods=["POST"])
@login_required
@admin_required
def preview_fragments():
    """
    Render all fragment PNGs for a recipe and return their URLs.

    JSON body:
      { "recipe_id": int }

    Returns:
      { "fragments": [ { "type": str, "page": int, "url": str }, ... ] }
    """
    data = request.get_json()
    if not data or not data.get("recipe_id"):
        return jsonify({"error": "recipe_id is required"}), 400

    recipe_id = int(data["recipe_id"])
    app = current_app._get_current_object()
    storage_provider = media_hub_bp.storage_provider

    try:
        from media_hub.snapshotter import render_recipe_fragments

        results = render_recipe_fragments(recipe_id, app, storage_provider)

        fragments = []
        for frag in results:
            # Build filename for storage
            fname = f"preview_{frag.fragment_type}"
            if frag.total_pages > 1:
                fname += f"_p{frag.page}"
            fname += ".png"
            folder = f"fragments/recipe_{recipe_id}"

            if storage_provider:
                url = storage_provider.save(frag.png_bytes, fname, folder)
            else:
                # Fallback: return data URL (local dev without storage)
                import base64
                b64 = base64.b64encode(frag.png_bytes).decode()
                url = f"data:image/png;base64,{b64}"

            fragments.append({
                "type": frag.fragment_type,
                "page": frag.page,
                "total_pages": frag.total_pages,
                "component": frag.component,
                "url": url,
            })

        logger.info(f"[Snapshotter] Preview generated: {len(fragments)} fragments for recipe {recipe_id}")
        return jsonify({"fragments": fragments}), 200

    except Exception as e:
        logger.exception(f"[Snapshotter] Preview failed for recipe {recipe_id}")
        return jsonify({"error": str(e)}), 500


@media_hub_bp.route("/sandbox/api/search-recipes", methods=["GET"])
@login_required
@admin_required
def sandbox_search_recipes():
    """
    Lightweight recipe search for the Sandbox recipe picker.
    Accepts ?q=... and returns up to 10 matches by title or ID.
    """
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify([])

    results = []
    # If the query is purely numeric, search by ID first
    if query.isdigit():
        recipe = db.session.get(Recipe, int(query))
        if recipe:
            results.append({"id": recipe.id, "title": recipe.title, "cuisine": recipe.cuisine or ""})

    # Then search by title (case-insensitive LIKE)
    title_matches = (
        Recipe.query
        .filter(Recipe.title.ilike(f"%{query}%"))
        .order_by(Recipe.id.desc())
        .limit(10)
        .all()
    )
    seen_ids = {r["id"] for r in results}
    for r in title_matches:
        if r.id not in seen_ids:
            results.append({"id": r.id, "title": r.title, "cuisine": r.cuisine or ""})

    return jsonify(results[:10])


@media_hub_bp.route("/sandbox", methods=["GET"])
@login_required
@admin_required
def sandbox_gui():
    """
    Landing page for the Media Hub Design Sandbox.
    Provides a GUI to select recipes, themes, and launch specific fragments.
    """
    return render_template("admin/sandbox_gui.html")


@media_hub_bp.route("/sandbox/<fragment_name>", methods=["GET"])
@login_required
@admin_required
def fragment_sandbox(fragment_name):
    """
    Design sandbox — renders a single fragment as a standard web page.
    Open in browser and use F12 Inspector for real-time CSS iteration.

    Query params:
        recipe_id (int)  — default 192
        theme     (str)  — 'modern' | 'classic'
        debug     (bool) — '1'/'true' to show TikTok safe zones overlay
    """
    from media_hub.snapshotter import build_sandbox_context, VALID_FRAGMENTS

    if fragment_name not in VALID_FRAGMENTS:
        return jsonify({"error": f"Unknown fragment: {fragment_name}", "valid": sorted(VALID_FRAGMENTS)}), 404

    recipe_id = request.args.get("recipe_id", 192, type=int)
    theme_name = request.args.get("theme", "modern")
    debug = request.args.get("debug", "").lower() in ("1", "true", "yes")
    scale = request.args.get("scale", 1.0, type=float)

    try:
        storage_provider = media_hub_bp.storage_provider
        ctx = build_sandbox_context(
            recipe_id=recipe_id,
            fragment_name=fragment_name,
            app=current_app._get_current_object(),
            storage_provider=storage_provider,
            theme_name=theme_name,
            debug=debug,
            scale=scale,
        )
        # Support serving specific versions for comparison
        version = request.args.get("version", "1")
        template_path = f"fragments/{fragment_name}.html"

        if version == "pinned":
            pinned_tpl = f"fragments/{fragment_name}.html.pinned"
            pinned_abs = os.path.join(current_app.root_path, "templates", pinned_tpl)
            if os.path.exists(pinned_abs):
                template_path = pinned_tpl
        elif version not in ("1", "live"):
            versioned_tpl = f"fragments/{fragment_name}.v{version}.html"
            versioned_abs = os.path.join(current_app.root_path, "templates", versioned_tpl)
            if os.path.exists(versioned_abs):
                template_path = versioned_tpl

        return render_template(template_path, **ctx)
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        logger.exception(f"[Sandbox] Failed to render {fragment_name}")
        return jsonify({"error": str(e)}), 500


@media_hub_bp.route("/sandbox/pin/<fragment_name>", methods=["POST"])
@login_required
@admin_required
def pin_fragment(fragment_name):
    """Copy current fragment template to a .pinned backup for comparison."""
    import shutil
    from media_hub.snapshotter import VALID_FRAGMENTS

    if fragment_name not in VALID_FRAGMENTS:
        return jsonify({"error": f"Unknown fragment: {fragment_name}"}), 404

    src = os.path.join(current_app.root_path, "templates", "fragments", f"{fragment_name}.html")
    dst = os.path.join(current_app.root_path, "templates", "fragments", f"{fragment_name}.html.pinned")

    if not os.path.exists(src):
        return jsonify({"error": f"Template not found: {fragment_name}.html"}), 404

    shutil.copy2(src, dst)
    logger.info(f"[Sandbox] Pinned {fragment_name}.html → .pinned")
    return jsonify({"status": "pinned", "fragment": fragment_name})


@media_hub_bp.route("/sandbox/revert/<fragment_name>", methods=["POST"])
@login_required
@admin_required
def revert_fragment(fragment_name):
    """Restore the pinned version over the current live template."""
    import shutil
    from media_hub.snapshotter import VALID_FRAGMENTS

    if fragment_name not in VALID_FRAGMENTS:
        return jsonify({"error": f"Unknown fragment: {fragment_name}"}), 404

    pinned = os.path.join(current_app.root_path, "templates", "fragments", f"{fragment_name}.html.pinned")
    live = os.path.join(current_app.root_path, "templates", "fragments", f"{fragment_name}.html")

    if not os.path.exists(pinned):
        return jsonify({"error": "No pinned version found"}), 404

    shutil.copy2(pinned, live)
    os.remove(pinned)
    logger.info(f"[Sandbox] Reverted {fragment_name}.html from .pinned")
    return jsonify({"status": "reverted", "fragment": fragment_name})


@media_hub_bp.route("/sandbox/accept/<fragment_name>", methods=["POST"])
@login_required
@admin_required
def accept_fragment(fragment_name):
    """Accept the current live version and delete the pinned backup."""
    from media_hub.snapshotter import VALID_FRAGMENTS

    if fragment_name not in VALID_FRAGMENTS:
        return jsonify({"error": f"Unknown fragment: {fragment_name}"}), 404

    pinned = os.path.join(current_app.root_path, "templates", "fragments", f"{fragment_name}.html.pinned")

    if os.path.exists(pinned):
        os.remove(pinned)
        logger.info(f"[Sandbox] Accepted new {fragment_name}.html, deleted .pinned")

    return jsonify({"status": "accepted", "fragment": fragment_name})


@media_hub_bp.route("/sandbox/pin-status/<fragment_name>", methods=["GET"])
@login_required
@admin_required
def pin_status(fragment_name):
    """Check if a pinned version exists for this fragment."""
    pinned = os.path.join(current_app.root_path, "templates", "fragments", f"{fragment_name}.html.pinned")
    return jsonify({"pinned": os.path.exists(pinned), "fragment": fragment_name})


@media_hub_bp.route("/sandbox/versions/<fragment_name>", methods=["GET"])
@login_required
@admin_required
def list_fragment_versions(fragment_name):
    """List all available versions for a fragment (1 = original, 2+ = variants)."""
    import glob, re
    from media_hub.snapshotter import VALID_FRAGMENTS
    if fragment_name not in VALID_FRAGMENTS:
        return jsonify({"error": f"Unknown fragment: {fragment_name}"}), 404

    fragments_dir = os.path.join(current_app.root_path, "templates", "fragments")
    versions = [1]  # v1 always exists (the original .html)
    pattern = os.path.join(fragments_dir, f"{fragment_name}.v*.html")
    for path in glob.glob(pattern):
        m = re.search(r'\.v(\d+)\.html$', path)
        if m:
            versions.append(int(m.group(1)))
    versions.sort()
    return jsonify({"fragment": fragment_name, "versions": versions})


@media_hub_bp.route("/sandbox/create-version/<fragment_name>", methods=["POST"])
@login_required
@admin_required
def create_fragment_version(fragment_name):
    """Save the current fragment as a new numbered version (next unused integer)."""
    import shutil, glob, re
    from media_hub.snapshotter import VALID_FRAGMENTS
    if fragment_name not in VALID_FRAGMENTS:
        return jsonify({"error": f"Unknown fragment: {fragment_name}"}), 404

    fragments_dir = os.path.join(current_app.root_path, "templates", "fragments")
    src = os.path.join(fragments_dir, f"{fragment_name}.html")
    if not os.path.exists(src):
        return jsonify({"error": "Source template not found"}), 404

    # Find the highest existing version number
    max_v = 1
    pattern = os.path.join(fragments_dir, f"{fragment_name}.v*.html")
    for path in glob.glob(pattern):
        m = re.search(r'\.v(\d+)\.html$', path)
        if m:
            max_v = max(max_v, int(m.group(1)))

    next_v = max_v + 1
    dst = os.path.join(fragments_dir, f"{fragment_name}.v{next_v}.html")
    shutil.copy2(src, dst)
    logger.info(f"[Sandbox] Created version {next_v} for {fragment_name}")
    return jsonify({"status": "created", "fragment": fragment_name, "version": next_v})


@media_hub_bp.route("/sandbox/version/<fragment_name>/<int:version_num>", methods=["DELETE"])
@login_required
@admin_required
def delete_fragment_version(fragment_name, version_num):
    """Delete a specific version of a fragment.

    If version 1 is deleted, the lowest other version is promoted to v1
    (its file replaces the main .html and the old .v*.html is removed).
    """
    import glob, re, shutil
    from media_hub.snapshotter import VALID_FRAGMENTS
    if fragment_name not in VALID_FRAGMENTS:
        return jsonify({"error": f"Unknown fragment: {fragment_name}"}), 404

    fragments_dir = os.path.join(current_app.root_path, "templates", "fragments")

    if version_num == 1:
        # Find all other versions
        pattern = os.path.join(fragments_dir, f"{fragment_name}.v*.html")
        others = []
        for path in glob.glob(pattern):
            m = re.search(r'\.v(\d+)\.html$', path)
            if m:
                others.append(int(m.group(1)))
        if not others:
            return jsonify({"error": "Cannot delete the only version"}), 400

        # Promote the lowest other version to v1
        promote = min(others)
        src = os.path.join(fragments_dir, f"{fragment_name}.v{promote}.html")
        dst = os.path.join(fragments_dir, f"{fragment_name}.html")
        shutil.copy2(src, dst)
        os.remove(src)
        logger.info(f"[Sandbox] Deleted v1 of {fragment_name}, promoted v{promote} to v1")
        return jsonify({"status": "deleted", "fragment": fragment_name, "version": version_num, "promoted": promote})

    target = os.path.join(fragments_dir, f"{fragment_name}.v{version_num}.html")

    if not os.path.exists(target):
        return jsonify({"error": f"Version {version_num} not found"}), 404

    os.remove(target)
    logger.info(f"[Sandbox] Deleted version {version_num} for {fragment_name}")
    return jsonify({"status": "deleted", "fragment": fragment_name, "version": version_num})


@media_hub_bp.route("/sandbox/poll-templates", methods=["GET"])
@login_required
@admin_required
def poll_templates():
    """
    Endpoint for the Design Sandbox to check if fragments were saved to disk.
    Used for the Javascript Hot-Reloading feature.
    """
    import os
    root = os.getcwd()
    frag_dir = os.path.join(root, "templates", "fragments")
    max_mtime = 0.0
    if os.path.isdir(frag_dir):
        for fname in os.listdir(frag_dir):
            if fname.endswith(".html"):
                fpath = os.path.join(frag_dir, fname)
                mtime = os.path.getmtime(fpath)
                if mtime > max_mtime:
                    max_mtime = mtime
                    
    return jsonify({"last_modified": max_mtime})

# ---------------------------------------------------------------------------
# Routes — Knowledge Factory (Article + Podcast Generation)
# ---------------------------------------------------------------------------

@media_hub_bp.route("/generate-article", methods=["POST"])
@login_required
@admin_required
def trigger_article_generation():
    """
    Triggers async article generation for a recipe or ingredient.

    JSON body:
      { "source_type": "recipe" | "ingredient", "source_id": int }
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "JSON body required"}), 400

    source_type = data.get("source_type")
    source_id = data.get("source_id")

    if source_type not in ("recipe", "ingredient"):
        return jsonify({"error": f"Unsupported source_type: {source_type}"}), 400
    if not source_id:
        return jsonify({"error": "source_id is required"}), 400

    app = current_app._get_current_object()
    storage_provider = media_hub_bp.storage_provider

    def _run():
        from media_hub.orchestrator import generate_article_for_recipe, generate_article_for_ingredient
        if source_type == "recipe":
            generate_article_for_recipe(int(source_id), app, storage_provider)
        else:
            generate_article_for_ingredient(int(source_id), app, storage_provider)

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()

    logger.info(f"[KnowledgeFactory] Article generation triggered: {source_type} #{source_id}")
    return jsonify({"status": "accepted", "source_type": source_type, "source_id": source_id}), 202


@media_hub_bp.route("/generate-podcast", methods=["POST"])
@login_required
@admin_required
def trigger_podcast_generation():
    """
    Triggers async podcast script generation.

    JSON body:
      { "source_type": "recipe" | "ingredient" | "resource", "source_id": int, "force": bool }
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "JSON body required"}), 400

    source_type = data.get("source_type")
    source_id = data.get("source_id")
    force = data.get("force", False)

    if source_type not in ("recipe", "ingredient", "resource"):
        return jsonify({"error": f"Unsupported source_type: {source_type}"}), 400
    if not source_id:
        return jsonify({"error": "source_id is required"}), 400

    app = current_app._get_current_object()

    def _run():
        from media_hub.podcast_engine import generate_podcast_script
        generate_podcast_script(source_type, int(source_id), app, force=force)

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()

    logger.info(f"[PodcastEngine] Generation triggered: {source_type} #{source_id} (force={force})")
    return jsonify({"status": "accepted", "source_type": source_type, "source_id": source_id}), 202


@media_hub_bp.route("/generate-bulk", methods=["POST"])
@login_required
@admin_required
def trigger_bulk_generation():
    """
    Triggers bulk generation across multiple recipes.

    JSON body:
      { "action": "articles" | "podcasts" | "videos", "recipe_ids": [int] | "all" }

    If recipe_ids is "all", operates on all approved recipes missing the requested content.
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "JSON body required"}), 400

    action = data.get("action")
    recipe_ids = data.get("recipe_ids", "all")

    if action not in ("articles", "podcasts", "videos"):
        return jsonify({"error": f"Unknown action: {action}"}), 400

    # Resolve recipe IDs
    if recipe_ids == "all":
        recipes = db.session.execute(
            db.select(Recipe).where(Recipe.status == "approved")
        ).scalars().all()
        resolved_ids = [r.id for r in recipes]
    else:
        resolved_ids = [int(rid) for rid in recipe_ids]

    app = current_app._get_current_object()
    storage_provider = media_hub_bp.storage_provider

    def _run_bulk():
        if action == "articles":
            from media_hub.orchestrator import generate_article_for_recipe
            for rid in resolved_ids:
                generate_article_for_recipe(rid, app, storage_provider)
        elif action == "podcasts":
            from media_hub.podcast_engine import generate_podcast_script
            for rid in resolved_ids:
                generate_podcast_script("recipe", rid, app)
        elif action == "videos":
            from media_hub.orchestrator import generate_studio_pack
            for rid in resolved_ids:
                generate_studio_pack(rid, "tiktok", storage_provider, app)

    thread = threading.Thread(target=_run_bulk, daemon=True)
    thread.start()

    logger.info(f"[MediaHub] Bulk {action} triggered for {len(resolved_ids)} recipes")
    return jsonify({
        "status": "accepted",
        "action": action,
        "count": len(resolved_ids),
    }), 202


# ---------------------------------------------------------------------------
# Routes — Ingredients API (for Management Dashboard)
# ---------------------------------------------------------------------------

@media_hub_bp.route("/api/ingredients", methods=["GET"])
@login_required
@admin_required
def list_ingredients_with_status():
    """
    Returns all active ingredients with their knowledge asset statuses.
    """
    ingredients = db.session.execute(
        db.select(Ingredient)
        .where(Ingredient.status == "active")
        .order_by(Ingredient.name)
    ).scalars().all()

    # Get all podcast posts for ingredients (recipe_id is NULL, template_name like 'podcast_ingredient')
    podcast_posts = db.session.execute(
        db.select(SocialMediaPost).where(
            SocialMediaPost.platform == "podcast",
            SocialMediaPost.template_name == "podcast_ingredient",
        )
    ).scalars().all()

    # Build a lookup: we store ingredient-podcast scripts keyed by some mechanism
    # For now, look for posts with voiceover_script containing ingredient references

    result = []
    for ing in ingredients:
        result.append({
            "id": ing.id,
            "name": ing.name,
            "main_category": ing.main_category,
            "sub_category": ing.sub_category,
            "status": ing.status,
            "data_source": ing.data_source,
            "knowledge": {
                "has_article": ing.primary_resource_id is not None,
                "primary_resource_id": ing.primary_resource_id,
                "has_podcast": False,  # Will be enhanced when ingredient podcasts are indexed
            },
        })

    return jsonify(result)
