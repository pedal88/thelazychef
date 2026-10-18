import json

from database.models import db, Ingredient
from services.nutrition_service import calculate_nutritional_totals

def get_list_from_json(field_value):
    """Safely parse a JSON string into a list."""
    if not field_value:
        return []
    try:
        parsed = json.loads(field_value)
        if isinstance(parsed, list):
            return parsed
        return [str(parsed)]
    except (json.JSONDecodeError, TypeError):
        # If it's a raw string (e.g. from an old format or just bad data), wrap it
        return [str(field_value)]

def merge_ingredients(winner_id: int, loser_id: int) -> dict:
    """
    Merge the loser ingredient into the winner and delete the loser.

    Every recipe line that used the loser now uses the winner. Lines are
    moved, never deleted or summed: a recipe may use the same ingredient on
    two lines (different amounts or units), so nothing is lost. The loser's
    name and aliases become aliases on the winner, and recipe nutrition is
    recalculated for the recipes that changed.

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

        # 3. Merge aliases (case-insensitive, never the winner's own name)
        winner_aliases = get_list_from_json(winner.aliases)
        known = {a.lower() for a in winner_aliases} | {winner.name.lower()}
        for alias in [loser.name] + get_list_from_json(loser.aliases):
            if alias and alias.lower() not in known:
                winner_aliases.append(alias)
                known.add(alias.lower())
        winner.aliases = json.dumps(winner_aliases)

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
