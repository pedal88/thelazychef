"""Ingredient symbols: one image per pantry ingredient, in the app's style.

The prompt comes from the prompt lab task data/prompts/lab/ingredient_image,
using the variants in its [final] table, so the app, the batch run and the
lab all build the same prompt. Try a change in the lab before changing
[final].
"""
import io

from services.image_generation import generate_image

TASK = 'ingredient_image'
WEB_SIZE = 512


def symbol_sample(ingredient) -> dict:
    """The fields the prompt layers use, from an Ingredient or a dict with the same keys."""
    get = ingredient.get if isinstance(ingredient, dict) else lambda k, d=None: getattr(ingredient, k, d)
    return {
        'name': get('name') or '',
        'main_category': get('main_category') or '',
        'sub_category': get('sub_category') or '',
        'form': get('image_form') or '',
        'notes': get('image_notes') or '',
    }


def symbol_prompt(ingredient) -> str:
    from promptlab.compose import load_task

    task = load_task(TASK)
    return task.compose(task.final, symbol_sample(ingredient))


def generate_symbol(ingredient) -> tuple[bytes, str, dict]:
    """Return (PNG bytes, prompt, meta) for one ingredient."""
    prompt = symbol_prompt(ingredient)
    png, meta = generate_image(prompt)
    return png, prompt, meta


def web_image(png: bytes, size: int = WEB_SIZE) -> bytes:
    """A small WebP for the app: the generated PNGs are about 700 KB each."""
    from PIL import Image

    image = Image.open(io.BytesIO(png)).convert('RGB')
    image.thumbnail((size, size))
    out = io.BytesIO()
    image.save(out, 'WEBP', quality=85, method=6)
    return out.getvalue()
