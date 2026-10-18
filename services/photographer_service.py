import os
import time
from google import genai
from google.genai import types
from PIL import Image
from io import BytesIO

# Initialize Client
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
client = None
if GOOGLE_API_KEY:
    client = genai.Client(api_key=GOOGLE_API_KEY)


def generate_actual_image(visual_prompt: str, number_of_images: int = 1) -> list[Image.Image]:
    """
    Uses Gemini (Image) to generate the actual pixel data from the prompt.
    Returns: List of PIL Image objects
    """
    if not client:
        raise Exception("Google API Key not configured")

    # Define model fallback strategy
    # Primary: Imagen 3.0 (Fastest/Standard) -> Wait, user said Imagen 4 was primary in the logs?
    # The logs showed: "model for flow_id: flow-juno-prompt-rewriter-vertex-imagen-jpe-v1-8"
    # And code had 'imagen-4.0-generate-001'.
    # We will try 4.0 first, then 3.0.
    
    models_to_try = ['imagen-4.0-generate-001']
    last_exception = None

    for model_name in models_to_try:
        print(f"DEBUG: Attempting image generation with model: {model_name}")
        
        # Retry loop for transient errors (e.g. 503)
        for attempt in range(1, 4): # Try 3 times
            try:
                response = client.models.generate_images(
                    model=model_name,
                    prompt=visual_prompt,
                    config=types.GenerateImagesConfig(
                        number_of_images=number_of_images,
                        aspect_ratio='1:1'
                    )
                )
                
                # Access images
                if response.generated_images:
                    images = []
                    for gen_img in response.generated_images:
                        # Access the inner 'image' object which contains the bytes
                        images.append(Image.open(BytesIO(gen_img.image.image_bytes)))
                    return images
                else:
                    raise Exception("No images returned from API")
            
            except Exception as e:
                print(f"WARNING: Attempt {attempt} failed for {model_name}: {e}")
                last_exception = e
                
                # Check for critical errors that shouldn't be retried or suggest switching models
                error_str = str(e)
                if "503" in error_str or "429" in error_str:
                    time.sleep(2 * attempt) # Backoff
                    continue # Retry same model
                else:
                    break # specific model error, try next model

    # If we get here, all models failed
    print(f"CRITICAL: All image generation attempts failed. Last error: {last_exception}")
    raise last_exception
