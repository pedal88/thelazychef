from app import app
from database.models import db, RecipeEvaluation

with app.app_context():
    evals = db.session.query(RecipeEvaluation).all()
    print(f"Total evals: {len(evals)}")
    for e in evals:
        print(f"Recipe ID: {e.recipe_id}, Details: {e.evaluation_details}")
