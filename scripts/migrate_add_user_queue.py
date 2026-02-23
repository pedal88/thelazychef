"""
Migration: Add user_queue table.

Safe to run multiple times — db.create_all() is idempotent. It will only
create tables that don't already exist; it will never drop or alter existing ones.

Usage:
    venv/bin/python scripts/migrate_add_user_queue.py
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from database.models import db, UserQueue
from sqlalchemy import inspect, text


def migrate() -> None:
    with app.app_context():
        inspector = inspect(db.engine)
        existing_tables = inspector.get_table_names()

        if 'user_queue' in existing_tables:
            print("✅ user_queue table already exists — nothing to do.")
            return

        print("🔧 Creating user_queue table...")
        # create_all only creates tables that are missing
        db.create_all()

        # Verify
        inspector2 = inspect(db.engine)
        if 'user_queue' in inspector2.get_table_names():
            print("✅ user_queue table created successfully.")
        else:
            print("❌ Something went wrong — table was not created.")


if __name__ == "__main__":
    migrate()
