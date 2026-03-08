import json
import logging
import typing_extensions as typing
from google.genai import types

from ai_engine import client, load_controlled_vocabularies, get_slim_pantry_context, pantry_map
from database.models import db, TikTokSource, Recipe
from services.social_media_service import SocialMediaExtractor

logger = logging.getLogger(__name__)

class TikTokIngestionService:
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
            
            Step 1: Classification
            If the video demonstrates how to make a specific dish (even loosely), classify as "RECIPE".
            If the video shares cooking knowledge, equipment reviews, or techniques without a dish, classify as "RESOURCE".
            If it's entirely unrelated to cooking/food, classify as "NO_MATCH".
            
            Step 2: Extraction
            If "RECIPE", provide the full recipe_data matching our application schema.
            If not a recipe, leave recipe_data empty.

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
            
            # Format correction for fallback AI dicts
            if not recipe_data and entity_type == 'RECIPE':
                # Sometimes gemini nests it differently without schema enforcement
                if 'title' in res_json:
                     recipe_data = res_json
                     dish_name = res_json.get('title')
            
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
