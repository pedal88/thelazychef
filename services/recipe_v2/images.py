"""Dish and component images for v2 recipes, in the order of RECIPE_VISUALIZATIONS.md 9.7.

1. How the dish and each part look (services/recipe_v2/appearance.py), kept on the recipe and its components.
2. The dish image first, from the prompt lab task dish_image with the variants in its [final] table,
   so the lab and the app build the same prompt.
3. A vision check of the dish image against the parts; one more try with what was missing.
4. An image of each part that is seen on its own, with the dish image as reference so they match,
   each checked against the dish image the same way. A dish with one part needs no part images.

What the checks still find wrong is kept in validation_errors (rule "image") for the admin. Old image
files are left in storage: deleting is not this module's job.
"""
import base64
import io
import json
import os
import uuid

from jinja2 import Environment, FileSystemLoader

from services.ai_models import RECIPE_V2_EFFORT, RECIPE_V2_MODEL
from services.image_generation import generate_image
from services.ingredient_symbols import web_image
from services.recipe_v2 import appearance, claude
from services.recipe_v2.store import to_v2

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
env = Environment(loader=FileSystemLoader(os.path.join(ROOT, 'data', 'prompts')))
FOLDER = 'recipes'
TASK = 'dish_image'
IMAGE_COST = 0.039  # USD per image from the Gemini image model
DISH_SIZE, PART_SIZE = 1200, 600
CHECK_SCHEMA = {
    'type': 'object', 'additionalProperties': False, 'required': ['ok', 'missing'],
    'properties': {'ok': {'type': 'boolean'}, 'missing': {'type': 'array', 'items': {'type': 'string'}}},
}


def ensure_appearance(recipe, call=None):
    """Describe the dish and its parts once. Returns the cost. A part not seen on its own gets ''."""
    if recipe.plating and all(c.appearance is not None for c in recipe.components):
        return 0.0
    look, usage = appearance.describe(to_v2(recipe), recipe.yield_text, recipe.chef_note, call=call)
    recipe.plating = look['plating']
    by = {c.local_id: c for c in recipe.components}
    for part in look['components']:
        if part['local_id'] in by:
            by[part['local_id']].appearance = part['appearance'] if part['visible'] else ''
    for c in recipe.components:
        if c.appearance is None:
            c.appearance = ''
    return usage.get('cost_usd') or 0.0


def visible_parts(recipe):
    return [c for c in recipe.components if c.appearance]


def dish_prompt(recipe):
    """(prompt, style) for the dish image, as the lab task's [final] variants build it."""
    from promptlab.compose import load_task

    task = load_task(TASK)
    sample = {'title': recipe.title, 'plating': recipe.plating or '',
              'components': [{'name': c.name, 'appearance': c.appearance} for c in visible_parts(recipe)]}
    return task.compose(task.final, sample), task.final.get('style')


def part_prompt(recipe, component):
    return ' '.join(env.get_template('recipe_v2/component_image.jinja2').render(
        title=recipe.title, name=component.name, appearance=component.appearance).split())


def _jpeg(png, size=1024):
    """A smaller copy for the vision check: fewer tokens, same answer."""
    from PIL import Image

    image = Image.open(io.BytesIO(png)).convert('RGB')
    image.thumbnail((size, size))
    out = io.BytesIO()
    image.save(out, 'JPEG', quality=85)
    return {'type': 'image', 'source': {'type': 'base64', 'media_type': 'image/jpeg',
                                        'data': base64.b64encode(out.getvalue()).decode()}}


def check_image(png, subject, expected, reference=None, call=None):
    """Ask a vision model whether the image shows what it should. Returns ({'ok', 'missing'}, cost)."""
    text = env.get_template('recipe_v2/image_check.jinja2').render(subject=subject, expected=expected, reference=reference)
    content = ([_jpeg(reference)] if reference else []) + [_jpeg(png), {'type': 'text', 'text': text}]
    msg, usage = (call or claude.call)(RECIPE_V2_MODEL, RECIPE_V2_EFFORT, [{'role': 'user', 'content': content}],
                                       schema=CHECK_SCHEMA)
    return json.loads(claude.text_of(msg)), usage.get('cost_usd') or 0.0


def _draw_checked(prompt, subject, expected, aspect, reference=None, draw=None, call=None):
    """Draw, check, and draw once more with what the check missed. Returns (png, prompt, missing, cost)."""
    draw = draw or generate_image
    cost, tried = 0.0, prompt
    for attempt in range(2):
        png, _ = draw(tried, references=[reference] if reference else None, aspect_ratio=aspect)
        verdict, check_cost = check_image(png, subject, expected, reference=reference, call=call)
        cost += IMAGE_COST + check_cost
        if verdict['ok']:
            return png, tried, [], cost
        if attempt == 0:
            tried = f"{prompt} Make sure of this: {'; '.join(verdict['missing'])}."
    return png, tried, verdict['missing'], cost


def make_images(recipe, storage, draw=None, call=None):
    """Make the dish image and the part images, and save them. Returns a report; the caller commits.

    draw and call stand in for the image model and Claude in tests."""
    cost = ensure_appearance(recipe, call=call)
    notes = []
    prompt, style = dish_prompt(recipe)
    parts = visible_parts(recipe)
    expected = recipe.plating + ''.join(f'\n- {c.name}: {c.appearance}' for c in parts)
    png, used, missing, spent = _draw_checked(prompt, f'one serving of {recipe.title}', expected, '4:3', draw=draw, call=call)
    cost += spent
    if missing:
        notes.append(f"Dish image: {', '.join(missing)}")
    name = f'dish_{recipe.id}_{uuid.uuid4().hex[:8]}.webp'
    storage.save(web_image(png, DISH_SIZE), name, FOLDER)
    recipe.image_filename, recipe.hero_image_prompt, recipe.image_style = name, used, style

    made = 0
    for c in recipe.components:
        c.image_filename = c.image_from = None
    if len(recipe.components) > 1:
        for c in parts:
            part, _, missing, spent = _draw_checked(part_prompt(recipe, c), f'only {c.name} from this dish', c.appearance,
                                                    '1:1', reference=png, draw=draw, call=call)
            cost += spent
            if missing:
                notes.append(f"{c.name}: {', '.join(missing)}")
            c.image_filename = f'part_{recipe.id}_{c.local_id}_{uuid.uuid4().hex[:8]}.webp'
            c.image_from = name
            storage.save(web_image(part, PART_SIZE), c.image_filename, FOLDER)
            made += 1

    kept = [e for e in recipe.validation_errors or [] if e.get('rule') != 'image']
    recipe.validation_errors = kept + [{'rule': 'image', 'message': n} for n in notes]
    return {'dish': name, 'parts': made, 'notes': notes, 'cost_usd': round(cost, 3)}
