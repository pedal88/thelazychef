import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db
from database.models import User
from sqlalchemy import select

def get_admin_hash():
    with app.app_context():
        stmt = select(User).where(User.id == 1)
        user = db.session.execute(stmt).scalar_one_or_none()
        
        if user:
            print(f"User: {user.email}")
            print(f"Password Hash: {user.password_hash}")
        else:
            print("User id=1 not found.")

if __name__ == "__main__":
    get_admin_hash()
