"""
media_hub/snapshotter.py — Lego-Fragment Snapshotter Engine

Renders Jinja2 fragment templates into 1080×1920 PNG images using Playwright.
Supports SmartOverflow: auto-paginating Ingredients / Steps when content exceeds
the safe zone.

Architecture:
    1. build_fragment_context()  — extracts all recipe data into template-friendly dicts
    2. render_fragment()         — renders one HTML template → PNG via headless Chromium
    3. render_recipe_fragments() — orchestrates the full manifest for a recipe
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Optional

from flask import Flask
from jinja2 import Environment, FileSystemLoader
from playwright.sync_api import sync_playwright

logger = logging.getLogger("media_hub.snapshotter")

# ---------------------------------------------------------------------------
# Data Structures
# ---------------------------------------------------------------------------

@dataclass
class FragmentResult:
    """One rendered fragment image."""
    fragment_type: str          # hero, meta, nutrition, ingredients, steps, galaxy
    page: int = 1               # 1-indexed page number
    total_pages: int = 1        # total pages for this fragment type
    component: Optional[str] = None  # dish component name (for ingredients/steps)
    png_bytes: bytes = field(default=b"", repr=False)


# ---------------------------------------------------------------------------
# Safe zone: how many items fit per 1920px page (conservative estimates)
# ---------------------------------------------------------------------------

MAX_INGREDIENTS_PER_PAGE = 14
MAX_STEPS_PER_PAGE = 6


# ---------------------------------------------------------------------------
# THEMES — injected as CSS custom properties via base_fragment.html
# ---------------------------------------------------------------------------

THEMES: dict[str, dict[str, str]] = {
    "classic": {
        "fg": "#1e1e1e",
        "fg_muted": "rgba(30,30,30,0.75)",
        "fg_subtle": "rgba(30,30,30,0.45)",
        "bg": "#faf5ef",
        "bg_lighter": "#f0e9df",
        "bg_card": "#faf5ef",
        "bg_gradient_start": "#faf5ef",
        "bg_gradient_end": "#e8dfd3",
        "accent": "#b45309",
        "accent_dark": "#92400e",
        "accent_light": "#d97706",
        "card_border": "rgba(30,30,30,0.10)",
        "card_bg": "rgba(30,30,30,0.04)",
    },
    "modern": {
        "fg": "#ffffff",
        "fg_muted": "rgba(255,255,255,0.60)",
        "fg_subtle": "rgba(255,255,255,0.40)",
        "bg": "#0f172a",
        "bg_lighter": "#1e293b",
        "bg_card": "#1e293b",
        "bg_gradient_start": "#0f172a",
        "bg_gradient_end": "#0c1222",
        "accent": "#f97316",
        "accent_dark": "#ea580c",
        "accent_light": "#fdba74",
        "card_border": "rgba(255,255,255,0.10)",
        "card_bg": "rgba(255,255,255,0.05)",
    },
}

DEFAULT_THEME = "modern"

def get_theme(name: str) -> dict[str, str]:
    """Return a theme dict by name, falling back to modern."""
    return THEMES.get(name, THEMES[DEFAULT_THEME])

# ---------------------------------------------------------------------------
# 1. CONTEXT BUILDERS
# ---------------------------------------------------------------------------

def _format_amount(amount: float) -> str:
    """Format ingredient amount without trailing decimals."""
    if amount is None:
        return ""
    if amount == int(amount):
        return str(int(amount))
    return f"{amount:.1f}"


def _build_ingredient_groups(recipe, storage_provider=None) -> list[dict]:
    """Group ingredients by component, preserving order."""
    from collections import OrderedDict
    groups: OrderedDict[str, list] = OrderedDict()

    for ri in recipe.ingredients:
        comp = ri.component or "Main"
        if comp not in groups:
            groups[comp] = []

        # Get ingredient image URL (stored directly on Ingredient model)
        image_url = None
        if ri.ingredient and ri.ingredient.image_url:
            image_url = ri.ingredient.image_url

        groups[comp].append({
            "name": ri.ingredient.name if ri.ingredient else "Unknown",
            "amount": ri.amount,
            "amount_display": _format_amount(ri.amount),
            "unit": ri.unit or "",
            "image_url": image_url,
        })

    return [{"component": comp, "entries": items} for comp, items in groups.items()]


def _build_step_groups(recipe) -> list[dict]:
    """Group instructions by component, preserving order."""
    from collections import OrderedDict
    groups: OrderedDict[str, list] = OrderedDict()

    sorted_instructions = sorted(
        recipe.instructions,
        key=lambda i: (i.component or "Main", i.global_order_index or i.step_number or 0),
    )

    step_counter = 1
    for instr in sorted_instructions:
        comp = instr.component or "Main"
        if comp not in groups:
            groups[comp] = []

        groups[comp].append({
            "number": step_counter,
            "text": instr.text,
            "phase": instr.phase,
            "estimated_minutes": instr.estimated_minutes,
        })
        step_counter += 1

    return [{"component": comp, "entries": items} for comp, items in groups.items()]


def _build_nutrition_context(recipe) -> dict:
    """Extract nutrition facts into template-friendly dict."""
    base_srv = recipe.base_servings or 4

    def per_serving(total: Optional[float]) -> str:
        if total is None:
            return "—"
        val = total / base_srv
        return str(round(val)) if val >= 1 else f"{val:.1f}"

    calories_total = recipe.total_calories or 0
    calories_per = round(calories_total / base_srv) if calories_total else 0
    # Rough % of 2000 kcal daily target
    calories_pct = min(100, round((calories_per / 2000) * 100)) if calories_per else 0

    detail_rows = []
    if recipe.total_saturated_fat is not None:
        detail_rows.append({"label": "Saturated Fat", "value": f"{per_serving(recipe.total_saturated_fat)}g"})
    if recipe.total_fiber is not None:
        detail_rows.append({"label": "Fiber", "value": f"{per_serving(recipe.total_fiber)}g"})
    if recipe.total_sugar is not None:
        detail_rows.append({"label": "Sugar", "value": f"{per_serving(recipe.total_sugar)}g"})
    if recipe.total_sodium_mg is not None:
        detail_rows.append({"label": "Sodium", "value": f"{per_serving(recipe.total_sodium_mg)}mg"})
    if recipe.total_cholesterol_mg is not None:
        detail_rows.append({"label": "Cholesterol", "value": f"{per_serving(recipe.total_cholesterol_mg)}mg"})
    if recipe.total_calcium_mg is not None:
        detail_rows.append({"label": "Calcium", "value": f"{per_serving(recipe.total_calcium_mg)}mg"})

    return {
        "calories": calories_per,
        "calories_pct": calories_pct,
        "protein": per_serving(recipe.total_protein),
        "carbs": per_serving(recipe.total_carbs),
        "fat": per_serving(recipe.total_fat),
        "detail_rows": detail_rows,
    }


# ---------------------------------------------------------------------------
# 2. HTML RENDERING (Jinja2 → string)
# ---------------------------------------------------------------------------

def _render_html(app: Flask, template_name: str, context: dict) -> str:
    """Render a fragment template to an HTML string using the app's Jinja env."""
    env = Environment(
        loader=FileSystemLoader(app.template_folder),
        autoescape=True,
    )
    template = env.get_template(f"fragments/{template_name}")
    return template.render(**context)


# ---------------------------------------------------------------------------
# 3. SCREENSHOT (HTML → PNG via Playwright)
# ---------------------------------------------------------------------------

def _screenshot_html(html: str, wait_for_selector: Optional[str] = None) -> bytes:
    """
    Open HTML in headless Chromium at 1080×1920 and screenshot.

    Args:
        html: Full HTML string.
        wait_for_selector: Optional CSS selector to wait for before screenshotting
                           (used for Galaxy D3 rendering).

    Returns:
        PNG bytes.
    """
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1080, "height": 1920})
        page.set_content(html, wait_until="networkidle")

        if wait_for_selector:
            try:
                page.wait_for_selector(wait_for_selector, timeout=15000)
            except Exception:
                logger.warning(f"Timed out waiting for selector: {wait_for_selector}")

        # Short extra wait for fonts / Tailwind to settle
        page.wait_for_timeout(500)

        png_bytes = page.screenshot(type="png", full_page=False)
        browser.close()
        return png_bytes


# ---------------------------------------------------------------------------
# 4. SMART OVERFLOW — auto-paginate Ingredients / Steps
# ---------------------------------------------------------------------------

def _paginate_groups(
    groups: list[dict],
    max_items_per_page: int,
) -> list[list[dict]]:
    """
    Split ingredient/step groups across pages while keeping components together
    where possible.

    Returns:
        List of pages, where each page is a list of group dicts.
    """
    pages: list[list[dict]] = []
    current_page: list[dict] = []
    current_count = 0

    for group in groups:
        entries = group["entries"]

        if current_count + len(entries) <= max_items_per_page:
            # Entire component fits on current page
            current_page.append(group)
            current_count += len(entries)
        else:
            # Need to split
            remaining = entries
            while remaining:
                space = max_items_per_page - current_count
                if space <= 0:
                    pages.append(current_page)
                    current_page = []
                    current_count = 0
                    space = max_items_per_page

                chunk = remaining[:space]
                remaining = remaining[space:]
                current_page.append({
                    "component": group["component"],
                    "entries": chunk,
                })
                current_count += len(chunk)

                if remaining:
                    pages.append(current_page)
                    current_page = []
                    current_count = 0

    if current_page:
        pages.append(current_page)

    return pages


# ---------------------------------------------------------------------------
# 5. MAIN ORCHESTRATOR — render_recipe_fragments()
# ---------------------------------------------------------------------------

def render_recipe_fragments(
    recipe_id: int,
    app: Flask,
    storage_provider=None,
    theme_name: str = DEFAULT_THEME,
) -> list[FragmentResult]:
    """
    Render all fragment PNGs for a recipe.

    Returns a list of FragmentResult objects with PNG bytes.
    """
    from database.models import Recipe

    with app.app_context():
        from database.models import db
        recipe = db.session.get(Recipe, recipe_id)
        if not recipe:
            raise ValueError(f"Recipe {recipe_id} not found")

        results: list[FragmentResult] = []
        theme = get_theme(theme_name)

        # --- Shared context ---
        from services.storage_service import GoogleCloudStorageProvider
        is_gcs = isinstance(storage_provider, GoogleCloudStorageProvider)
        image_url = None
        if recipe.image_filename and is_gcs:
            image_url = f"https://storage.googleapis.com/{storage_provider.bucket_name}/recipes/{recipe.image_filename}"

        # Pre-calculate counts for density awareness
        ingredient_groups = _build_ingredient_groups(recipe, storage_provider)
        step_groups = _build_step_groups(recipe)
        total_ingredients = sum(len(g["entries"]) for g in ingredient_groups)
        total_steps = sum(len(g["entries"]) for g in step_groups)
        has_multiple_components = len(ingredient_groups) > 1

        base_ctx = {
            "title": recipe.title,
            "cuisine": recipe.cuisine,
            "difficulty": recipe.difficulty,
            "prep_time_mins": recipe.prep_time_mins,
            "base_servings": recipe.base_servings or 4,
            "image_url": image_url,
            "diets": recipe.diets_list,
            "meal_types": recipe.meal_types_list,
            "chef_name": recipe.chef.name if recipe.chef else None,
            "theme": theme,
            "debug": False,
        }

        # ── 1. HERO ──
        logger.info(f"[Snapshotter] Rendering Hero for recipe {recipe_id}")
        html = _render_html(app, "hero.html", base_ctx)
        results.append(FragmentResult(
            fragment_type="hero",
            png_bytes=_screenshot_html(html),
        ))

        # ── 2. META ──
        logger.info(f"[Snapshotter] Rendering Meta for recipe {recipe_id}")
        meta_ctx = {
            **base_ctx,
            "compact_meta": total_ingredients > 15,
        }
        html = _render_html(app, "meta.html", meta_ctx)
        results.append(FragmentResult(
            fragment_type="meta",
            png_bytes=_screenshot_html(html),
        ))

        # ── 3. NUTRITION ──
        logger.info(f"[Snapshotter] Rendering Nutrition for recipe {recipe_id}")
        nutrition_ctx = {**base_ctx, **_build_nutrition_context(recipe)}
        html = _render_html(app, "nutrition.html", nutrition_ctx)
        results.append(FragmentResult(
            fragment_type="nutrition",
            png_bytes=_screenshot_html(html),
        ))

        # ── 4. INGREDIENTS (with SmartOverflow + density) ──
        logger.info(f"[Snapshotter] Rendering Ingredients for recipe {recipe_id}")
        pages = _paginate_groups(ingredient_groups, MAX_INGREDIENTS_PER_PAGE)

        for page_idx, page_groups in enumerate(pages):
            page_num = page_idx + 1
            total_pages = len(pages)
            page_indicator = f"Ingredients {page_num}/{total_pages}" if total_pages > 1 else None
            page_item_count = sum(len(g["entries"]) for g in page_groups)

            ctx = {
                **base_ctx,
                "ingredient_groups": page_groups,
                "show_component_headers": has_multiple_components,
                "page_indicator": page_indicator,
                "item_count": page_item_count,
            }
            html = _render_html(app, "ingredients.html", ctx)
            results.append(FragmentResult(
                fragment_type="ingredients",
                page=page_num,
                total_pages=total_pages,
                png_bytes=_screenshot_html(html),
            ))

        # ── 5. STEPS (with SmartOverflow + density) ──
        logger.info(f"[Snapshotter] Rendering Steps for recipe {recipe_id}")
        pages = _paginate_groups(step_groups, MAX_STEPS_PER_PAGE)

        for page_idx, page_groups in enumerate(pages):
            page_num = page_idx + 1
            total_pages = len(pages)
            page_indicator = f"Steps {page_num}/{total_pages}" if total_pages > 1 else None
            page_item_count = sum(len(g["entries"]) for g in page_groups)

            ctx = {
                **base_ctx,
                "step_groups": page_groups,
                "show_component_headers": has_multiple_components,
                "page_indicator": page_indicator,
                "item_count": page_item_count,
            }
            html = _render_html(app, "steps.html", ctx)
            results.append(FragmentResult(
                fragment_type="steps",
                page=page_num,
                total_pages=total_pages,
                png_bytes=_screenshot_html(html),
            ))

        # ── 6. GALAXY ──
        logger.info(f"[Snapshotter] Rendering Galaxy for recipe {recipe_id}")
        try:
            graph_data = _build_galaxy_data(recipe, db.session, storage_provider)
            galaxy_ctx = {**base_ctx, "graph_data": graph_data}
            html = _render_html(app, "galaxy.html", galaxy_ctx)
            results.append(FragmentResult(
                fragment_type="galaxy",
                png_bytes=_screenshot_html(html, wait_for_selector='[data-rendered="true"]'),
            ))
        except Exception as e:
            logger.warning(f"[Snapshotter] Galaxy rendering failed: {e}")

        logger.info(f"[Snapshotter] Rendered {len(results)} fragments for recipe {recipe_id}")
        return results


def _build_galaxy_data(recipe, session, storage_provider=None) -> dict:
    """
    Build the graph data for the Flavor Galaxy fragment.
    Mirrors the /api/graph/orbital/<recipe_id> endpoint logic.
    """
    from database.models import Recipe
    from sqlalchemy import or_

    from services.storage_service import GoogleCloudStorageProvider
    is_gcs = isinstance(storage_provider, GoogleCloudStorageProvider)

    def _recipe_image(r):
        if not r.image_filename or not is_gcs:
            return None
        return f"https://storage.googleapis.com/{storage_provider.bucket_name}/recipes/{r.image_filename}"

    nodes = [{
        "id": f"recipe_{recipe.id}",
        "name": recipe.title,
        "group": "center",
        "image": _recipe_image(recipe),
    }]
    links = []

    c_attr = recipe.cuisine
    p_attr = recipe.protein_type

    if c_attr:
        nodes.append({"id": f"attr_cuisine_{c_attr}", "name": c_attr, "group": "cuisine"})
        links.append({"source": f"attr_cuisine_{c_attr}", "target": f"recipe_{recipe.id}", "weight": 5.0})

    if p_attr:
        nodes.append({"id": f"attr_protein_{p_attr}", "name": p_attr, "group": "protein"})
        links.append({"source": f"attr_protein_{p_attr}", "target": f"recipe_{recipe.id}", "weight": 5.0})

    if c_attr or p_attr:
        from database.models import db
        conditions = []
        if c_attr:
            conditions.append(Recipe.cuisine == c_attr)
        if p_attr:
            conditions.append(Recipe.protein_type == p_attr)

        siblings = db.session.execute(
            db.select(Recipe).where(
                Recipe.id != recipe.id,
                Recipe.status == "approved",
                or_(*conditions),
            ).limit(10)
        ).scalars().all()

        for sib in siblings:
            nodes.append({
                "id": f"recipe_{sib.id}",
                "name": sib.title,
                "group": "sibling",
                "image": _recipe_image(sib),
            })
            matches_c = (sib.cuisine == c_attr) and c_attr
            matches_p = (sib.protein_type == p_attr) and p_attr

            if matches_c:
                links.append({"source": f"recipe_{sib.id}", "target": f"attr_cuisine_{c_attr}", "weight": 2.0})
            if matches_p:
                links.append({"source": f"recipe_{sib.id}", "target": f"attr_protein_{p_attr}", "weight": 2.0})

    return {"nodes": nodes, "links": links}


# ---------------------------------------------------------------------------
# 7. SANDBOX — build context for browser-based design iteration
# ---------------------------------------------------------------------------

VALID_FRAGMENTS = {"hero", "meta", "nutrition", "ingredients", "steps", "galaxy"}


def build_sandbox_context(recipe_id: int, fragment_name: str, app, storage_provider, theme_name="modern", debug=False, scale=1.0):
    """
    Builds the Jinja context needed to render a specific fragment in the browser sandbox.
    """
    from database.models import Recipe, db

    if fragment_name not in VALID_FRAGMENTS:
        raise ValueError(f"Unknown fragment: {fragment_name}. Valid: {VALID_FRAGMENTS}")

    with app.app_context():
        recipe = db.session.get(Recipe, recipe_id)
        if not recipe:
            raise ValueError(f"Recipe {recipe_id} not found")

        from services.storage_service import GoogleCloudStorageProvider
        is_gcs = isinstance(storage_provider, GoogleCloudStorageProvider)
        image_url = None
        if recipe.image_filename and is_gcs:
            image_url = f"https://storage.googleapis.com/{storage_provider.bucket_name}/recipes/{recipe.image_filename}"

        theme = get_theme(theme_name)

        base_ctx = {
            "title": recipe.title,
            "cuisine": recipe.cuisine,
            "difficulty": recipe.difficulty,
            "prep_time_mins": recipe.prep_time_mins,
            "base_servings": recipe.base_servings or 4,
            "image_url": image_url,
            "diets": recipe.diets_list,
            "meal_types": recipe.meal_types_list,
            "chef_name": recipe.chef.name if recipe.chef else None,
            "theme": theme,
            "debug": debug,
            "scale": scale,
        }

        if fragment_name == "hero":
            return base_ctx

        if fragment_name == "meta":
            ingredient_groups = _build_ingredient_groups(recipe, storage_provider)
            total_ingredients = sum(len(g["entries"]) for g in ingredient_groups)
            return {**base_ctx, "compact_meta": total_ingredients > 15}

        if fragment_name == "nutrition":
            return {**base_ctx, **_build_nutrition_context(recipe)}

        if fragment_name == "ingredients":
            ingredient_groups = _build_ingredient_groups(recipe, storage_provider)
            total_items = sum(len(g["entries"]) for g in ingredient_groups)
            return {
                **base_ctx,
                "ingredient_groups": ingredient_groups,
                "show_component_headers": len(ingredient_groups) > 1,
                "item_count": total_items,
            }

        if fragment_name == "steps":
            step_groups = _build_step_groups(recipe)
            total_items = sum(len(g["entries"]) for g in step_groups)
            return {
                **base_ctx,
                "step_groups": step_groups,
                "show_component_headers": len(step_groups) > 1,
                "item_count": total_items,
            }

        if fragment_name == "galaxy":
            graph_data = _build_galaxy_data(recipe, db.session, storage_provider)
            return {**base_ctx, "graph_data": graph_data}

        return base_ctx
