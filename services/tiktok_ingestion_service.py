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
        Fast triage step: Scrapes text caption, uses Gemini to classify (RECIPE vs RESOURCE)
        and determine format (VIDEO vs SLIDESHOW) based purely on text.
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
             return {"status": "skipped", "reason": "Already imported as Recipe", "id": existing_recipe.id}

        # 2. Extract Metadata ONLY (no video download)
        try:
            extract_result = SocialMediaExtractor.extract_metadata(url)
            caption = extract_result.get('caption', '')
        except Exception as e:
            logger.error(f"Failed to extract metadata from {url}: {e}")
            return {"status": "error", "reason": str(e)}

        try:
            # 3. Fast Text Triage with Gemini
            system_prompt = f"""
            You are a culinary intelligence triager. Your job is to analyze the caption text of a social media post.
            
            CRITICAL: You MUST return a JSON object with EXACTLY this structure:
            {{
                "entity_type": "RECIPE" | "RESOURCE" | "NO_MATCH",
                "dish_name": "The name of the dish or subject of the resource",
                "format_type": "VIDEO" | "CAROUSEL_IMAGE" | "UNKNOWN"
            }}
            
            Step 1: Classification
            If the text indicates it's demonstrating a specific dish, classify as "RECIPE".
            If the text shares cooking knowledge, reviews, or techniques without a dish, classify as "RESOURCE".
            If completely unrelated to food, classify as "NO_MATCH".
            
            Step 2: Format Guessing
            If the caption mentions "swipe", "slideshow", "pictures", etc., guess "CAROUSEL_IMAGE".
            Otherwise, guess "VIDEO".
            """
            
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=[system_prompt, f"Caption text to analyze: {caption}"],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                )
            )
            
            res_json = json.loads(response.text)
            
            entity_type = res_json.get('entity_type', 'NO_MATCH')
            dish_name = res_json.get('dish_name', 'Unknown')
            format_type = res_json.get('format_type', 'UNKNOWN')
            
            # Format correction
            if 'entity_type' not in res_json:
                if 'title' in res_json or 'recipe_name' in res_json:
                     entity_type = 'RECIPE'
                     dish_name = res_json.get('title') or res_json.get('recipe_name', 'Unknown')
            
            # 4. Save to TikTokSource sidecar
            new_source = TikTokSource(
                tiktok_url=url,
                dish_name=dish_name,
                entity_type=entity_type,
                format_type=format_type,
                status='SUGGESTED',
                raw_caption=caption
            )
            db.session.add(new_source)
            db.session.commit()
            
            return {
                "status": "success", 
                "entity_type": entity_type, 
                "format_type": format_type,
                "dish_name": dish_name,
                "id": new_source.id
            }

        except Exception as e:
            db.session.rollback()
            logger.error(f"Sidecar text triage failed for {url}: {e}")
            return {"status": "error", "reason": str(e)}
