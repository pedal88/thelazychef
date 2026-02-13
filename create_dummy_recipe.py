
from app import app, db, Recipe

with app.app_context():
    # Create a dummy recipe
    r = Recipe(
        title="Delete Me Test Recipe",
        cuisine="Test",
        diet="Test",
        difficulty="Easy",
        protein_type="None",
        chef_id="gourmet",
        cleanup_factor=1,
        taste_level=1,
        prep_time_mins=1
    )
    db.session.add(r)
    db.session.commit()
    print(f"Created recipe ID: {r.id}")
