import json
import logging
import typing_extensions as typing
from google.genai import types

from ai_engine import client, load_controlled_vocabularies, pantry_map
from services.pantry_service import get_slim_pantry_context
from database.models import db, TikTokSource, Recipe
from services.social_media_service import SocialMediaExtractor

logger = logging.getLogger(__name__)

class TikTokIngestionService:
    @staticmethod
    def parse_tiktok_file(file_content: str) -> list[str]:
        """
        Parses a TikTok export file (Like List.txt, Favourite Videos.txt) to extract URLs.
        Filters out duplicates against TikTokSource and Recipe tables.
        """
        import re
        # Find all URLs that look like tiktok links
        urls = re.findall(r'Link:\s*(https?://[^\s]+)', file_content)
        
        # Fallback if the word "Link:" wasn't used but it's clearly a TikTok URL
        if not urls:
             urls = re.findall(r'(https?://(?:www\.)?(?:vt\.)?tiktok\.com/[^\s]+)', file_content)

        # Deduplicate the list itself
        urls = list(set(urls))
        
        valid_urls = []
        for url in urls:
             existing_source = db.session.execute(
                 db.select(TikTokSource).where(TikTokSource.tiktok_url == url)
             ).scalar_one_or_none()
             
             existing_recipe = db.session.execute(
                 db.select(Recipe).where(Recipe.source_input == url)
             ).scalar_one_or_none()
             
             if not existing_source and not existing_recipe:
                  valid_urls.append(url)
                  
        return valid_urls

    @staticmethod
    def classify_and_extract(url: str):
        """
        Downloads a video, uses Gemini to classify it as RECIPE, RESOURCE, or NO_MATCH.
        If it's a RECIPE, extracts the JSON matching the main RecipeSchema.
        """
        # 1. Deduplication check
        existing_source = db.session.execute(
            db.select(TikTokSource).where(TikTokSource.tiktok_url == url)
        ).scalar_one_or_none()
        
        if existing_source:
            return {"status": "skipped", "reason": "Already in sidecar", "id": existing_source.id}

        existing_recipe = db.session.execute(
            db.select(Recipe).where(Recipe.source_input == url)
        ).scalar_one_or_none()
        
        if existing_recipe:
             # It's already fully imported
             return {"status": "skipped", "reason": "Already imported as Recipe", "id": existing_recipe.id}

        # 2. Extract Video
        try:
            extract_result = SocialMediaExtractor.download_video(url)
            video_path = extract_result['video_path']
            caption = extract_result.get('caption', '')
        except Exception as e:
            logger.error(f"Failed to download video from {url}: {e}")
            return {"status": "error", "reason": str(e)}

        try:
            # 3. Upload to Gemini
            file_ref = client.files.upload(file=video_path)
            
            import time
            while True:
                file_info = client.files.get(name=file_ref.name)
                if file_info.state == "ACTIVE":
                    break
                elif file_info.state == "FAILED":
                    raise ValueError("Video processing failed inside Gemini")
                time.sleep(2)
            
            # 4. Get Context
            slim_context = get_slim_pantry_context()
            pantry_str = json.dumps(slim_context)
            vocab = load_controlled_vocabularies()
            
            # Ask Gemini to return a combined schema
            system_prompt = f"""
            You are a culinary intelligence extractor. Your job is to analyze the provided video.
            
            CRITICAL: You MUST return a JSON object with EXACTLY this wrapper structure:
            {{
                "entity_type": "RECIPE" | "RESOURCE" | "NO_MATCH",
                "dish_name": "The name of the dish or subject of the resource",
                "recipe_data": {{ ... the actual recipe details if it's a recipe ... }}
            }}
            
            Step 1: Classification
            If the video demonstrates how to make a specific dish (even loosely), classify as "RECIPE".
            If the video shares cooking knowledge, equipment reviews, or techniques without a dish, classify as "RESOURCE".
            If it's entirely unrelated to cooking/food, classify as "NO_MATCH".
            
            Step 2: Extraction
            If "RECIPE", populate 'recipe_data' matching our standard recipe schema (title, difficulty, etc).
            If not a recipe, leave 'recipe_data' empty {{}}.

            Pantry Context for matching ingredient IDs (pantry_id):
            {pantry_str}
            
            Valid Metadata vocabularies:
            {json.dumps(vocab)}
            """
            
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=[file_ref, system_prompt, f"Caption: {caption}"],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                )
            )
            
            res_json = json.loads(response.text)
            
            entity_type = res_json.get('entity_type', 'NO_MATCH')
            dish_name = res_json.get('dish_name', 'Unknown')
            recipe_data = res_json.get('recipe_data', {})
            
            # Format correction for fallback AI dicts when it ignores the wrapper
            if 'entity_type' not in res_json:
                if 'title' in res_json or 'recipe_name' in res_json or 'ingredients' in res_json:
                     entity_type = 'RECIPE'
                     recipe_data = res_json
                     dish_name = res_json.get('title') or res_json.get('recipe_name', 'Unknown')
            
            # 5. Save to TikTokSource sidecar
            new_source = TikTokSource(
                tiktok_url=url,
                dish_name=dish_name,
                entity_type=entity_type,
                status='SUGGESTED',
                extracted_json=recipe_data
            )
            db.session.add(new_source)
            db.session.commit()
            
            return {
                "status": "success", 
                "entity_type": entity_type, 
                "dish_name": dish_name,
                "id": new_source.id
            }

        except Exception as e:
            db.session.rollback()
            logger.error(f"Sidecar extraction failed for {url}: {e}")
            return {"status": "error", "reason": str(e)}
        finally:
            if 'video_path' in locals():
                SocialMediaExtractor.cleanup(video_path)
