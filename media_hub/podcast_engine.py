"""
media_hub/podcast_engine.py — Dialogue Script Generator

Generates 5-minute podcast dialogue scripts from harmonized content contexts.
Supports three source types: Recipe, Ingredient, Resource.

The generated scripts are saved to SocialMediaPost (platform='podcast')
for future TTS rendering via the existing PodcastGenerator service.
"""

import json
import logging
from typing import Optional

from database.models import (
    Recipe, Ingredient, Resource, RecipeIngredient,
    SocialMediaPost, db,
)
from utils.prompt_manager import load_prompt

logger = logging.getLogger("media_hub.podcast_engine")

# Template registry — maps (source_type) to Jinja2 template path
PODCAST_TEMPLATES = {
    "recipe": "factory/podcast_recipe_dialogue.jinja2",
    "ingredient": "factory/podcast_ingredient_dialogue.jinja2",
    "resource": "factory/podcast_resource_dialogue.jinja2",
}


# ---------------------------------------------------------------------------
# Context builders (per source type)
# ---------------------------------------------------------------------------

def _build_recipe_podcast_context(recipe: Recipe, session) -> dict:
    """Build podcast context from a Recipe, including linked article if available."""
    from media_hub.orchestrator import build_full_recipe_context
    ctx = build_full_recipe_context(recipe, session)

    # Add linked article summary if the recipe has a primary_resource
    if recipe.primary_resource_id:
        resource = session.get(Resource, recipe.primary_resource_id)
        if resource and resource.summary:
            ctx["linked_article_summary"] = f"{resource.title}: {resource.summary}"

    return ctx


def _build_ingredient_podcast_context(ingredient: Ingredient, session) -> dict:
    """Build podcast context from an Ingredient."""
    # Parse aliases
    aliases = []
    if ingredient.aliases:
        try:
            aliases = json.loads(ingredient.aliases)
        except (json.JSONDecodeError, TypeError):
            aliases = []

    # Find recipes using this ingredient (top 5)
    recipe_ings = session.execute(
        db.select(RecipeIngredient)
        .where(RecipeIngredient.ingredient_id == ingredient.id)
        .limit(5)
    ).scalars().all()

    used_in_recipes = []
    for ri in recipe_ings:
        r = session.get(Recipe, ri.recipe_id)
        if r and r.status == "approved":
            used_in_recipes.append({"title": r.title, "cuisine": r.cuisine or "International"})

    # Nutrition
    nutrition = None
    if ingredient.calories_per_100g:
        nutrition = {
            "calories": round(ingredient.calories_per_100g or 0),
            "protein": round(ingredient.protein_per_100g or 0, 1),
            "fat": round(ingredient.fat_per_100g or 0, 1),
            "carbs": round(ingredient.carbs_per_100g or 0, 1),
            "fiber": round(ingredient.fiber_per_100g or 0, 1),
            "sodium": round(ingredient.sodium_mg_per_100g or 0, 1),
        }

    # Linked article
    linked_article_summary = None
    if ingredient.primary_resource_id:
        resource = session.get(Resource, ingredient.primary_resource_id)
        if resource and resource.summary:
            linked_article_summary = f"{resource.title}: {resource.summary}"

    return {
        "ingredient_name": ingredient.name,
        "main_category": ingredient.main_category or "Food",
        "sub_category": ingredient.sub_category,
        "tags": ingredient.tags,
        "nutrition": nutrition,
        "used_in_recipes": used_in_recipes,
        "aliases": aliases if aliases else None,
        "linked_article_summary": linked_article_summary,
    }


def _build_resource_podcast_context(resource: Resource, session) -> dict:
    """Build podcast context from a Resource (article)."""
    # Get an excerpt of the article content (first ~1500 chars)
    content_excerpt = ""
    if resource.content_markdown:
        content_excerpt = resource.content_markdown[:1500]
        if len(resource.content_markdown) > 1500:
            content_excerpt += "\n\n[... article continues ...]"

    return {
        "resource_title": resource.title,
        "resource_summary": resource.summary or "",
        "resource_tags": resource.tags or "",
        "resource_content_excerpt": content_excerpt,
        "related_recipes": [],  # Could be enriched via resource_relations
    }


# ---------------------------------------------------------------------------
# Main generation function
# ---------------------------------------------------------------------------

def generate_podcast_script(
    source_type: str,
    source_id: int,
    app,
    storage_provider=None,
    force: bool = False,
) -> dict:
    """
    Generate a 5-minute podcast dialogue script for a given source.

    Args:
        source_type: 'recipe', 'ingredient', or 'resource'
        source_id: The DB primary key of the source entity
        app: Flask app (for app context in background threads)
        storage_provider: Optional, for future TTS audio upload
        force: If True, regenerate even if a script already exists

    Returns:
        {"status": "ready", "script": dict} or {"status": "failed", "error": str}
    """
    from media_hub.orchestrator import _get_client, MODEL_ID

    template_name = PODCAST_TEMPLATES.get(source_type)
    if not template_name:
        return {"status": "failed", "error": f"Unknown source_type: {source_type}"}

    with app.app_context():
        session = db.session

        # --- Resolve source entity + build context ---
        if source_type == "recipe":
            entity = session.get(Recipe, source_id)
            if not entity:
                return {"status": "failed", "error": f"Recipe {source_id} not found"}
            context = _build_recipe_podcast_context(entity, session)
            post_recipe_id = source_id

        elif source_type == "ingredient":
            entity = session.get(Ingredient, source_id)
            if not entity:
                return {"status": "failed", "error": f"Ingredient {source_id} not found"}
            context = _build_ingredient_podcast_context(entity, session)
            post_recipe_id = None

        elif source_type == "resource":
            entity = session.get(Resource, source_id)
            if not entity:
                return {"status": "failed", "error": f"Resource {source_id} not found"}
            context = _build_resource_podcast_context(entity, session)
            post_recipe_id = None

        else:
            return {"status": "failed", "error": f"Unknown source_type: {source_type}"}

        # --- Cost guard: check for existing podcast script ---
        post_template = f"podcast_{source_type}"
        existing = session.execute(
            db.select(SocialMediaPost).where(
                SocialMediaPost.platform == "podcast",
                SocialMediaPost.template_name == post_template,
                SocialMediaPost.recipe_id == post_recipe_id if post_recipe_id else True,
            )
        ).scalar()

        if existing and not force:
            if existing.status == "ready":
                logger.info(f"[PodcastEngine] Skipping — script already exists (id={existing.id})")
                return {"status": "ready", "script": existing.voiceover_script, "skipped": True}

        # --- Create or reuse SocialMediaPost record ---
        if existing and force:
            # Reuse existing post: clear old script + audio
            post = existing
            post.voiceover_script = None
            post.video_url = None  # Invalidate old audio
            post.error_message = None
            post.status = "generating"
            logger.info(f"[PodcastEngine] Force-regenerating script for post {post.id}")
        else:
            post = SocialMediaPost(
                recipe_id=post_recipe_id,
                platform="podcast",
                template_name=post_template,
                status="generating",
            )
        session.add(post)
        session.commit()

        try:
            # --- Render prompt and call Gemini ---
            rendered_prompt = load_prompt(template_name, **context)
            logger.info(f"[PodcastEngine] Calling Gemini for {source_type} #{source_id}")

            client = _get_client()
            response = client.models.generate_content(
                model=MODEL_ID,
                contents=rendered_prompt,
                config={"response_mime_type": "application/json"},
            )

            script_data = json.loads(response.text)

            # --- Save script to post ---
            post.voiceover_script = json.dumps(script_data)
            post.status = "ready"
            session.commit()

            logger.info(
                f"[PodcastEngine] Script ready: '{script_data.get('episode_title', '?')}' "
                f"({script_data.get('word_count', '?')} words)"
            )
            return {"status": "ready", "script": script_data}

        except Exception as e:
            logger.error(f"[PodcastEngine] Failed for {source_type} #{source_id}: {e}")
            post.status = "failed"
            post.error_message = str(e)
            session.commit()
            return {"status": "failed", "error": str(e)}


# ---------------------------------------------------------------------------
# Phase 2: Audio Rendering (TTS)
# ---------------------------------------------------------------------------

def render_podcast_audio(
    post_id: int,
    app,
    storage_provider,
    force: bool = False,
) -> dict:
    """
    Render a podcast script to audio via Google Cloud TTS.

    This is Phase 2 of the two-phase workflow:
    Phase 1: generate_podcast_script() → saves dialogue JSON to SocialMediaPost
    Phase 2: render_podcast_audio() → TTS → MP3 → GCS → saves audio URL

    Args:
        post_id: The SocialMediaPost.id containing the script
        app: Flask app for DB context
        storage_provider: For uploading the MP3 to GCS
        force: If True, re-render even if audio already exists

    Returns:
        {"status": "ready", "audio_url": str} or {"status": "failed", "error": str}
    """
    from services.podcast_service import PodcastGenerator

    with app.app_context():
        session = db.session
        post = session.get(SocialMediaPost, post_id)

        if not post:
            return {"status": "failed", "error": f"Post {post_id} not found"}

        if not post.voiceover_script:
            return {"status": "failed", "error": "No script found on this post. Generate the script first."}

        # If audio already exists, skip (unless force)
        if not force and post.video_url and post.video_url.endswith(".mp3"):
            logger.info(f"[PodcastEngine] Audio already exists for post {post_id}")
            return {"status": "ready", "audio_url": post.video_url, "skipped": True}

        # Initialize TTS
        tts = PodcastGenerator(storage_provider=storage_provider)
        if not tts.is_available:
            return {
                "status": "failed",
                "error": "TTS service unavailable. Check GOOGLE_APPLICATION_CREDENTIALS.",
            }

        try:
            # Parse the dialogue script
            script_data = json.loads(post.voiceover_script)
            dialogue = script_data.get("dialogue", [])

            if not dialogue:
                return {"status": "failed", "error": "Script has no dialogue lines."}

            logger.info(
                f"[PodcastEngine] Rendering audio for post {post_id}: "
                f"{len(dialogue)} lines, ~{script_data.get('word_count', '?')} words"
            )

            # Update status to rendering
            post.status = "rendering"
            session.commit()

            # Generate audio
            audio_bytes = tts.generate_audio(dialogue)

            # Upload to GCS
            source_ref = f"recipe_{post.recipe_id}" if post.recipe_id else f"post_{post_id}"
            filename = f"podcast_{source_ref}.mp3"
            folder = f"podcasts/{source_ref}"
            audio_url = storage_provider.save(audio_bytes, filename, folder)

            # Save URL back to post
            post.video_url = audio_url  # Reusing video_url field for audio URL
            post.status = "ready"
            post.error_message = None
            session.commit()

            logger.info(f"[PodcastEngine] Audio ready: {audio_url}")
            return {"status": "ready", "audio_url": audio_url}

        except Exception as e:
            logger.error(f"[PodcastEngine] Audio rendering failed for post {post_id}: {e}")
            post.status = "ready"  # Keep script as 'ready' — only audio failed
            post.error_message = f"Audio rendering failed: {e}"
            session.commit()
            return {"status": "failed", "error": str(e)}
