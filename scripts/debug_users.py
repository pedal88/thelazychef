import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import app, db
from database.models import User
from sqlalchemy import select

def list_users():
    with app.app_context():
        users = db.session.execute(select(User)).scalars().all()
        print(f"Total Users: {len(users)}")
        for u in users:
            print(f"ID: {u.id} | Email: {u.email} | Hash: {u.password_hash[:20]}...")

if __name__ == "__main__":
    list_users()
