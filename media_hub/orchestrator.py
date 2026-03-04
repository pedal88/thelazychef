"""
media_hub/orchestrator.py — Data Harmonization & Script Generation

The 'Context Builder' aggregates data from three sources before calling Gemini:
  1. Recipe Table: Steps, Prep Time, Servings, Difficulty
  2. Ingredient Table: Fun facts / descriptions for top 4 ingredients
  3. Resource Table: Method-specific tips (e.g. "Searing 101")

This harmonized context is fed into platform-specific Jinja2 prompts,
then sent to Gemini 2.0 Flash for voiceover script generation.
"""

import json
import logging
from typing import Optional

from google import genai
from sqlalchemy.orm import Session

from database.models import Recipe, RecipeIngredient, Ingredient, Resource, SocialMediaPost, db
from utils.prompt_manager import load_prompt

logger = logging.getLogger(__name__)

# Gemini client — reuses the API key already loaded by ai_engine on app startup
_client: Optional[genai.Client] = None

MODEL_ID = "gemini-2.0-flash"


def _get_client() -> genai.Client:
    """Lazy-init Gemini client so we don't import ai_engine directly."""
    global _client
    if _client is None:
        import os
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY is required for Media Hub script generation.")
        _client = genai.Client(api_key=api_key)
    return _client


# ---------------------------------------------------------------------------
# 1. DATA HARMONIZATION — Context Builder
# ---------------------------------------------------------------------------

def build_recipe_context(recipe: Recipe, session: Session) -> dict:
    """
    Aggregates a 'harmonized context' dict from Recipe + Ingredient + Resource tables.

    Returns a dict suitable for rendering into a Jinja2 social prompt template:
      {
        "recipe_title": str,
        "cuisine": str,
        "prep_time": int,
        "servings": int,
        "difficulty": str,
        "ingredients": [ {name, image_url, fun_fact}, ... ],  # top 4
        "steps": [ str, ... ],
        "method_tip": str | None,
      }
    """
    # --- Recipe core ---
    steps: list[str] = []
    detected_methods: list[str] = []

    for inst in sorted(recipe.instructions, key=lambda i: (i.global_order_index or 0, i.step_number)):
        steps.append(inst.text)
        # Heuristic: detect cooking methods mentioned in step text
        for method_keyword in ("sear", "braise", "blanch", "sous vide", "flambe", "deglaze", "temper"):
            if method_keyword in inst.text.lower() and method_keyword not in detected_methods:
                detected_methods.append(method_keyword)

    # --- Ingredients (top 4 by amount/weight descending) ---
    recipe_ings: list[RecipeIngredient] = sorted(
        recipe.ingredients,
        key=lambda ri: ri.gram_weight or 0,
        reverse=True,
    )[:4]

    enriched_ingredients: list[dict] = []
    for ri in recipe_ings:
        ing: Ingredient = ri.ingredient
        enriched_ingredients.append({
            "name": ing.name,
            "image_url": ing.image_url,
            "fun_fact": _get_ingredient_fact(ing),
        })

    # --- Resource lookup for method tips ---
    method_tip: Optional[str] = None
    if detected_methods:
        method_tip = _find_method_tip(detected_methods, session)

    return {
        "recipe_title": recipe.title,
        "cuisine": recipe.cuisine or "International",
        "prep_time": recipe.prep_time_mins or 30,
        "servings": recipe.base_servings or 4,
        "difficulty": recipe.difficulty or "Medium",
        "ingredients": enriched_ingredients,
        "steps": steps,
        "method_tip": method_tip,
    }


def _get_ingredient_fact(ing: Ingredient) -> Optional[str]:
    """
    Extracts a fun fact or description from the Ingredient record.

    Falls back to sub-category if no richer text is available.
    """
    # Ingredients don't have a 'fun_fact' column today,
    # but they have tags and sub_category which can serve as a lightweight fact.
    # When a dedicated 'fun_fact' or 'description' column is added, this is the
    # single place to update.
    if ing.sub_category:
        return f"A {ing.sub_category.lower()} ingredient"
    if ing.tags:
        return ing.tags
    return None


def _find_method_tip(methods: list[str], session: Session) -> Optional[str]:
    """
    Searches the Resource table for articles whose title or tags mention
    one of the detected cooking methods. Returns the first matching
    article's summary as a pro tip.
    """
    for method in methods:
        resource: Optional[Resource] = session.execute(
            db.select(Resource)
            .where(Resource.status == 'published')
            .where(
                db.or_(
                    Resource.title.ilike(f"%{method}%"),
                    Resource.tags.ilike(f"%{method}%"),
                )
            )
            .limit(1)
        ).scalar()

        if resource and resource.summary:
            return f"{resource.title}: {resource.summary}"

    return None


# ---------------------------------------------------------------------------
# 2. SCRIPT GENERATION — Gemini 2.0 Flash
# ---------------------------------------------------------------------------

PLATFORM_TEMPLATES = {
    "tiktok": "social/tiktok_persona.jinja2",
    "instagram": "social/insta_persona.jinja2",
}


def generate_script(recipe: Recipe, platform: str, session: Session) -> dict:
    """
    End-to-end pipeline: harmonize context → render prompt → call Gemini → return parsed JSON.

    Args:
        recipe: The Recipe ORM object (with relationships loaded).
        platform: 'tiktok' or 'instagram'.
        session: Active SQLAlchemy session.

    Returns:
        Parsed JSON dict from Gemini containing voiceover_script, subtitle_segments, etc.

    Raises:
        ValueError on unknown platform or Gemini errors.
    """
    template_name = PLATFORM_TEMPLATES.get(platform)
    if not template_name:
        raise ValueError(f"Unknown platform: {platform}. Supported: {list(PLATFORM_TEMPLATES.keys())}")

    # Step 1: Build harmonized context
    context = build_recipe_context(recipe, session)
    logger.info(f"[MediaHub] Built context for recipe '{recipe.title}' ({platform})")

    # Step 2: Render prompt
    rendered_prompt = load_prompt(template_name, **context)

    # Step 3: Call Gemini
    client = _get_client()
    response = client.models.generate_content(
        model=MODEL_ID,
        contents=rendered_prompt,
        config={"response_mime_type": "application/json"},
    )

    # Step 4: Parse response
    try:
        result = json.loads(response.text)
    except json.JSONDecodeError as e:
        logger.error(f"[MediaHub] Gemini returned invalid JSON: {e}")
        raise ValueError(f"Gemini returned invalid JSON: {response.text[:200]}")

    logger.info(f"[MediaHub] Script generated for '{recipe.title}' ({platform})")
    return result


# ---------------------------------------------------------------------------
# 3. FULL ORCHESTRATION — Called by the route
# ---------------------------------------------------------------------------

def generate_studio_pack(
    recipe_id: int,
    platform: str,
    storage_provider,
    app,
) -> dict:
    """
    Full orchestration: check cost guard → generate script → render video → upload → save record.

    Designed to run in a background thread. Uses app context for DB access.

    Returns:
        {"status": "ready", "video_url": str, "script": dict}
        or {"status": "failed", "error": str}
    """
    from media_hub.video_engine import render_video

    template_name = PLATFORM_TEMPLATES.get(platform, "unknown")

    with app.app_context():
        session = db.session

        # --- Cost Guard: check for existing identical post ---
        existing: Optional[SocialMediaPost] = session.execute(
            db.select(SocialMediaPost).where(
                SocialMediaPost.recipe_id == recipe_id,
                SocialMediaPost.platform == platform,
                SocialMediaPost.template_name == template_name,
                SocialMediaPost.status == "ready",
            )
        ).scalar()

        if existing:
            logger.info(f"[MediaHub] Skipping — identical post already exists (id={existing.id})")
            return {
                "status": "ready",
                "video_url": existing.video_url,
                "script": existing.voiceover_script,
                "skipped": True,
            }

        # --- Upsert SocialMediaPost record to 'generating' ---
        post: Optional[SocialMediaPost] = session.execute(
            db.select(SocialMediaPost).where(
                SocialMediaPost.recipe_id == recipe_id,
                SocialMediaPost.platform == platform,
                SocialMediaPost.template_name == template_name,
            )
        ).scalar()

        if not post:
            post = SocialMediaPost(
                recipe_id=recipe_id,
                platform=platform,
                template_name=template_name,
                status="generating",
            )
            session.add(post)
        else:
            post.status = "generating"
            post.error_message = None

        session.commit()

        try:
            # Load recipe with relationships
            recipe = session.execute(
                db.select(Recipe).where(Recipe.id == recipe_id)
            ).scalar()

            if not recipe:
                raise ValueError(f"Recipe {recipe_id} not found")

            # Step 1: Generate script
            script_data = generate_script(recipe, platform, session)
            post.voiceover_script = json.dumps(script_data)
            session.commit()

            # Step 2: Render video
            video_bytes = render_video(recipe, script_data, platform, storage_provider)

            # Step 3: Upload to GCS
            filename = f"{platform}_{recipe_id}.mp4"
            folder = f"social_outputs/{recipe_id}"
            video_url = storage_provider.save(video_bytes, filename, folder)

            # Step 4: Update record
            post.status = "ready"
            post.video_url = video_url
            session.commit()

            logger.info(f"[MediaHub] Studio pack ready: {video_url}")
            return {"status": "ready", "video_url": video_url, "script": script_data}

        except Exception as e:
            logger.error(f"[MediaHub] Generation failed for recipe {recipe_id}: {e}")
            post.status = "failed"
            post.error_message = str(e)
            session.commit()
            return {"status": "failed", "error": str(e)}
