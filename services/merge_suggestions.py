from database.models import db, Ingredient, RecipeIngredient
from thefuzz import fuzz

def get_suggested_merges(limit=20):
    """
    Finds potentially duplicate ingredients and suggests a 'winner' and 'loser' 
    based on lexical similarity and string heuristics.
    """
    ingredients = db.session.query(Ingredient).filter(Ingredient.status == 'active').all()
    
    candidates = []
    
    # Simple O(N^2) comparison. OK for < 10,000 items (1000 items is ~500k ops, <1 sec in pure python)
    for i in ingredients:
        for j in ingredients:
            if i.id >= j.id: continue
            
            name_i = i.name.lower()
            name_j = j.name.lower()
            
            # Filter out identical exact matches (usually impossible due to UI constraints, but just in case)
            if name_i == name_j:
                continue

            # Category sanity check:
            # We don't want to over-reach by merging things in different categories unless they are super close.
            # But AI generated ingredients often have wrong categories, so we won't strictly forbid it,
            # but we can prioritize those in the same category or penalize those that aren't.
            same_cat = getattr(i, 'main_category', '') == getattr(j, 'main_category', '')

            # --- Rule 1: Substring containment (e.g. "tomato" and "sliced tomato") ---
            if name_i in name_j or name_j in name_i:
                # Winner is usually the shorter, base name
                if len(name_i) <= len(name_j):
                    winner = i
                    loser = j
                else:
                    winner = j
                    loser = i
                    
                # Calculate similarity ratio
                ratio = fuzz.ratio(name_i, name_j)
                
                # To avoid merging "oat milk" with "goat milk", we enforce a fuzz ratio floor
                # even if one is a substring of the other.
                if ratio > 65:
                    candidates.append({
                        "winner_id": winner.id,
                        "winner_name": winner.name,
                        "loser_id": loser.id,
                        "loser_name": loser.name,
                        "score": ratio + (5 if same_cat else 0), # Small boost for same category
                        "reason": "Base Ingredient vs Prep Style"
                    })
                    continue

            # --- Rule 2: High Lexical Similarity (e.g., misspellings, plurals) ---
            ratio = fuzz.ratio(name_i, name_j)
            if ratio > 88: # High threshold to prevent false positives like "lemon juice" and "lime juice"
                # Tie-breaker: Shorter name wins (usually the singular form or without a typo letter)
                if len(name_i) <= len(name_j):
                    winner = i
                    loser = j
                else:
                    winner = j
                    loser = i

                candidates.append({
                    "winner_id": winner.id,
                    "winner_name": winner.name,
                    "loser_id": loser.id,
                    "loser_name": loser.name,
                    "score": ratio + (5 if same_cat else 0),
                    "reason": "High Lexical Similarity (Typo/Plural)"
                })

    # Sort by descending score
    candidates.sort(key=lambda x: x['score'], reverse=True)
    
    # Deduplicate: A loser can only be suggested once to prevent UX clutter
    seen_losers = set()
    final_list = []
    
    for c in candidates:
        if c['loser_id'] not in seen_losers:
            # Also prevent chains if needed, e.g., A -> B, B -> C. We just skip them for now for simplicity.
            final_list.append(c)
            seen_losers.add(c['loser_id'])
            
            if len(final_list) >= limit:
                break
                
    # Gather additional info for the top matches
    for c in final_list:
        winner = db.session.get(Ingredient, c['winner_id'])
        loser = db.session.get(Ingredient, c['loser_id'])
        
        c['winner_image'] = winner.image_filename if hasattr(winner, 'image_filename') and winner.image_filename else ''
        c['loser_image'] = loser.image_filename if hasattr(loser, 'image_filename') and loser.image_filename else ''
        
        c['winner_count'] = db.session.query(db.func.count(RecipeIngredient.id)).filter(RecipeIngredient.ingredient_id == winner.id).scalar()
        c['loser_count'] = db.session.query(db.func.count(RecipeIngredient.id)).filter(RecipeIngredient.ingredient_id == loser.id).scalar()

    return final_list
