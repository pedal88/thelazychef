import sys
import os
from io import BytesIO
from PIL import Image
from rembg import remove
import requests
import time

# Load Flask App Context
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import create_app
from database.models import db, Ingredient
from services.storage_service import get_storage_provider

app = create_app()

def run_migration():
    with app.app_context():
        storage = get_storage_provider()
        
        # 1. Query all ingredients that already have an image
        ingredients = db.session.execute(
            db.select(Ingredient).where(Ingredient.image_url != None, Ingredient.image_url != "")
        ).scalars().all()

        current_time = int(time.time())

        for ing in ingredients:
            print(f"Processing: {ing.name} (ID: {ing.id}) - Current URL: {ing.image_url}")
            try:
                # 2. Download the existing image bytes
                resp = requests.get(ing.image_url)
                if resp.status_code != 200: 
                    print(f"  -> Failed to download image: HTTP {resp.status_code}")
                    continue
                
                # 3. Strip the background
                output_image_bytes = remove(resp.content)
                
                # Convert explicitly to PNG
                img = Image.open(BytesIO(output_image_bytes))
                final_buffer = BytesIO()
                img.save(final_buffer, format="PNG")
                final_bytes = final_buffer.getvalue()

                # 4. Upload the transparent PNG to Cloud Storage
                # Generates a random cache-busting suffix to ensure the dashboard instantly reflects the new image
                new_filename = f"{ing.id}_transparent_{current_time}.png"
                new_url = storage.save(final_bytes, new_filename, "ingredients")
                
                # 5. Save back to database
                ing.image_url = new_url
                db.session.commit()
                print(f"  -> Success. New URL: {new_url}")
                
            except Exception as e:
                print(f"  -> Failed on {ing.name}: {e}")

if __name__ == "__main__":
    run_migration()
