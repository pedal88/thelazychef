from database.models import db, Ingredient, IngredientAlias
from services.nutrition_service import calculate_nutritional_totals

def normalize_alias(name: str) -> str:
    return " ".join((name or "").split()).lower()


def add_alias(ingredient: Ingredient, name: str) -> bool:
    """Add an alias to an ingredient. Returns False when it is skipped: empty,
    the ingredient's own name, or already an alias of some ingredient."""
    alias = normalize_alias(name)
    if not alias or alias == normalize_alias(ingredient.name):
        return False
    exists = db.session.execute(
        db.select(IngredientAlias.id).where(IngredientAlias.name == alias)
    ).first()
    if exists:
        return False
    db.session.add(IngredientAlias(ingredient=ingredient, name=alias))
    db.session.flush()
    return True


def merge_ingredients(winner_id: int, loser_id: int) -> dict:
    """
    Merge the loser ingredient into the winner and delete the loser.

    Every recipe line that used the loser now uses the winner. Lines are
    moved, never deleted or summed: a recipe may use the same ingredient on
    two lines (different amounts or units), so nothing is lost. The loser's
    aliases move to the winner and its name becomes one, and recipe
    nutrition is recalculated for the recipes that changed.

    Returns dict: {'success': bool, 'message': str}
    """
    if winner_id == loser_id:
        return {"success": False, "message": "Cannot merge an ingredient into itself."}

    winner = db.session.get(Ingredient, winner_id)
    loser = db.session.get(Ingredient, loser_id)

    if not winner or not loser:
        return {"success": False, "message": "One or both ingredients not found."}

    try:
        # 1. Move every recipe line. Assigning through the relationship also
        #    removes the line from loser.recipe_ingredients, so deleting the
        #    loser below does not touch it.
        affected_recipe_ids = set()
        moved = 0
        for usage in list(loser.recipe_ingredients):
            usage.ingredient = winner
            affected_recipe_ids.add(usage.recipe_id)
            moved += 1

        # 2. Keep a sub-recipe link if only the loser had one
        if winner.sub_recipe_id is None and loser.sub_recipe_id is not None:
            winner.sub_recipe_id = loser.sub_recipe_id

        # 3. Move the loser's aliases, then add the loser's own name
        winner_name = normalize_alias(winner.name)
        for entry in list(loser.alias_entries):
            if entry.name == winner_name:
                db.session.delete(entry)
            else:
                entry.ingredient = winner
        db.session.flush()
        add_alias(winner, loser.name)

        # 4. Delete the loser (its IngredientEvaluation cascades with it)
        loser_name = loser.name
        db.session.delete(loser)
        db.session.commit()

        # 5. Nutrition depends on the ingredient, so recalculate what changed
        for recipe_id in affected_recipe_ids:
            try:
                calculate_nutritional_totals(recipe_id)
            except Exception as e:
                print(f"Nutrition recalculation failed for recipe {recipe_id}: {e}")

        return {
            "success": True,
            "message": f"Merged {loser_name} into {winner.name}. Moved {moved} recipe lines in {len(affected_recipe_ids)} recipes."
        }
    except Exception as e:
        db.session.rollback()
        return {"success": False, "message": f"Merge failed due to a database error: {str(e)}"}
