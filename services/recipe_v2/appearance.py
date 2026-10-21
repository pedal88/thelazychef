"""How a finished dish and each of its parts look, for the dish and component images.

Step 2 of RECIPE_VISUALIZATIONS.md 9.7: the image prompts are built from these
descriptions, not from the recipe text, so the dish image and the component
images describe the same food. Claude writes them from the saved recipe, in
English whatever the recipe's language.
"""
import json
import os

from jinja2 import Environment, FileSystemLoader

from services.ai_models import RECIPE_V2_EFFORT, RECIPE_V2_MODEL
from services.recipe_v2 import claude
from services.recipe_v2.view import v2_text

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
env = Environment(loader=FileSystemLoader(os.path.join(ROOT, 'data', 'prompts')))
SCHEMA = {
    'type': 'object', 'additionalProperties': False, 'required': ['plating', 'components'],
    'properties': {
        'plating': {'type': 'string'},
        'components': {'type': 'array', 'items': {
            'type': 'object', 'additionalProperties': False, 'required': ['name', 'visible', 'appearance'],
            'properties': {'name': {'type': 'string'}, 'visible': {'type': 'boolean'}, 'appearance': {'type': 'string'}}}},
    },
}


def describe(v2, yield_text=None, chef_note=None, call=None):
    """Returns ({'plating', 'components': [{'local_id', 'name', 'visible', 'appearance'}]}, usage) for a recipe in v2 JSON.

    Parts are matched to the recipe's components by name; a part with another name gets the first component
    left over."""
    prompt = env.get_template('recipe_v2/appearance.jinja2').render(recipe=v2_text(v2, yield_text, chef_note))
    msg, usage = (call or claude.call)(RECIPE_V2_MODEL, RECIPE_V2_EFFORT, [{'role': 'user', 'content': prompt}],
                                       schema=SCHEMA)
    data = json.loads(claude.text_of(msg))
    comps = v2.get('components') or []
    by_name = {c['name'].strip().lower(): c for c in comps}
    named = {id(by_name[p['name'].strip().lower()]) for p in data['components'] if p['name'].strip().lower() in by_name}
    left = [c for c in comps if id(c) not in named]
    out = []
    for part in data['components']:
        comp = by_name.get(part['name'].strip().lower()) or (left.pop(0) if left else None)
        out.append({'local_id': comp['local_id'] if comp else None, 'name': comp['name'] if comp else part['name'],
                    'visible': part.get('visible', True), 'appearance': part['appearance'].strip()})
    return {'plating': data['plating'].strip(), 'components': out}, usage
