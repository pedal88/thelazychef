"""Chef personas, stored in the `chef` table.

The JSON columns (constraints, cooking_style, ...) are Text in the database.
chef_to_dict() turns a row into the same shape as data/agents/chefs.json, which
is what the templates expect. data/agents/chefs.json is only seed data now: a
migration copies missing chefs from it into the table.
"""
import json

from database.models import Chef, db

# Text columns holding JSON, with the empty value used when a column is blank
JSON_FIELDS = {
    'constraints': {},
    'diet_preferences': [],
    'cooking_style': {},
    'ingredient_logic': {},
    'instruction_style': {},
}
TEXT_FIELDS = ('name', 'archetype', 'description')

# constraints holds the persona's hard rules (services/recipe_v2/persona.py). None means no limit.
DIFFICULTIES = ['Simplistic', 'Moderate', 'Elevated']
DEFAULT_RULES = {'max_total_minutes': None, 'max_cleanup': None, 'max_spice': None, 'difficulties': DIFFICULTIES,
                 'diet': None, 'max_carbs_per_serving': None}


def rules_of(constraints: dict) -> dict:
    """The hard rules, with defaults. Chefs still in the old shape (1-5 sliders for taste, speed, complexity,
    richness and clean-up) keep what maps: complexity becomes the allowed difficulties, clean-up its maximum."""
    rules = {**DEFAULT_RULES, **{k: v for k, v in constraints.items() if k in DEFAULT_RULES}}
    old = constraints.get('complexity_range')
    if old and 'difficulties' not in constraints:
        rules['difficulties'] = DIFFICULTIES[max(1, old.get('min', 1)) - 1:min(3, old.get('max', 3))]
    old = constraints.get('cleanup_range')
    if old and 'max_cleanup' not in constraints and old.get('max', 5) < 5:
        rules['max_cleanup'] = old['max']
    return rules


def _load(value, empty):
    try:
        loaded = json.loads(value) if value else empty
    except (TypeError, ValueError):
        return empty
    return loaded if isinstance(loaded, type(empty)) else empty


def chef_to_dict(chef: Chef) -> dict:
    data = {
        'id': chef.id,
        'name': chef.name,
        'archetype': chef.archetype or '',
        'description': chef.description or '',
        'image_filename': chef.image_filename,
    }
    for field, empty in JSON_FIELDS.items():
        data[field] = _load(getattr(chef, field), type(empty)())
    data['constraints'] = rules_of(data['constraints'])
    data['cooking_style'].setdefault('preferred_methods', [])
    data['cooking_style'].setdefault('avoid_methods', [])
    data['ingredient_logic'].setdefault('staples', [])
    data['ingredient_logic'].setdefault('banned_ingredients', [])
    return data


def get_chefs() -> list[dict]:
    """All chefs as dicts, sorted by name."""
    chefs = db.session.execute(db.select(Chef).order_by(Chef.name)).scalars().all()
    return [chef_to_dict(c) for c in chefs]


def update_chefs(chefs: list[dict]) -> list[str]:
    """Apply edits from the chef editor and commit.

    Only updates chefs that already exist; the editor can't create or delete
    them, and recipes reference chefs by id. Fields missing from a payload
    (e.g. image_filename, which the editor doesn't send) are left as they are.
    All or nothing: if any id is unknown, nothing is saved and those ids are
    returned. Returns [] on success.
    """
    rows = {data.get('id'): db.session.get(Chef, data.get('id')) for data in chefs}
    missing = [chef_id for chef_id, chef in rows.items() if chef is None]
    if missing:
        return missing
    for data in chefs:
        chef = rows[data['id']]
        for field in TEXT_FIELDS:
            if field in data:
                setattr(chef, field, data[field])
        for field in JSON_FIELDS:
            if field in data:
                setattr(chef, field, json.dumps(data[field]))
    db.session.commit()
    return []
