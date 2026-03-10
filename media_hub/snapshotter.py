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
    "dark": {
        "fg": "#ffffff",
        "fg_muted": "rgba(255,255,255,0.70)",
        "fg_subtle": "rgba(255,255,255,0.40)",
        "bg": "#121212",
        "bg_lighter": "#1e1e1e",
        "bg_card": "#282828",
        "bg_gradient_start": "#121212",
        "bg_gradient_end": "#0a0a0a",
        "accent": "#1db954",
        "accent_dark": "#1aa34a",
        "accent_light": "#1ed760",
        "card_border": "rgba(255,255,255,0.08)",
        "card_bg": "rgba(255,255,255,0.05)",
    },
    "light": {
        "fg": "#202124",
        "fg_muted": "rgba(32,33,36,0.72)",
        "fg_subtle": "rgba(32,33,36,0.45)",
        "bg": "#ffffff",
        "bg_lighter": "#f8f9fa",
        "bg_card": "#ffffff",
        "bg_gradient_start": "#ffffff",
        "bg_gradient_end": "#f1f3f4",
        "accent": "#1a73e8",
        "accent_dark": "#1557b0",
        "accent_light": "#4285f4",
        "card_border": "rgba(0,0,0,0.08)",
        "card_bg": "rgba(0,0,0,0.02)",
    },
    "earthy": {
        "fg": "#3d2b1f",
        "fg_muted": "rgba(61,43,31,0.75)",
        "fg_subtle": "rgba(61,43,31,0.45)",
        "bg": "#f5ebe0",
        "bg_lighter": "#edddcc",
        "bg_card": "#faf3eb",
        "bg_gradient_start": "#f5ebe0",
        "bg_gradient_end": "#e6d5c3",
        "accent": "#606c38",
        "accent_dark": "#4a5328",
        "accent_light": "#7c8a4e",
        "card_border": "rgba(61,43,31,0.12)",
        "card_bg": "rgba(61,43,31,0.04)",
    },
    "contrast": {
        "fg": "#ffffff",
        "fg_muted": "rgba(255,255,255,0.85)",
        "fg_subtle": "rgba(255,255,255,0.55)",
        "bg": "#000000",
        "bg_lighter": "#111111",
        "bg_card": "#111111",
        "bg_gradient_start": "#000000",
        "bg_gradient_end": "#000000",
        "accent": "#ff3b30",
        "accent_dark": "#d62d23",
        "accent_light": "#ff6961",
        "card_border": "rgba(255,255,255,0.15)",
        "card_bg": "rgba(255,255,255,0.06)",
    },
    "pastel": {
        "fg": "#2d2d3f",
        "fg_muted": "rgba(45,45,63,0.70)",
        "fg_subtle": "rgba(45,45,63,0.42)",
        "bg": "#fef6f9",
        "bg_lighter": "#f8ecf1",
        "bg_card": "#fff5f8",
        "bg_gradient_start": "#fef6f9",
        "bg_gradient_end": "#f3e8f4",
        "accent": "#c084fc",
        "accent_dark": "#a855f7",
        "accent_light": "#d8b4fe",
        "card_border": "rgba(45,45,63,0.08)",
        "card_bg": "rgba(192,132,252,0.06)",
    },
    "mono": {
        "fg": "#1a1a1a",
        "fg_muted": "rgba(26,26,26,0.65)",
        "fg_subtle": "rgba(26,26,26,0.35)",
        "bg": "#f5f5f5",
        "bg_lighter": "#ebebeb",
        "bg_card": "#ffffff",
        "bg_gradient_start": "#f5f5f5",
        "bg_gradient_end": "#e8e8e8",
        "accent": "#404040",
        "accent_dark": "#262626",
        "accent_light": "#737373",
        "card_border": "rgba(0,0,0,0.10)",
        "card_bg": "rgba(0,0,0,0.03)",
    },
    "spicy": {
        "fg": "#ffffff",
        "fg_muted": "rgba(255,255,255,0.85)",
        "fg_subtle": "rgba(255,255,255,0.55)",
        "bg": "#1A1311",
        "bg_lighter": "#2d211e",
        "bg_card": "#261c1a",
        "bg_gradient_start": "#1A1311",
        "bg_gradient_end": "#110c0b",
        "accent": "#EF4444",
        "accent_dark": "#dc2626",
        "accent_light": "#f87171",
        "card_border": "rgba(255,255,255,0.12)",
        "card_bg": "rgba(255,255,255,0.06)",
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

        # Check for dual-layer structure robustly inside JS context
        has_dual = page.evaluate("() => document.querySelectorAll('.media-bg').length > 0")
        
        if not has_dual:
            png_bytes = page.screenshot(type="png", full_page=False)
            browser.close()
            return png_bytes
            
        # 1. Capture BG only (hide FG)
        page.evaluate("() => { document.querySelectorAll('.media-fg').forEach(el => el.style.visibility = 'hidden'); }")
        bg_png = page.screenshot(type="png", full_page=False)
        
        # 2. Capture FG only (show FG, hide BG)
        page.evaluate("""() => { 
            document.querySelectorAll('.media-fg').forEach(el => el.style.visibility = 'visible');
            document.querySelectorAll('.media-bg').forEach(el => el.style.visibility = 'hidden');
            
            // Critical: make all containers transparent so fg_png preserves alpha
            document.body.style.backgroundColor = 'transparent';
            document.body.style.background = 'transparent';
            
            const root = document.getElementById('fragment-root');
            if(root) {
                root.style.backgroundColor = 'transparent';
                root.style.background = 'transparent';
            }
        }""")
        fg_png = page.screenshot(type="png", full_page=False, omit_background=True)
        
        browser.close()
        return {"bg": bg_png, "fg": fg_png}


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


def _paginate_steps_dynamically(groups: list[dict], max_budget: int = 1650) -> list[list[dict]]:
    """
    Split step groups based on a mathematical height/pixel budget instead of random counts.
    TikTok viewport height is exactly 1920px.
    """
    import math
    pages: list[list[dict]] = []
    current_page: list[dict] = []
    
    # Mathematical Layout Constants calibrated for "Phase 1" UI cuts
    HEADER_COST = 180         # H2 main title, pt-20 top safe-box padding, mb-6 margin
    COMP_HEADER_COST = 50     # H3 subtitle margin and line-height
    STEP_BASE_COST = 80       # p-5 padding inside card, 1rem gap between cards, step border
    LINE_HEIGHT = 51          # 32px font * 1.6 leading
    CHARS_PER_LINE = 58       # Expanded horizon: Safe-box px-8 + narrower w-12 badge gives ~100px more width

    current_budget_used = HEADER_COST

    for group in groups:
        remaining = list(group["entries"])
        
        while remaining:
            if current_budget_used >= max_budget:
                pages.append(current_page)
                current_page = []
                current_budget_used = HEADER_COST
            
            chunk = []
            chunk_budget = current_budget_used
            
            # If we show component headers, charge for it on this page slice
            if len(groups) > 1 or group.get("component"):  
                chunk_budget += COMP_HEADER_COST
            
            while remaining:
                step = remaining[0]
                text = step.get("text", "")
                
                lines = math.ceil(len(text) / CHARS_PER_LINE)
                if lines == 0: lines = 1
                step_cost = STEP_BASE_COST + (lines * LINE_HEIGHT)
                
                # Rule: Force it to fit if the slide is totally empty (to prevent infinite loops on giant steps)
                if len(chunk) == 0 and len(current_page) == 0:
                    chunk_budget += step_cost
                    chunk.append(step)
                    remaining.pop(0)
                    continue
                    
                if chunk_budget + step_cost <= max_budget:
                    chunk_budget += step_cost
                    chunk.append(step)
                    remaining.pop(0)
                else:
                    break
                    
            if chunk:
                current_page.append({
                    "component": group.get("component"),
                    "entries": chunk
                })
                current_budget_used = chunk_budget
            else:
                # If we couldn't fit a single step but we have content on the page, force a new page
                pages.append(current_page)
                current_page = []
                current_budget_used = HEADER_COST
                
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
                fragment_type="shop",
                page=page_num,
                total_pages=total_pages,
                png_bytes=_screenshot_html(html),
            ))

        # ── 5. STEPS (with SmartOverflow + density) ──
        logger.info(f"[Snapshotter] Rendering Steps for recipe {recipe_id}")
        pages = _paginate_steps_dynamically(step_groups)

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
                "current_page_idx": page_num,
                "total_pages_count": total_pages,
            }
            html = _render_html(app, "steps.html", ctx)
            results.append(FragmentResult(
                fragment_type="steps",
                page=page_num,
                total_pages=total_pages,
                png_bytes=_screenshot_html(html),
            ))

        # ── 6. END ──
        logger.info(f"[Snapshotter] Rendering End for recipe {recipe_id}")
        html = _render_html(app, "end.html", base_ctx)
        results.append(FragmentResult(
            fragment_type="end",
            png_bytes=_screenshot_html(html),
        ))

        # ── 7. GALAXY ──
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

VALID_FRAGMENTS = {"hero", "comp", "nutrition", "nutr", "shop", "galaxy", "typography", "coreid", "ing-grid", "hook-social", "hook-cinematic", "end"}

def is_valid_fragment(name: str) -> bool:
    if name.startswith("step") and name[4:].isdigit(): return True
    return name in VALID_FRAGMENTS


def build_sandbox_context(recipe_id: int, fragment_name: str, app, storage_provider, theme_name="modern", debug=False, scale=1.0, page=1):
    """
    Builds the Jinja context needed to render a specific fragment in the browser sandbox.
    """
    from database.models import Recipe, db

    if not is_valid_fragment(fragment_name):
        raise ValueError(f"Unknown fragment: {fragment_name}. Valid core types: {VALID_FRAGMENTS} plus step[N]")

    # Typography specimen is a virtual fragment — no recipe data needed
    if fragment_name == "typography":
        with app.app_context():
            theme = get_theme(theme_name)
            return {"theme": theme, "debug": debug, "scale": scale}

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

        if fragment_name == "hero" or fragment_name == "end":
            return base_ctx

        if fragment_name == "comp":
            return {
                **base_ctx,
                "ingredient_groups": _build_ingredient_groups(recipe, storage_provider)
            }



        if fragment_name == "nutrition":
            return {**base_ctx, **_build_nutrition_context(recipe)}

        if fragment_name == "nutr":
            return {**base_ctx, "recipe": recipe, "wgt": recipe.total_weight_g or 1}

        if fragment_name == "shop":
            ingredient_groups = _build_ingredient_groups(recipe, storage_provider)
            total_items = sum(len(g["entries"]) for g in ingredient_groups)
            return {
                **base_ctx,
                "ingredient_groups": ingredient_groups,
                "show_component_headers": len(ingredient_groups) > 1,
                "item_count": total_items,
            }

        if fragment_name.startswith("step") and fragment_name[4:].isdigit():
            comp_idx = int(fragment_name[4:]) - 1
            step_groups = _build_step_groups(recipe)
            
            # Bound check
            if comp_idx < 0 or comp_idx >= len(step_groups):
                raise ValueError(f"Component index {comp_idx+1} out of bounds for recipe {recipe_id}")
                
            group = step_groups[comp_idx]
            pages = _paginate_steps_dynamically([group])
            total_pages = len(pages)
            page_idx = min(max(1, page), total_pages) - 1
            page_groups = pages[page_idx]
            
            total_items = sum(len(g["entries"]) for g in page_groups)
            page_indicator = f"{group['component']} {page_idx + 1}/{total_pages}" if total_pages > 1 else None
            
            return {
                **base_ctx,
                "step_groups": page_groups,
                "show_component_headers": len(step_groups) > 1,
                "item_count": total_items,
                "page_indicator": page_indicator,
                "current_page_idx": page_idx + 1,
                "total_pages_count": total_pages,
            }

        if fragment_name == "galaxy":
            graph_data = _build_galaxy_data(recipe, db.session, storage_provider)
            return {**base_ctx, "graph_data": graph_data}

        if fragment_name == "coreid":
            return {
                **base_ctx,
                "recipe_id": recipe.id,
                "protein_type": recipe.protein_type,
                "image_filename": recipe.image_filename,
            }

        if fragment_name == "ing-grid":
            ingredient_groups = _build_ingredient_groups(recipe, storage_provider)
            # Flatten all groups into a single list, images first for visual impact
            all_items = []
            for g in ingredient_groups:
                all_items.extend(g["entries"])
            # Sort: ingredients with images first, then alphabetically
            all_items.sort(key=lambda x: (0 if x["image_url"] else 1, x["name"]))
            # Cap at 9 for a clean 3x3 grid (or 8 for 2x4)
            grid_items = all_items[:9]
            return {
                **base_ctx,
                "grid_items": grid_items,
            }

        if fragment_name in ["hook-social", "hook-cinematic"]:
            hooks = recipe.social_hooks or {}
            hook_type = "social" if fragment_name == "hook-social" else "cinematic"
            return {
                **base_ctx,
                "hook_text": hooks.get(hook_type)
            }

        return base_ctx

def compile_custom_reel(recipe_id: int, sequence: list[dict], app, storage_provider) -> str:
    """
    Renders an ordered sequence of fragments into a final MP4 video using FFmpeg.
    Supports granular duration and motion effects (zoom_in, zoom_out, pan_right, pan_left).
    """
    import os
    import tempfile
    import subprocess
    import time
    from database.models import Recipe, db

    with app.app_context():
        recipe = db.session.get(Recipe, recipe_id)
        if not recipe:
            raise ValueError(f"Recipe {recipe_id} not found")

        rendered_frames = []
        
        for item in sequence:
            # Backwards compatibility if list contains strings instead of dicts
            if isinstance(item, str):
                frag_name = item
                effect = "none"
                duration = 2.0
            else:
                frag_name = item.get("id", "hero")
                effect = item.get("effect", "none")
                duration = float(item.get("duration", 2.0))

            base_temp_name = "steps" if frag_name.startswith("step") else frag_name
            ctx1 = build_sandbox_context(recipe_id, frag_name, app, storage_provider, theme_name="modern", page=1)
            total_pages = ctx1.get("total_pages_count", 1)

            for p_num in range(1, total_pages + 1):
                ctx = build_sandbox_context(recipe_id, frag_name, app, storage_provider, theme_name="modern", page=p_num)
                try:
                    html = _render_html(app, f"{base_temp_name}.html", ctx)
                    wait_selector = '[data-rendered="true"]' if base_temp_name == "galaxy" else None
                    result = _screenshot_html(html, wait_for_selector=wait_selector)
                    if isinstance(result, dict):
                        rendered_frames.append({
                            "bg": result["bg"],
                            "fg": result["fg"],
                            "effect": effect,
                            "duration": duration
                        })
                    else:
                        rendered_frames.append({
                            "png": result,
                            "effect": effect,
                            "duration": duration
                        })
                except Exception as e:
                    logger.error(f"[Snapshotter] Failed to screenshot {frag_name} p{p_num}: {e}")

        if not rendered_frames:
            raise ValueError("No frames generated for sequence")

        timestamp = int(time.time())
        vid_filename = f"reel_{recipe_id}_{timestamp}.mp4"
        out_dir = os.path.join(app.root_path, "static", "reels")
        os.makedirs(out_dir, exist_ok=True)
        vid_path = os.path.join(out_dir, vid_filename)

        with tempfile.TemporaryDirectory() as td:
            concat_list = []
            
            for i, frame in enumerate(rendered_frames):
                chunk_path = os.path.join(td, f"chunk_{i:04d}.mp4")
                
                has_fg = "bg" in frame
                if has_fg:
                    bg_path = os.path.join(td, f"bg_{i:04d}.png")
                    fg_path = os.path.join(td, f"fg_{i:04d}.png")
                    with open(bg_path, "wb") as f: f.write(frame["bg"])
                    with open(fg_path, "wb") as f: f.write(frame["fg"])
                    img_path = bg_path
                else:
                    img_path = os.path.join(td, f"frame_{i:04d}.png")
                    with open(img_path, "wb") as f: f.write(frame["png"])
                
                effect = frame["effect"]
                duration = frame["duration"]
                fps = 30
                frames_needed = int(duration * fps)
                
                # z=1.1 means viewport drops 99x175 pixels of safe room to pan/zoom
                safe_x = 95
                safe_y = 87
                
                # Determine zoompan effect string
                if effect == "zoom_in":
                    zp = f"zoompan=z='min(1.0 + (on/{frames_needed})*0.1, 1.1)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames_needed}:s=1080x1920:fps=30"
                elif effect == "zoom_out":
                    zp = f"zoompan=z='max(1.1 - (on/{frames_needed})*0.1, 1.0)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames_needed}:s=1080x1920:fps=30"
                elif effect == "pan_right":
                    zp = f"zoompan=z=1.1:x='(on/{frames_needed})*{safe_x}':y='{safe_y}':d={frames_needed}:s=1080x1920:fps=30"
                elif effect == "pan_left":
                    zp = f"zoompan=z=1.1:x='{safe_x}-(on/{frames_needed})*{safe_x}':y='{safe_y}':d={frames_needed}:s=1080x1920:fps=30"
                else:
                    zp = None

                if has_fg:
                    if not zp:
                        # Static Dual Layer
                        cmd = [
                            "ffmpeg", "-y",
                            "-loop", "1", "-i", bg_path,
                            "-loop", "1", "-i", fg_path,
                            "-filter_complex", "overlay",
                            "-t", str(duration),
                            "-c:v", "libx264", "-r", "30", "-pix_fmt", "yuv420p"
                        ]
                    else:
                        # Motion Dual Layer
                        cmd = [
                            "ffmpeg", "-y",
                            "-i", bg_path,
                            "-loop", "1", "-i", fg_path,
                            "-filter_complex", f"[0:v]{zp}[bg]; [bg][1:v]overlay=shortest=1",
                            "-c:v", "libx264", "-pix_fmt", "yuv420p"
                        ]
                else:
                    if not zp:
                        # Static Single Layer
                        cmd = [
                            "ffmpeg", "-y",
                            "-loop", "1", "-i", img_path,
                            "-t", str(duration),
                            "-c:v", "libx264", "-r", "30", "-pix_fmt", "yuv420p"
                        ]
                    else:
                        # Motion Single Layer
                        cmd = [
                            "ffmpeg", "-y",
                            "-i", img_path,
                            "-vf", zp,
                            "-c:v", "libx264", "-pix_fmt", "yuv420p"
                        ]
                
                cmd.append(chunk_path)
                logger.info(f"[VideoEngine] Rendering chunk {i}: {effect} for {duration}s")
                subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                concat_list.append(chunk_path)
                
            # Write exactly ordered list for FFmpeg Demuxer
            concat_txt_path = os.path.join(td, "concat.txt")
            with open(concat_txt_path, "w") as f:
                for chunk in concat_list:
                    # FFmpeg concat file expects POSIX path strings
                    f.write(f"file '{chunk}'\n")
                    
            logger.info(f"[VideoEngine] Stitching {len(concat_list)} clips into master reel...")
            final_cmd = [
                "ffmpeg", "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", concat_txt_path,
                "-c", "copy",
                vid_path
            ]
            subprocess.run(final_cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
        logger.info(f"[VideoEngine] Reel Build Complete! Saved to: {vid_path}")
        return f"/static/reels/{vid_filename}"
