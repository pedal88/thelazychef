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


SPECS = {'ingredient_category': 'category_symbols.json', 'cuisine': 'cuisine_symbols.json'}


def concept_symbol(kind: str, name: str) -> tuple[bytes, str, dict]:
    """Return (PNG bytes, prompt, meta) for a concept in the same style as the ingredient symbols: a main ingredient
    category (three typical things) or a cuisine (a dish it is known for). What to show is in the kind's file in
    data/constraints (SPECS); it is the "name" the prompt shows, so the prompt's rule of showing only that still
    holds."""
    import json
    import os

    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'constraints', SPECS[kind])
    with open(path, encoding='utf-8') as f:
        spec = json.load(f)
    looks = spec['looks'].get(name)
    if not looks:
        raise KeyError(f'No looks for {name!r} in {SPECS[kind]}')
    main = name if kind == 'ingredient_category' else ''
    return generate_symbol({'name': looks, 'main_category': main, 'sub_category': '', 'image_form': spec['form']})


def category_symbol(main_category: str) -> tuple[bytes, str, dict]:
    """The symbol of a main ingredient category (concept_symbol)."""
    return concept_symbol('ingredient_category', main_category)


def web_image(png: bytes, size: int = WEB_SIZE) -> bytes:
    """A small WebP for the app: the generated PNGs are about 700 KB each."""
    from PIL import Image

    image = Image.open(io.BytesIO(png)).convert('RGB')
    image.thumbnail((size, size))
    out = io.BytesIO()
    image.save(out, 'WEBP', quality=85, method=6)
    return out.getvalue()
