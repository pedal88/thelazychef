"""Call a model with one prompt. Each runner returns (output, meta).

Image runners return PNG bytes; text runners return a string. meta holds
whatever the API reports (tokens, finish reason) for the run log.
"""
import io
import time


def run_image(model: str, prompt: str) -> tuple[bytes, dict]:
    from google.genai import types

    from services.ai_models import gemini_client

    client = gemini_client()
    started = time.monotonic()
    if model.startswith('imagen-'):
        response = client.models.generate_images(
            model=model, prompt=prompt,
            config=types.GenerateImagesConfig(number_of_images=1, aspect_ratio='1:1'),
        )
        image = response.generated_images[0].image
        data = image.image_bytes
        meta = {}
    else:
        response = client.models.generate_content(
            model=model, contents=[prompt],
            config=types.GenerateContentConfig(response_modalities=['IMAGE']),
        )
        parts = [p for c in response.candidates for p in c.content.parts if getattr(p, 'inline_data', None)]
        if not parts:
            raise RuntimeError(f"{model} returned no image: {response.text if hasattr(response, 'text') else response}")
        data = parts[0].inline_data.data
        usage = getattr(response, 'usage_metadata', None)
        meta = {'input_tokens': getattr(usage, 'prompt_token_count', None),
                'output_tokens': getattr(usage, 'candidates_token_count', None)}
    meta['seconds'] = round(time.monotonic() - started, 1)
    return _as_png(data), meta


def run_text(model: str, prompt: str) -> tuple[str, dict]:
    raise NotImplementedError("Text tasks get a Claude runner in step 5 (fase 0b).")


def _as_png(data: bytes) -> bytes:
    from PIL import Image

    image = Image.open(io.BytesIO(data))
    out = io.BytesIO()
    image.save(out, 'PNG')
    return out.getvalue()


RUNNERS = {'image': run_image, 'text': run_text}
