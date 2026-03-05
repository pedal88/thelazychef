"""
media_hub/orchestrator.py — Data Harmonization, Script Generation & Knowledge Factory

The 'Context Builder' aggregates data from three sources before calling Gemini:
  1. Recipe Table: ALL columns (steps, nutrition, diets, chef, protein_type...)
  2. Ingredient Table: Full nutrition, tags, aliases, sub_category
  3. Resource Table: Method-specific tips (e.g. "Searing 101")

The 'Knowledge Factory' generates long-form articles for recipes/ingredients
and saves them as Resource entries linked via primary_resource_id.
"""

import json
import logging
import re
from typing import Optional

from google import genai
from sqlalchemy.orm import Session

from database.models import (
    Recipe, RecipeIngredient, Ingredient, Resource,
    SocialMediaPost, db,
)
from utils.prompt_manager import load_prompt

logger = logging.getLogger("media_hub.orchestrator")

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


def _parse_gemini_json(raw_text: str) -> dict:
    """Parse JSON from Gemini, handling common malformed output.

    Gemini's JSON mode can produce strings with unescaped control characters
    (literal newlines, tabs) inside JSON string values, which breaks strict
    json.loads(). This function:
    1. Tries strict parsing first.
    2. On failure, sanitizes control chars inside string values and retries.
    3. As a last resort, uses a regex to extract a JSON object.
    """
    import re

    # Attempt 1: strict parse
    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        pass

    # Attempt 2: replace unescaped control characters within strings
    # This targets literal \n, \r, \t that aren't preceded by a backslash
    sanitized = raw_text
    # Replace actual control chars with their escaped equivalents
    sanitized = sanitized.replace('\r\n', '\\n')
    sanitized = sanitized.replace('\r', '\\n')
    sanitized = sanitized.replace('\n', '\\n')
    sanitized = sanitized.replace('\t', '\\t')
    try:
        return json.loads(sanitized)
    except json.JSONDecodeError:
        pass

    # Attempt 3: extract JSON block from markdown fences if present
    match = re.search(r'```json\s*(\{.*?\})\s*```', raw_text, re.DOTALL)
    if match:
        cleaned = match.group(1).replace('\n', '\\n').replace('\t', '\\t')
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

    # Final: raise with original error for debugging
    return json.loads(raw_text)  # Will raise the original JSONDecodeError


# ---------------------------------------------------------------------------
# 1. DATA HARMONIZATION — Context Builders
# ---------------------------------------------------------------------------

def build_recipe_context(recipe: Recipe, session: Session) -> dict:
    """
    LEGACY context builder — lightweight, used by social video generation.
    Returns the subset needed for TikTok/Instagram persona prompts.
    """
    steps: list[str] = []
    detected_methods: list[str] = []

    for inst in sorted(recipe.instructions, key=lambda i: (i.global_order_index or 0, i.step_number)):
        steps.append(inst.text)
        for method_keyword in ("sear", "braise", "blanch", "sous vide", "flambe", "deglaze", "temper"):
            if method_keyword in inst.text.lower() and method_keyword not in detected_methods:
                detected_methods.append(method_keyword)

    # Ingredients (top 4 by amount/weight descending)
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


def build_full_recipe_context(recipe: Recipe, session: Session) -> dict:
    """
    FULL context builder — pulls ALL columns for Knowledge Factory / podcasts.

    Enriches the base context with:
    - Nutrition data (calories, protein, carbs, fat)
    - Diet labels, protein type, taste level
    - ALL ingredients (not just top 4)
    - Chef attribution
    """
    # Start with the base context
    ctx = build_recipe_context(recipe, session)

    # --- Enrich with ALL ingredients ---
    all_ings: list[RecipeIngredient] = sorted(
        recipe.ingredients,
        key=lambda ri: ri.gram_weight or 0,
        reverse=True,
    )
    all_enriched: list[dict] = []
    for ri in all_ings:
        ing: Ingredient = ri.ingredient
        all_enriched.append({
            "name": ing.name,
            "amount": f"{ri.amount} {ri.unit}" if ri.amount else "",
            "image_url": ing.image_url,
            "fun_fact": _get_ingredient_fact(ing),
        })
    ctx["ingredients"] = all_enriched

    # --- Nutrition ---
    if recipe.total_calories:
        per_serving = recipe.base_servings or 4
        ctx["nutrition"] = {
            "calories": round((recipe.total_calories or 0) / per_serving),
            "protein": round((recipe.total_protein or 0) / per_serving, 1),
            "carbs": round((recipe.total_carbs or 0) / per_serving, 1),
            "fat": round((recipe.total_fat or 0) / per_serving, 1),
        }

    # --- Diets, protein type, taste ---
    try:
        ctx["diets"] = recipe.diets_list
    except Exception:
        ctx["diets"] = []

    ctx["protein_type"] = recipe.protein_type
    ctx["taste_level"] = recipe.taste_level

    # --- Chef attribution ---
    if recipe.chef:
        ctx["chef_name"] = recipe.chef.id  # chef.id is the display name/slug

    return ctx


def build_full_ingredient_context(ingredient: Ingredient, session: Session) -> dict:
    """
    Full context builder for an Ingredient — used by article generation.
    """
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

    return {
        "ingredient_name": ingredient.name,
        "main_category": ingredient.main_category or "Food",
        "sub_category": ingredient.sub_category,
        "tags": ingredient.tags,
        "nutrition": nutrition,
        "used_in_recipes": used_in_recipes,
        "aliases": aliases if aliases else None,
    }


def _get_ingredient_fact(ing: Ingredient) -> Optional[str]:
    """Extract a fun fact or description from the Ingredient record."""
    if ing.sub_category:
        return f"A {ing.sub_category.lower()} ingredient"
    if ing.tags:
        return ing.tags
    return None


def _find_method_tip(methods: list[str], session: Session) -> Optional[str]:
    """Search Resource table for articles matching detected cooking methods."""
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
# 2. KNOWLEDGE FACTORY — Article Generation
# ---------------------------------------------------------------------------

ARTICLE_TEMPLATES = {
    "recipe": "factory/recipe_deep_dive_writer.jinja2",
    "ingredient": "factory/ingredient_101_writer.jinja2",
}


def generate_article_for_recipe(
    recipe_id: int,
    app,
    storage_provider=None,
) -> dict:
    """
    Generate a "Food Forensics" deep-dive article for a recipe.

    Safety: Runs inside a DB transaction. If Gemini or image generation fails,
    no orphan Resource is left in the database.

    Returns:
        {"status": "ready", "resource_id": int} or {"status": "failed", "error": str}
    """
    with app.app_context():
        session = db.session
        recipe = session.get(Recipe, recipe_id)
        if not recipe:
            return {"status": "failed", "error": f"Recipe {recipe_id} not found"}

        # --- Guard: skip if primary_resource already exists ---
        if recipe.primary_resource_id:
            logger.info(f"[KnowledgeFactory] Recipe '{recipe.title}' already has primary resource (id={recipe.primary_resource_id})")
            return {"status": "ready", "resource_id": recipe.primary_resource_id, "skipped": True}

        try:
            # Build full context
            context = build_full_recipe_context(recipe, session)
            logger.info(f"[KnowledgeFactory] Generating article for recipe '{recipe.title}'")

            # Render prompt and call Gemini
            rendered_prompt = load_prompt(ARTICLE_TEMPLATES["recipe"], **context)
            client = _get_client()
            response = client.models.generate_content(
                model=MODEL_ID,
                contents=rendered_prompt,
                config={"response_mime_type": "application/json"},
            )

            article_data = _parse_gemini_json(response.text)

            # --- Create Resource in a transaction ---
            slug = article_data.get("slug", f"recipe-{recipe_id}-deep-dive")
            # Ensure slug uniqueness
            existing_slug = session.execute(
                db.select(Resource).where(Resource.slug == slug)
            ).scalar()
            if existing_slug:
                slug = f"{slug}-{recipe_id}"

            new_resource = Resource(
                slug=slug,
                title=article_data.get("title", f"Deep Dive: {recipe.title}"),
                summary=article_data.get("summary", ""),
                content_markdown=article_data.get("content_markdown", ""),
                tags=article_data.get("tags", ""),
                image_filename=recipe.image_filename,  # Inherit hero image from recipe
                status="draft",  # Start as draft for admin review
            )
            session.add(new_resource)
            session.flush()  # Get the ID without committing

            # Link back to recipe
            recipe.primary_resource_id = new_resource.id

            # Commit the transaction (Resource + Recipe FK update atomically)
            session.commit()

            logger.info(
                f"[KnowledgeFactory] Article created: '{new_resource.title}' "
                f"(resource_id={new_resource.id}, slug={slug})"
            )

            return {
                "status": "ready",
                "resource_id": new_resource.id,
                "title": new_resource.title,
                "image_prompt": article_data.get("image_prompt"),
            }

        except Exception as e:
            session.rollback()
            logger.error(f"[KnowledgeFactory] Article generation failed for recipe {recipe_id}: {e}")
            return {"status": "failed", "error": str(e)}


def generate_article_for_ingredient(
    ingredient_id: int,
    app,
    storage_provider=None,
) -> dict:
    """
    Generate a journalistic "101" article for an ingredient.

    Same transactional safety as recipe articles.
    """
    with app.app_context():
        session = db.session
        ingredient = session.get(Ingredient, ingredient_id)
        if not ingredient:
            return {"status": "failed", "error": f"Ingredient {ingredient_id} not found"}

        # --- Guard: skip if primary_resource already exists ---
        if ingredient.primary_resource_id:
            logger.info(f"[KnowledgeFactory] Ingredient '{ingredient.name}' already has primary resource (id={ingredient.primary_resource_id})")
            return {"status": "ready", "resource_id": ingredient.primary_resource_id, "skipped": True}

        try:
            context = build_full_ingredient_context(ingredient, session)
            logger.info(f"[KnowledgeFactory] Generating article for ingredient '{ingredient.name}'")

            rendered_prompt = load_prompt(ARTICLE_TEMPLATES["ingredient"], **context)
            client = _get_client()
            response = client.models.generate_content(
                model=MODEL_ID,
                contents=rendered_prompt,
                config={"response_mime_type": "application/json"},
            )

            article_data = _parse_gemini_json(response.text)

            # --- Create Resource in a transaction ---
            slug = article_data.get("slug", f"ingredient-{ingredient_id}-101")
            existing_slug = session.execute(
                db.select(Resource).where(Resource.slug == slug)
            ).scalar()
            if existing_slug:
                slug = f"{slug}-{ingredient_id}"

            new_resource = Resource(
                slug=slug,
                title=article_data.get("title", f"101: {ingredient.name}"),
                summary=article_data.get("summary", ""),
                content_markdown=article_data.get("content_markdown", ""),
                tags=article_data.get("tags", ""),
                status="draft",
            )
            session.add(new_resource)
            session.flush()

            ingredient.primary_resource_id = new_resource.id
            session.commit()

            logger.info(
                f"[KnowledgeFactory] Article created: '{new_resource.title}' "
                f"(resource_id={new_resource.id})"
            )

            return {
                "status": "ready",
                "resource_id": new_resource.id,
                "title": new_resource.title,
                "image_prompt": article_data.get("image_prompt"),
            }

        except Exception as e:
            session.rollback()
            logger.error(f"[KnowledgeFactory] Article generation failed for ingredient {ingredient_id}: {e}")
            return {"status": "failed", "error": str(e)}


# ---------------------------------------------------------------------------
# 3. SCRIPT GENERATION — Social Media (Gemini 2.0 Flash)
# ---------------------------------------------------------------------------

PLATFORM_TEMPLATES = {
    "tiktok": "social/tiktok_persona.jinja2",
    "instagram": "social/insta_persona.jinja2",
}


def generate_script(recipe: Recipe, platform: str, session: Session) -> dict:
    """
    End-to-end pipeline: harmonize context → render prompt → call Gemini → return parsed JSON.
    """
    template_name = PLATFORM_TEMPLATES.get(platform)
    if not template_name:
        raise ValueError(f"Unknown platform: {platform}. Supported: {list(PLATFORM_TEMPLATES.keys())}")

    context = build_recipe_context(recipe, session)
    logger.info(f"[MediaHub] Built context for recipe '{recipe.title}' ({platform})")

    rendered_prompt = load_prompt(template_name, **context)

    client = _get_client()
    response = client.models.generate_content(
        model=MODEL_ID,
        contents=rendered_prompt,
        config={"response_mime_type": "application/json"},
    )

    try:
        result = _parse_gemini_json(response.text)
    except json.JSONDecodeError as e:
        logger.error(f"[MediaHub] Gemini returned invalid JSON: {e}")
        raise ValueError(f"Gemini returned invalid JSON: {response.text[:200]}")

    logger.info(f"[MediaHub] Script generated for '{recipe.title}' ({platform})")
    return result


# ---------------------------------------------------------------------------
# 4. FULL ORCHESTRATION — Called by routes
# ---------------------------------------------------------------------------

def generate_studio_pack(
    recipe_id: int,
    platform: str,
    storage_provider,
    app,
) -> dict:
    """
    Full orchestration: check cost guard → generate script → render video → upload → save record.
    Designed to run in a background thread.
    """
    from media_hub.video_engine import render_video

    template_name = PLATFORM_TEMPLATES.get(platform, "unknown")

    with app.app_context():
        session = db.session

        # --- Cost Guard ---
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
