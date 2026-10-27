"""Recipes in the database: matching an ingredient line to the pantry (used when a v2 recipe is saved,
services/recipe_v2/generate.py) and deleting recipes with everything that belongs to them."""

from database.models import db, Ingredient, IngredientAlias, Recipe
from ai_engine import get_pantry_id, normalize_ingredient_name
from services.ingredient_service import normalize_alias


def _extract_pre_resolved_id(ing) -> str | None:
    """Safely extract the LLM-provided pantry_id from an ingredient object."""
    if hasattr(ing, 'pantry_id'):
        return getattr(ing, 'pantry_id', None)
    if isinstance(ing, dict):
        return ing.get('pantry_id')
    return None


def _resolve_ingredient(ing) -> Ingredient | None:
    """
    Try to resolve an ingredient to a DB record, in this order:
    1. The pantry_id the LLM picked (must exist).
    2. An active ingredient with exactly this name.
    3. An alias with this name (IngredientAlias).
    Steps 2 and 3 are tried with the name as written, then without cooking
    qualifiers.
    4. Fuzzy name match via get_pantry_id.
    Returns the Ingredient ORM object or None.
    """
    pre_id = _extract_pre_resolved_id(ing)

    if pre_id:
        record = db.session.execute(
            db.select(Ingredient).where(Ingredient.food_id == pre_id)
        ).scalars().first()
        if record:
            return record

    name = ing.name if hasattr(ing, 'name') else ing.get('name', '')
    # The name as written, then without cooking qualifiers ("feta, crumbled" -> "feta")
    keys = list(dict.fromkeys(k for k in (normalize_alias(name), normalize_alias(normalize_ingredient_name(name))) if k))
    for key in keys:
        record = db.session.execute(
            db.select(Ingredient)
            .where(db.func.lower(Ingredient.name) == key, Ingredient.status == 'active')
        ).scalars().first()
        if record:
            return record

        alias = db.session.execute(
            db.select(IngredientAlias).where(IngredientAlias.name == key)
        ).scalars().first()
        if alias:
            return alias.ingredient

    food_id = get_pantry_id(name)
    if food_id:
        record = db.session.execute(
            db.select(Ingredient).where(Ingredient.food_id == food_id)
        ).scalars().first()
        if record:
            return record

    return None


def delete_recipes(recipe_ids: list[int]) -> int:
    """Delete recipes and everything that belongs to them. Returns the count.

    The ORM cascades on Recipe remove every child row (lines, steps, diets,
    evaluations, queue items, collection items, interactions).
    Ingredients that use a deleted recipe as their sub-recipe lose the link.
    """
    from sqlalchemy import update

    recipes = db.session.execute(
        db.select(Recipe).where(Recipe.id.in_(recipe_ids))
    ).scalars().all()
    if not recipes:
        return 0

    found_ids = [r.id for r in recipes]
    db.session.execute(
        update(Ingredient).where(Ingredient.sub_recipe_id.in_(found_ids)).values(sub_recipe_id=None)
    )
    for recipe in recipes:
        db.session.delete(recipe)
    db.session.commit()
    return len(recipes)
