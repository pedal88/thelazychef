
import sys
import os
sys.path.append(os.getcwd())

from app import app
from database.models import db, UserRecipeInteraction
from sqlalchemy import text
import datetime

def migrate():
    with app.app_context():
        print("Starting migration of favorites...")
        
        # 1. Check if old table exists
        try:
            # We use text() to execute raw SQL
            result = db.session.execute(text("SELECT user_id, recipe_id, saved_at FROM user_favorite_recipes")).fetchall()
            print(f"Found {len(result)} existing favorites.")
        except Exception as e:
            print(f"Error reading old table or it doesn't exist: {e}")
            return

        # 2. Iterate and migrate
        migrated_count = 0
        for row in result:
            user_id = row[0]
            recipe_id = row[1]
            saved_at = row[2] if row[2] else datetime.datetime.utcnow()
            
            # Check if exists (idempotency)
            exists = db.session.execute(
                db.select(UserRecipeInteraction).where(
                    UserRecipeInteraction.user_id == user_id,
                    UserRecipeInteraction.recipe_id == recipe_id
                )
            ).scalar()
            
            if not exists:
                interaction = UserRecipeInteraction(
                    user_id=user_id,
                    recipe_id=recipe_id,
                    status="favorite",
                    is_super_like=False,
                    timestamp=saved_at
                )
                db.session.add(interaction)
                migrated_count += 1
        
        db.session.commit()
        print(f"Migrated {migrated_count} records.")
        
        # 3. Drop old table
        # We commented it out in models.py, so create_all won't create it, but it exists in DB.
        # We can drop it now.
        try:
            db.session.execute(text("DROP TABLE user_favorite_recipes"))
            db.session.commit()
            print("Dropped user_favorite_recipes table.")
        except Exception as e:
            print(f"Error dropping table: {e}")

if __name__ == "__main__":
    migrate()
