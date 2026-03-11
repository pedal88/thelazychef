import os
import sys
import time
import logging
from google import genai

# Add project root to path
sys.path.append('.')

logging.getLogger("werkzeug").setLevel(logging.ERROR)

from app import app
from database.models import db, Ingredient

from dotenv import load_dotenv
load_dotenv()

def generate_embeddings():
    print("Initializing Google GenAI Client...")
    location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
        
    client = genai.Client(vertexai=True, location=location)
    
    with app.app_context():
        # Find ingredients without an embedding
        ingredients = db.session.execute(
            db.select(Ingredient)
            .where(Ingredient.embedding == None)
        ).scalars().all()
        
        total = len(ingredients)
        print(f"Found {total} ingredients needing mathematically generated embeddings.")
        
        if total == 0:
            print("All ingredients already have embeddings!")
            return
            
        success_count = 0
        error_count = 0
        batch_size = 50
        
        # Google API has rate limits (e.g., 60-150 requests per minute depending on quota).
        # We process sequentially with a small delay.
        
        for idx, ing in enumerate(ingredients, 1):
            # We want the embedding to represent the culinary identity of the item.
            # Combining Name, Category, and Sub-category gives the AI perfect context.
            cat = ing.main_category or "food"
            sub = ing.sub_category or "general"
            text_to_embed = f"{ing.name}. Category: {cat}. Sub-category: {sub}."
            
            try:
                result = client.models.embed_content(
                    model='text-embedding-004',
                    contents=text_to_embed,
                )
                
                # The result contains a list of embeddings
                embedding_vector = result.embeddings[0].values
                
                # Optional: Ensure it matches the 768 dimension we defined in DB
                if len(embedding_vector) == 768:
                    ing.embedding = embedding_vector
                    success_count += 1
                else:
                    print(f"[{ing.id}] {ing.name} - Dimension mismatch: got {len(embedding_vector)}")
                    error_count += 1
                    continue
                    
            except Exception as e:
                print(f"[{ing.id}] Error generating embedding for {ing.name}: {e}")
                error_count += 1
                time.sleep(2)  # Backoff on error
                
            if idx % batch_size == 0 or idx == total:
                db.session.commit()
                print(f"Progress: {idx}/{total} (Success: {success_count}, Errors: {error_count})")
                
            # Respect basic quota constraints
            time.sleep(0.5)

        print("\nFinished embedding generation!")
        print(f"Total Success: {success_count}")
        print(f"Total Errors : {error_count}")

if __name__ == '__main__':
    generate_embeddings()
