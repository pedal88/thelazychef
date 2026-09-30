from app import app, db, Chef

with app.app_context():
    print("Checking Chefs in DB...")
    gourmet = db.session.get(Chef, 'gourmet')
    print(f"Chef 'gourmet': {gourmet}")
    kristine = db.session.get(Chef, 'Kristine')
    print(f"Chef 'Kristine': {kristine}")
    
    all_chefs = Chef.query.all()
    print(f"All Chefs: {[c.id for c in all_chefs]}")
