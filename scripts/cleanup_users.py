
import sys
import os
sys.path.append(os.getcwd())

from app import app, db
from database.models import User

def cleanup():
    with app.app_context():
        u = db.session.execute(db.select(User).where(User.email == "temp_admin@example.com")).scalar()
        if u:
            db.session.delete(u)
            db.session.commit()
            print("Deleted temp admin.")
        else:
            print("Temp admin not found.")

if __name__ == "__main__":
    cleanup()
