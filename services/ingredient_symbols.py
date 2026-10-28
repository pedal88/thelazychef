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


def category_symbol(main_category: str) -> tuple[bytes, str, dict]:
    """Return (PNG bytes, prompt, meta) for a main ingredient category: three typical things in the same style
    (data/constraints/category_symbols.json). The things are the "name" the prompt shows, so its rule of showing
    only that still holds."""
    import json
    import os

    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'constraints',
                        'category_symbols.json')
    with open(path, encoding='utf-8') as f:
        spec = json.load(f)
    looks = spec['looks'].get(main_category)
    if not looks:
        raise KeyError(f'No looks for the category {main_category!r} in category_symbols.json')
    return generate_symbol({'name': looks, 'main_category': main_category, 'sub_category': '', 'image_form': spec['form']})


def web_image(png: bytes, size: int = WEB_SIZE) -> bytes:
    """A small WebP for the app: the generated PNGs are about 700 KB each."""
    from PIL import Image

    image = Image.open(io.BytesIO(png)).convert('RGB')
    image.thumbnail((size, size))
    out = io.BytesIO()
    image.save(out, 'WEBP', quality=85, method=6)
    return out.getvalue()
