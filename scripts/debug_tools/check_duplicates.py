
from app import app, db, Ingredient

with app.app_context():
    names = ["Eggs", "Cottage Cheese", "Onion Powder", "Garlic Powder", "Italian Seasoning"]
    print(f"{'ID':<5} {'Food ID':<10} {'Name':<30}")
    print("-" * 50)
    
    for name in names:
        # ILIKE for case-insensitive partial match
        results = db.session.execute(
            db.select(Ingredient).filter(Ingredient.name.ilike(f"%{name}%"))
        ).scalars().all()
        
        for ing in results:
             print(f"{ing.id:<5} {ing.food_id:<10} {ing.name:<30}")
