from database.models import db, Ingredient, RecipeIngredient, IngredientEvaluation
import json

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
    Core merge logic.
    Moves all relations from loser to winner, merges aliases, and destroys loser.
    Returns dict: {'success': bool, 'message': str}
    """
    if winner_id == loser_id:
        return {"success": False, "message": "Cannot merge an ingredient into itself."}

    winner = db.session.get(Ingredient, winner_id)
    loser = db.session.get(Ingredient, loser_id)

    if not winner or not loser:
        return {"success": False, "message": "One or both ingredients not found."}

    try:
        # 1. Re-point RecipeIngredients
        # First, find if the recipe already has the winner. 
        # If so, we just remove the loser usage to prevent duplicate FK violations.
        usages = list(loser.recipe_ingredients)
        count_updated = 0
        count_conflicts = 0

        for usage in usages:
            recipe = usage.recipe
            conflict = next((ri for ri in recipe.ingredients if ri.ingredient_id == winner.id), None)
            
            if conflict:
                # The recipe already has the winner. We can't have two RecipeIngredients for the same ingredient in the same recipe (likely).
                # We'll just delete the loser usage.
                db.session.delete(usage)
                count_conflicts += 1
            else:
                # Safe to move
                usage.ingredient_id = winner.id
                count_updated += 1
                
        # 2. Merge Aliases
        # The prompt instructed: "Read the loser.name (and any strings in loser.aliases) and append them to the winner.aliases JSON array."
        winner_aliases = get_list_from_json(winner.aliases)
        loser_aliases = get_list_from_json(loser.aliases)
        
        # We need to add the loser's primary name as an alias
        strings_to_add = [loser.name] + loser_aliases
        
        for string in strings_to_add:
            # Add to winner if it's not the winner's actual name, and not already an alias
            if string and string.lower() != winner.name.lower() and string not in [a.lower() for a in winner_aliases]:
                winner_aliases.append(string)
                
        winner.aliases = json.dumps(winner_aliases)

        # 3. Destroy Loser 
        # (IngredientEvaluation has cascade="all, delete-orphan", so it dies with loser. 
        # If SubRecipe or PantryItem existed pointing to it, we'd need to re-point them here. 
        # But SubRecipe is linked via sub_recipe_id ON the ingredient, not pointing TO the ingredient.)
        db.session.delete(loser)

        db.session.commit()
        return {
            "success": True, 
            "message": f"Successfully merged {loser.name} into {winner.name}. Updated {count_updated} recipes, deleted {count_conflicts} duplicates."
        }
    except Exception as e:
        db.session.rollback()
        return {"success": False, "message": f"Merge failed due to a database error: {str(e)}"}
