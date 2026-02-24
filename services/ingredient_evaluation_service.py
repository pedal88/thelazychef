"""Ingredient LLM-as-a-Judge QA pipeline.

Mirrors the recipe evaluation_service.py pattern exactly:
- TypedDict schema enforces Chain-of-Thought ordering (reasoning before score).
- Multimodal: fetches the ingredient image from its URL and passes it to Gemini.
- score_commonness is captured but excluded from total_score average.
- Auto-promotes pending ingredients to 'active' when total_score >= 85.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import requests
import typing_extensions as typing
from dotenv import load_dotenv
from google import genai
from google.genai import types
from io import BytesIO
from jinja2 import Environment, FileSystemLoader
from PIL import Image

from database.models import db, Ingredient, IngredientEvaluation

# ---------------------------------------------------------------------------
# Infrastructure setup (mirrors evaluation_service.py exactly)
# ---------------------------------------------------------------------------

PROMPTS_DIR = Path(__file__).parent.parent / "data" / "prompts"
_jinja_env = Environment(loader=FileSystemLoader(str(PROMPTS_DIR)))

load_dotenv()
_api_key = os.getenv("GOOGLE_API_KEY")
if not _api_key:
    raise ValueError("GOOGLE_API_KEY environment variable is missing.")

client = genai.Client(api_key=_api_key)


# ---------------------------------------------------------------------------
# TypedDict Schema — reasoning keys MUST precede their score keys so the LLM
# generates Chain-of-Thought before committing to a number.
# ---------------------------------------------------------------------------

class IngredientEvaluationSchema(typing.TypedDict):
    """Strict schema for LLM ingredient QA output with enforced Chain-of-Thought."""
    reasoning_image:     str
    score_image:         int
    reasoning_nutrition: str
    score_nutrition:     int
    reasoning_taxonomy:  str
    score_taxonomy:      int
    reasoning_utility:   str
    score_utility:       int
    reasoning_commonness: str
    score_commonness:    int
    total_score:         float


# ---------------------------------------------------------------------------
# Core evaluation function
# ---------------------------------------------------------------------------

def evaluate_ingredient(ingredient_id: int) -> dict:
    """Run the multimodal LLM-as-a-Judge pipeline on a single ingredient.

    Steps:
        1. Fetch the Ingredient ORM object.
        2. Build a flattened dict payload for the prompt.
        3. Render the Jinja2 prompt template.
        4. Attempt to load the ingredient image via its URL (PIL).
        5. Call Gemini with structured JSON output.
        6. Parse the response, compute total_score, persist to DB.
        7. Auto-promote status to 'active' if score >= 85 and status == 'pending'.

    Args:
        ingredient_id: Primary key of the Ingredient to evaluate.

    Returns:
        dict with keys: status, total_score, auto_promoted.

    Raises:
        ValueError on ingredient-not-found or API failure.
    """
    ing = db.session.get(Ingredient, ingredient_id)
    if not ing:
        raise ValueError(f"Ingredient with ID {ingredient_id} not found.")

    # ── Build text payload ──────────────────────────────────────────
    ing_dict = {
        "id": ing.id,
        "food_id": ing.food_id,
        "name": ing.name,
        "main_category": ing.main_category,
        "sub_category": ing.sub_category,
        "default_unit": ing.default_unit,
        "average_g_per_unit": ing.average_g_per_unit,
        "is_staple": ing.is_staple,
        "tags": ing.tags,
        "aliases": ing.aliases,
        "status": ing.status,
        # Nutrition
        "calories_per_100g": ing.calories_per_100g,
        "protein_per_100g": ing.protein_per_100g,
        "carbs_per_100g": ing.carbs_per_100g,
        "fat_per_100g": ing.fat_per_100g,
        "fiber_per_100g": ing.fiber_per_100g,
        "sugar_per_100g": ing.sugar_per_100g,
        "sodium_mg_per_100g": ing.sodium_mg_per_100g,
        "image_url": ing.image_url,
        "image_prompt": ing.image_prompt,
    }
    ing_json_str = json.dumps(ing_dict, indent=2)

    # ── Render Jinja2 prompt ────────────────────────────────────────
    try:
        template = _jinja_env.get_template("ingredient_qa/ingredient_evaluator.jinja2")
        prompt = template.render(ingredient_json=ing_json_str)
    except Exception as exc:
        raise ValueError(f"Failed to render ingredient QA template: {exc}") from exc

    # ── Load image via PIL (handles GCS URLs and missing images) ────
    image_obj: Image.Image | None = None
    if ing.image_url:
        try:
            if ing.image_url.startswith("http"):
                response = requests.get(ing.image_url, timeout=10)
                response.raise_for_status()
                image_obj = Image.open(BytesIO(response.content))
            else:
                # Local relative path (legacy)
                local_path = Path(ing.image_url)
                if local_path.exists():
                    image_obj = Image.open(local_path)
        except Exception as exc:
            print(f"⚠️  Could not load image for ingredient {ingredient_id}: {exc}")
            image_obj = None

    if image_obj:
        payload = [prompt, image_obj]
    else:
        prompt += (
            "\n\n[SYSTEM NOTE: NO IMAGE PROVIDED. "
            "Set reasoning_image to 'No image available' and score_image to 0.]"
        )
        payload = [prompt]

    # ── Call Gemini with structured output ─────────────────────────
    try:
        api_response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=payload,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=IngredientEvaluationSchema,
                temperature=0.1,  # Low temperature for deterministic analytical scoring
            ),
        )
    except Exception as exc:
        raise ValueError(f"Gemini API call failed during ingredient QA: {exc}") from exc

    # ── Parse response ─────────────────────────────────────────────
    try:
        eval_data = api_response.parsed if api_response.parsed else json.loads(api_response.text)
        if hasattr(eval_data, "__dict__"):
            eval_data = vars(eval_data)
        elif not isinstance(eval_data, dict):
            eval_data = dict(eval_data)
    except Exception as exc:
        raise ValueError(f"Could not parse LLM JSON response: {exc}") from exc

    # ── Compute total_score (excludes score_commonness) ────────────
    scored_keys = ("score_image", "score_nutrition", "score_taxonomy", "score_utility")
    scored_values = [eval_data.get(k, 0) for k in scored_keys]
    computed_total = sum(scored_values) / len(scored_values)

    # ── Persist to DB (upsert pattern) ─────────────────────────────
    if ing.evaluation:
        db.session.delete(ing.evaluation)
        db.session.flush()  # Ensure the old record is gone before inserting the new one

    evaluation = IngredientEvaluation(
        ingredient_id=ing.id,
        score_image=eval_data.get("score_image", 0),
        score_nutrition=eval_data.get("score_nutrition", 0),
        score_taxonomy=eval_data.get("score_taxonomy", 0),
        score_utility=eval_data.get("score_utility", 0),
        score_commonness=eval_data.get("score_commonness", 0),
        total_score=round(computed_total, 1),
        evaluation_details={
            "reasoning_image":      eval_data.get("reasoning_image", ""),
            "reasoning_nutrition":  eval_data.get("reasoning_nutrition", ""),
            "reasoning_taxonomy":   eval_data.get("reasoning_taxonomy", ""),
            "reasoning_utility":    eval_data.get("reasoning_utility", ""),
            "reasoning_commonness": eval_data.get("reasoning_commonness", ""),
        },
    )
    db.session.add(evaluation)

    # ── Auto-promote pending → active if score >= 85 ───────────────
    auto_promoted = False
    if computed_total >= 85.0 and ing.status == "pending":
        ing.status = "active"
        auto_promoted = True
        print(f"✅ Auto-promoted ingredient #{ingredient_id} ({ing.name}) from 'pending' → 'active'")

    db.session.commit()

    return {
        "status": "success",
        "total_score": evaluation.total_score,
        "auto_promoted": auto_promoted,
    }
