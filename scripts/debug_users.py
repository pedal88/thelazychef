
import sys
import os
sys.path.append(os.getcwd())

from app import app, db
from database.models import User
from werkzeug.security import generate_password_hash

def manage_users():
    with app.app_context():
        # 1. Demote pedal88
        u = db.session.get(User, 3)
        if u:
            u.is_admin = False
            print(f"Demoted user {u.email} (ID: 3) to regular user.")
        
        # 2. Create temp admin
        email = "temp_admin@example.com"
        pwd = "password123"
        
        existing = db.session.execute(db.select(User).where(User.email == email)).scalar()
        if not existing:
            new_admin = User(
                email=email,
                password_hash=generate_password_hash(pwd),
                is_admin=True
            )
            db.session.add(new_admin)
            print(f"Created temp admin: {email} / {pwd}")
        else:
            existing.is_admin = True
            existing.password_hash = generate_password_hash(pwd) # Reset pwd to be sure
            print(f"Updated temp admin: {email}")
            
        db.session.commit()

if __name__ == "__main__":
    manage_users()
