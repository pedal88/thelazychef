import sys
import os
import getpass
from sqlalchemy import delete

# Add parent directory to path to import app and models
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db
from database.models import User

def reset_admin():
    with app.app_context():
        print("--- ⚠️  DANGER ZONE: DELETE ALL USERS & CREATE ADMIN ⚠️  ---")
        confirm = input("Are you sure you want to DELETE ALL USERS? (y/n): ").strip().lower()
        if confirm != 'y':
            print("Operation cancelled.")
            return

        # 1. Delete All Users
        try:
            num_deleted = db.session.query(User).delete()
            db.session.commit()
            print(f"✅ Deleted {num_deleted} existing users.")
        except Exception as e:
            print(f"❌ Error deleting users: {e}")
            db.session.rollback()
            return

        # 2. Create New Admin
        print("\n--- Create New Admin ---")
        email = "thelazychefai@gmail.com"
        print(f"Creating Admin User: {email}")
        
        password = getpass.getpass("Enter Password: ")
        confirm_password = getpass.getpass("Confirm Password: ")

        if password != confirm_password:
            print("❌ Error: Passwords do not match.")
            return
            
        new_admin = User(email=email, is_admin=True)
        new_admin.set_password(password)
        
        try:
            db.session.add(new_admin)
            db.session.commit()
            print(f"✅ Successfully created admin user: {email}")
        except Exception as e:
            print(f"❌ Error creating admin: {e}")
            db.session.rollback()

if __name__ == "__main__":
    reset_admin()
