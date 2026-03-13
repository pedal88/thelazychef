import os
import shutil
import json
import re
import time
import logging
from typing import Optional
from google import genai
from google.genai import types
from PIL import Image
from io import BytesIO

logger = logging.getLogger(__name__)

# Load Credentials (Assuming Environment Variables or default Auth)
# Project ID and Location are usually required for Vertex AI
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "your-project-id") 
LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")

class VertexImageGenerator:
    _force_fallback = False

    def __init__(self, storage_provider, root_path=None):
        self.storage = storage_provider
        self.root_path = root_path or os.getcwd()
        self.pantry_file = os.path.join(self.root_path, 'data', 'constraints', 'pantry.json')
        
        # Local candidate storage (Legacy support for dashboard)
        self.candidates_dir = os.path.join(self.root_path, 'static', 'pantry', 'candidates')
        os.makedirs(self.candidates_dir, exist_ok=True)
        
        # Initialize GenAI Client
        api_key = os.getenv("GOOGLE_API_KEY")
        if api_key:
            self.client = genai.Client(api_key=api_key)
        else:
            self.client = None
            print("WARNING: GOOGLE_API_KEY not set. VertexImageGenerator will fail.")
            
        # Initialize Jinja2 Env
        try:
            from jinja2 import Environment, FileSystemLoader
            self.jinja_env = Environment(loader=FileSystemLoader(os.path.join(self.root_path, 'data', 'prompts')))
        except Exception as e:
            print(f"Warning: Jinja2 initialization failed: {e}")
            self.jinja_env = None

    def get_prompt(self, ingredient_name, visual_details=""):
        if not self.jinja_env:
            return f"A professional studio food photography shot of {ingredient_name}. {visual_details}"
            
        try:
            template = self.jinja_env.get_template('ingredient_image/ingredient_image.jinja2')
            return template.render(ingredient_name=ingredient_name, visual_details=visual_details)
        except Exception as e:
            print(f"Error rendering prompt: {e}")
            return f"A professional studio food photography shot of {ingredient_name}."


    def _get_safe_filename(self, name: str) -> str:
        """Converts ingredient name to safe filename: 'Beef Ribeye' -> 'beef_ribeye.png'"""
        safe_name = re.sub(r'[^a-zA-Z0-9]', '_', name.lower())
        safe_name = re.sub(r'_+', '_', safe_name).strip('_')
        return f"{safe_name}.png"
    
    def _generate_with_fallback(self, prompt: str, config):
        """Executes generation with tiered model fallback logic."""
        if VertexImageGenerator._force_fallback:
            models = ['imagen-4.0-fast-generate-001']
        else:
            models = ['imagen-4.0-generate-001', 'imagen-4.0-fast-generate-001']

        last_error = None
        for i, model_name in enumerate(models):
            try:
                response = self.client.models.generate_images(
                    model=model_name,
                    prompt=prompt,
                    config=config
                )
                if response and response.generated_images:
                    return response, model_name
            except Exception as e:
                error_msg = str(e).lower()
                is_429 = "429" in error_msg or "resourceexhausted" in error_msg or "quota" in error_msg
                last_error = e

                if is_429:
                    if "per_day" in error_msg or "daily" in error_msg:
                        logger.critical(f"CRITICAL: {model_name} quota exhausted (daily). Falling back to next model for prompt: {prompt[:60]}")
                        if model_name == 'imagen-4.0-generate-001':
                            VertexImageGenerator._force_fallback = True
                        continue # switch model completely
                    
                    elif "per_minute" in error_msg or "minute" in error_msg:
                        if i == 0:  
                            logger.warning(f"Minute quota exhausted for {model_name}. Sleeping 10s and retrying...")
                            time.sleep(10)
                            try:
                                response = self.client.models.generate_images(
                                    model=model_name,
                                    prompt=prompt,
                                    config=config
                                )
                                if response and response.generated_images:
                                    return response, model_name
                            except Exception as inner_e:
                                logger.critical(f"CRITICAL: {model_name} quota exhausted (per_minute retried). Falling back. Inner err: {inner_e}")
                                last_error = inner_e
                                continue
                        else:
                            logger.critical(f"CRITICAL: {model_name} quota exhausted (per_minute). Falling back to next model...")
                            continue
                
                # If it's a structural API error (e.g. 400 Bad Request, safety block), we shouldn't fallback blindly to different models as they likely fail too
                logger.error(f"Error with model {model_name}: {e}")
                raise e
        
        raise Exception(f"All fallback models exhausted. Last error: {last_error}")

    def generate_candidate(self, ingredient_name: str, prompt: str = None, scope: str = None) -> dict:
        """
        Generates an image using Imagen and saves it to the candidates folder.
        """
        import time

        if not self.client:
            return {'success': False, 'error': "Google API Key not configured"}

        try:
            # Timestamp suffix guarantees a fresh URL on every regeneration
            ts = int(time.time())
            base_name = self._get_safe_filename(ingredient_name).replace('.png', '')
            filename = f"{base_name}_{ts}.png"

            remove_bg = True
            negative_prompt = None

            # Apply orchestrator if scope is present
            if scope:
                from services.visual_orchestrator_service import VisualOrchestrator
                prompt = VisualOrchestrator.get_styled_prompt(ingredient_name, scope)
                rules = VisualOrchestrator.get_processing_rules(scope)
                remove_bg = rules.get('remove_background', False)
                negative_prompt = VisualOrchestrator.get_negative_prompt(scope)

            # Some Vertex GenAI models/SDK versions reject distinct `negative_prompt` params.
            # Append it directly into the prompt string using negative steering text.
            if negative_prompt:
                prompt = f"{prompt} DO NOT INCLUDE: {negative_prompt}"

            print(f"Generating candidate for {ingredient_name} → {filename} | Prompt: {str(prompt)[:60]}...")

            config = types.GenerateImagesConfig(
                number_of_images=1,
                aspect_ratio='1:1'
            )

            response, model_used = self._generate_with_fallback(prompt, config)

            if response.generated_images:
                raw_image_bytes = response.generated_images[0].image.image_bytes
                
                if remove_bg:
                    from rembg import remove
                    output_image_bytes = remove(raw_image_bytes)
                else:
                    output_image_bytes = raw_image_bytes
                
                # Convert explicitly to PNG
                img = Image.open(BytesIO(output_image_bytes))
                final_buffer = BytesIO()
                img.save(final_buffer, format="PNG")
                final_bytes = final_buffer.getvalue()

                # New filename ⟹ new GCS blob ⟹ new public URL — no cache hit possible
                public_url = self.storage.save(final_bytes, filename, "pantry/candidates")

                return {
                    'success': True,
                    'image_url': public_url,
                    'has_transparent_image': remove_bg,
                    'local_path': public_url  # Backwards compat
                }
            else:
                return {'success': False, 'error': "No image returned from API"}

        except Exception as e:
            print(f"Error generating candidate: {e}")
            return {'success': False, 'error': str(e)}

    def approve_candidate(self, ingredient_name: str) -> dict:
        """
        Approves a candidate image by overwriting the production image.
        1. Finds candidate file.
        2. Looks up target filename from pantry.json.
        3. Overwrites target file.
        4. Deletes candidate.
        """
        candidate_filename = self._get_safe_filename(ingredient_name)
        candidate_path = os.path.join(self.candidates_dir, candidate_filename)
        
        if not os.path.exists(candidate_path):
            return {'success': False, 'error': f"Candidate file not found: {candidate_filename}"}
        
        # Look up target in pantry.json
        target_relative_path = None
        try:
            with open(self.pantry_file, 'r') as f:
                pantry_data = json.load(f)
                
            # Search for ingredient (case-insensitive)
            # pantry_data is a list of objects
            for item in pantry_data:
                if item.get('food_name', '').lower() == ingredient_name.lower():
                    # found it
                    if 'images' in item and 'image_url' in item['images']:
                        target_relative_path = item['images']['image_url']
                    break
            
            if not target_relative_path:
                 return {'success': False, 'error': f"Ingredient '{ingredient_name}' not found in pantry.json or has no image_url defined."}
                 
        except Exception as e:
             return {'success': False, 'error': f"Error reading pantry.json: {str(e)}"}

        # Perform Overwrite
        # target_relative_path is likely "pantry/000001.png" or "/static/pantry/000001.png"
        clean_target = target_relative_path
        if clean_target.startswith("/static/"):
            clean_target = clean_target.replace("/static/", "")
        
        # Now we have something like "pantry/000001.png"
        # We need to extract folder and filename
        if "/" in clean_target:
            dest_folder = os.path.dirname(clean_target)
            dest_filename = os.path.basename(clean_target)
        else:
            dest_folder = "pantry" # Default
            dest_filename = clean_target

        try:
            print(f"Approving: Moving Candidate -> {dest_folder}/{dest_filename}")
            
            # Since candidate is already in storage, we need a "move/copy" operation.
            # However, our current StorageProvider only has `copy` from LOCAL source.
            # If we are in GCS, we'd want a bucket-to-bucket copy.
            # For Phase 2, let's assume valid flow is:
            # 1. Candidate is in "pantry/candidates/{filename}"
            # 2. We want to move it to "{dest_folder}/{dest_filename}"
            
            # Simplification: READ bytes -> WRITE bytes -> DELETE old
            # This is inefficient for GCS but universal.
            # Better: Add `move` to StorageProvider later.
            
            # For now, we will rely on `approve_candidate` being used mostly for metadata updates
            # OR we implement a simple read-and-write. 
            pass 
            # WAIT: The storage interface doesn't have a generic "read" or "move". 
            # The prompt asked for `copy(source_path, ...)` but defined source_path as local.
            # Current `LocalStorageProvider` supports `copy` from local path.
            # `GoogleCloudStorageProvider` assumes receiving local path too and uploading.
            
            # CRITICAL: `approve_candidate` logic relies on the file being present to move it.
            # If we are strictly using StorageProvider, we should probably just re-generate 
            # or expect the caller to handle the bytes.
            # BUT, the `copy` method I implemented in `GoogleCloudStorageProvider` does `open(source_path)`.
            
            # For this specific refactor, since we changed `generate_candidate` to return a URL,
            # `approve_candidate` is tricky without direct file access.
            # Let's Modify StorageProvider to include `move` or just omit this feature for now?
            # User requirement: "Refactor... Inject StorageProvider... Replace all local save logic".
            
            # Let's assume for now that `approve_candidate` needs to know the source.
            # Since `generate_candidate` saves via storage, we can't easily "move" it if we don't have a "move" method.
            # Let's add a TODO and return success for now to unblock, 
            # or implemented a specific hack?
            # Actually, `approve_candidate` was reading `candidates_dir` locally. 
            # If we are on GCS, `candidates_dir` doesn't exist locally.
            
            return {'success': False, 'error': "Approve functionality pending update for Cloud Storage."}

        except Exception as e:
            return {'success': False, 'error': f"Error moving file: {str(e)}"}
