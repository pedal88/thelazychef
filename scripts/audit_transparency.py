import sys
import logging
import requests
import time
from PIL import Image
from io import BytesIO

# Add project root to path
sys.path.append('.')

logging.getLogger("werkzeug").setLevel(logging.ERROR)

from app import app
from database.models import db, Ingredient

def has_transparency(img):
    if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
        alpha = img.convert('RGBA').getchannel('A')
        min_alpha, max_alpha = alpha.getextrema()
        if min_alpha < 255:
            return True
    return False

def main():
    print("Starting Transparency Audit across all Ingredient Images...")
    
    with app.app_context():
        # Get all ingredients with an image
        ingredients = db.session.execute(
            db.select(Ingredient)
            .where(Ingredient.image_url != None)
            .where(Ingredient.image_url != "")
        ).scalars().all()
        
        total = len(ingredients)
        print(f"Found {total} images to inspect.")
        
        count_transparent = 0
        count_solid = 0
        count_error = 0
        
        # Batch commit to save database IO
        batch_size = 50
        processed = 0
        
        session = requests.Session()
        
        for ing in ingredients:
            
            # Handle relative paths for legacy
            url = ing.image_url
            if not url.startswith('http'):
                url = f"https://storage.googleapis.com/thelazychef-assets/{url}"
                
            try:
                resp = session.get(url, timeout=(3.0, 5.0))
                if resp.status_code == 200:
                    try:
                        img = Image.open(BytesIO(resp.content))
                        is_transp = has_transparency(img)
                        
                        if is_transp:
                            count_transparent += 1
                            ing.has_transparent_image = True
                        else:
                            count_solid += 1
                            ing.has_transparent_image = False
                    except Exception as img_e:
                        count_error += 1
                        print(f"[{ing.id}] Image corrupt: {str(img_e)}", flush=True)
                        continue
                else:
                    count_error += 1
                    print(f"[{ing.id}] {url} - Status {resp.status_code}", flush=True)
                    continue
            except Exception as e:
                count_error += 1
                print(f"[{ing.id}] Timeout or Network Error: {url}", flush=True)
                continue
                
            processed += 1
            if processed % batch_size == 0:
                db.session.commit()
                print(f"Progress: {processed}/{total} (Transparent: {count_transparent}, Solid: {count_solid})", flush=True)
                
            # Rate limit to avoid triggering GC limits
            time.sleep(0.05)
            
        # Final commit
        db.session.commit()
        
        print(f"\nAudit Complete!")
        print(f"Total Transparent: {count_transparent}")
        print(f"Total Solid (Needs Rembg): {count_solid}")
        print(f"Errors: {count_error}")

if __name__ == '__main__':
    main()
