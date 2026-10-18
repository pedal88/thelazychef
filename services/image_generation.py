"""Generate one image with the Gemini image model. Used by every image path.

Imagen 4 was retired from the Gemini API in 2026; the Gemini image models
replace it. They take the prompt as content and return the image inline.
They also accept reference images, which the v2 image flow uses to keep a
dish and its components consistent.
"""
import io
import time

from google.genai import types

from services.ai_models import GEMINI_IMAGE, gemini_client


def generate_image(prompt: str, model: str = GEMINI_IMAGE, references: list[bytes] | None = None,
                   attempts: int = 3, aspect_ratio: str = '1:1') -> tuple[bytes, dict]:
    """Return (PNG bytes, meta). Retries transient errors (429, 5xx).

    The aspect ratio is set in the request, not only in the prompt: without
    it some models return wide images."""
    contents = [types.Part.from_bytes(data=ref, mime_type='image/png') for ref in references or []] + [prompt]
    config = types.GenerateContentConfig(
        response_modalities=['IMAGE'],
        image_config=types.ImageConfig(aspect_ratio=aspect_ratio),
    )

    last_error = None
    for attempt in range(attempts):
        started = time.monotonic()
        try:
            response = gemini_client().models.generate_content(model=model, contents=contents, config=config)
        except Exception as e:  # noqa: BLE001 - classified below
            last_error = e
            message = str(e)
            if any(code in message for code in ('429', '500', '502', '503', '504')) and attempt < attempts - 1:
                time.sleep(5 * (attempt + 1))
                continue
            raise
        parts = [p for c in (response.candidates or []) for p in (c.content.parts if c.content else [])
                 if getattr(p, 'inline_data', None)]
        if not parts:
            reason = response.candidates[0].finish_reason if response.candidates else 'no candidates'
            raise RuntimeError(f"{model} returned no image ({reason})")
        usage = getattr(response, 'usage_metadata', None)
        meta = {
            'model': model,
            'seconds': round(time.monotonic() - started, 1),
            'input_tokens': getattr(usage, 'prompt_token_count', None),
            'output_tokens': getattr(usage, 'candidates_token_count', None),
        }
        return _as_png(parts[0].inline_data.data), meta
    raise last_error


def _as_png(data: bytes) -> bytes:
    from PIL import Image

    image = Image.open(io.BytesIO(data))
    out = io.BytesIO()
    image.save(out, 'PNG')
    return out.getvalue()
