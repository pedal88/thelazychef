
from app import app, db, RecipeIngredient, Ingredient

with app.app_context():
    recipe_id = 89
    print(f"Checking ingredients for Recipe {recipe_id}...")
    
    # join with Ingredient to be sure
    results = db.session.execute(
        db.select(RecipeIngredient, Ingredient)
        .join(Ingredient, RecipeIngredient.ingredient_id == Ingredient.id)
        .filter(RecipeIngredient.recipe_id == recipe_id)
    ).all()
    
    if not results:
        print("No linked ingredients found!")
    else:
        print(f"{'Qty':<10} {'Unit':<10} {'Ingredient Name':<30} {'ID':<5} {'Food ID':<10}")
        print("-" * 70)
        for ri, ing in results:
            print(f"{ri.amount:<10} {ri.unit:<10} {ing.name:<30} {ing.id:<5} {ing.food_id:<10}")
            
    # Check if these IDs were recently created or old? 
    # (We can't easily know 'age' without created_at on Ingredient, let's check if they have it)
    # Ingredient model has 'created_at' (String ISO)
            
    print("\n--- Ingredient Details ---")
    for ri, ing in results:
        print(f"ID {ing.id}: Created At: {ing.created_at}, Is Basic: {ing.is_basic_ingredient}")
