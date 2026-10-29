"""Helpers shared by the route modules that were split out of app.py."""
import json
import os

from flask import current_app, request, url_for
from markupsafe import Markup
from flask_login import current_user

from services.storage_service import GoogleCloudStorageProvider


# Stored difficulty (data/constraints/difficulty.json) -> what readers see. The stored values stay as they are.
DIFFICULTY_LABELS = {'Simplistic': 'Easy', 'Moderate': 'Medium', 'Elevated': 'Challenging'}

def viewer_is_admin() -> bool:
    """Public routes show drafts, pending ingredients and unpublished pages only to admins."""
    return bool(current_user.is_authenticated and getattr(current_user, 'is_admin', False))


def public_url(endpoint, **values):
    """An absolute address, for text copied out of the app. Behind Cloud Run's proxy the app sees http, so https
    unless it runs on this machine."""
    url = url_for(endpoint, _external=True, **values)
    local = request.host.split(':')[0] in ('localhost', '127.0.0.1')
    return url if local else url.replace('http://', 'https://', 1)


def notes_text(recipe, notes=None):
    """A recipe's open admin notes (or the notes given) as text to paste elsewhere (services/recipe_notes.py)."""
    from services.recipe_notes import as_text
    notes = [n for n in recipe.notes if not n.done] if notes is None else notes
    return as_text(recipe, notes, public_url('recipe_detail', recipe_id=recipe.id))


def get_storage():
    """The storage provider app.py creates at startup (local disk or GCS)."""
    return current_app.extensions['storage_provider']


def get_recipe_image_url(recipe):
    """Generates the correct URL for a recipe image based on storage backend."""
    if not recipe or not recipe.image_filename:
        return None
    
    # If using GCS, return the public URL directly
    # We construct it manually or use storage_provider if it had a get_url method
    # But for now, we know the pattern or can assume public access for simplicity
    # The storage provider saves as "recipes/<filename>" or just "<filename>" in recipes folder?
    # Let's check storage provider usage.
    
    storage_provider = get_storage()
    is_gcs = isinstance(storage_provider, GoogleCloudStorageProvider)
    
    if is_gcs:
        # GCS Public URL Convention: https://storage.googleapis.com/<bucket>/<blob_path>
        # The app saves/moves items to "recipes" folder.
        return f"https://storage.googleapis.com/{storage_provider.bucket_name}/recipes/{recipe.image_filename}"
    else:
        # Local Flask Static
        return url_for('static', filename='recipes/' + recipe.image_filename)


# The site menu: one list for the top bar and the phone menu (components/site_menu.html). A group: (label, who, items); an item: (label, endpoint, url arguments, icon, who), or
# None for a line between items. who: 'all', 'user' (signed in) or 'admin'. A group with one item is a plain link.
MENU = [
    ('Discover', 'all', [('Discover recipes', 'discover', {}, 'search', 'all'),
                         ('Galaxy map', 'explore_galaxy', {}, 'galaxy', 'all')]),
    ('Recipes', 'all', [('All recipes', 'recipes_list', {}, 'book', 'all'),
                        None,
                        ('Saved', 'saved_recipes_view', {}, 'heart', 'user'),
                        ('Made', 'recipes_list', {'view': 'made'}, 'check', 'user'),
                        ('Cook next', 'queue.next_recipes_view', {}, 'pot', 'user'),
                        ('Recipe Mirror', 'mirror_hub', {}, 'mirror', 'user')]),
    ('Ingredients', 'all', [('All ingredients', 'pantry_management', {}, 'carrot', 'all'),
                            ('Ingredient galaxy', 'explore_ingredient_galaxy', {}, 'galaxy', 'all')]),
    ('Admin', 'admin', [('New recipe', 'new_recipe', {}, 'pot', 'admin'),
                        ('Many recipes at once', 'recipe_v2.batch_new', {}, 'list', 'admin'),
                        ('Images for recipes', 'recipe_v2.batch_images', {}, 'image', 'admin'),
                        ('New ingredient', 'new_ingredient_view', {}, 'carrot', 'admin'),
                        None,
                        ('Recipes', 'admin_recipes_management', {}, 'clipboard', 'admin'),
                        ('Notes on recipes', 'notes.overview', {}, 'file-plus', 'admin'),
                        ('Pages', 'content.admin_pages', {}, 'book', 'admin'),
                        ('Ingredients', 'ingredients_mgmt.dashboard', {}, 'package', 'admin'),
                        ('Chefs', 'chefs_list', {}, 'chef', 'admin')]),
]


def site_menu():
    """The menu for the person looking: [{'label', 'items': [{'label', 'url', 'icon'} or None]}], without what they
    may not see and without a line at the start or end of a group, or two in a row."""
    user = current_user.is_authenticated
    admin = user and getattr(current_user, 'is_admin', False)
    sees = {'all': True, 'user': user, 'admin': admin}
    out = []
    for label, who, items in MENU:
        if not sees[who]:
            continue
        shown = []
        for item in items:
            if item is None:
                if shown and shown[-1] is not None:
                    shown.append(None)
            elif sees[item[4]]:
                shown.append({'label': item[0], 'url': url_for(item[1], **item[2]), 'icon': item[3]})
        while shown and shown[-1] is None:
            shown.pop()
        if shown:
            out.append({'label': label, 'items': shown})
    return out


def icon(name, label=None, cls=''):
    """A line icon from static/icons/icons.svg. Without a label it is decoration and hidden from screen readers."""
    src = url_for('static', filename='icons/icons.svg')
    who = Markup('role="img" aria-label="{}"').format(label) if label else Markup('aria-hidden="true"')
    return Markup('<svg class="icon {}" {} focusable="false"><use href="{}#i-{}"/></svg>').format(cls, who, src, name)


def get_image_url(filename):
    """Translates a raw filename to its full public URL based on the active storage backend."""
    if not filename:
        return ""
    
    storage_provider = get_storage()
    is_gcs = isinstance(storage_provider, GoogleCloudStorageProvider)
    if is_gcs:
        return f"https://storage.googleapis.com/{storage_provider.bucket_name}/recipes/{filename}"
    else:
        return url_for('static', filename='recipes/' + filename)


def load_json_option(filename, key):
    data_dir = os.path.join(current_app.root_path, 'data')
    try:
        with open(os.path.join(data_dir, filename), 'r') as f:
            return json.load(f).get(key, [])
    except:
        return []


# Image trial (temporary): the style of the dish and part images an admin has switched to (a cookie set by the
# switch on the recipe pages). Visitors and the recipe cards always get the recipe's own images.
IMAGE_STYLES = {'cutout': 'White', 'editorial': 'Angled', 'overhead': 'From above', 'illustrated': 'Illustrated'}


def chosen_image_style():
    """The admin's chosen image style, or None: everyone else gets the recipe's own images."""
    style = request.cookies.get('dish_images')
    admin = current_user.is_authenticated and getattr(current_user, 'is_admin', False)
    return style if admin and style in IMAGE_STYLES else None


# Overview layout trial (temporary): how the overview of the one-page flow is laid out to fit one screen. "poster"
# (A) has the image over half the screen beside the ingredients; "compact" (C) a plate at the top and the ingredients
# in columns under it. The first layout ("now") was dropped 25.10.2026. Cookie overview_layout, admins only.
OVERVIEW_LAYOUTS = {'poster': 'A Poster', 'compact': 'C Compact'}


def chosen_overview():
    style = request.cookies.get('overview_layout')
    return style if style in OVERVIEW_LAYOUTS else 'poster'


# Equipment symbol trial (temporary): the same, for the equipment symbols (data/constraints/equipment.json "image" is
# the realistic set, "image_variants" the others). Cookie equipment_images, admins only; everyone else gets the default.
EQUIPMENT_STYLES = {'realistic': 'Realistic', 'painted': 'Painted', 'line_tint': 'Line'}


DEFAULT_EQUIPMENT_STYLE = 'line_tint'  # Pål's favourite for now (23.10.2026), not final


def chosen_equipment_style():
    """The admin's chosen equipment style; the default for everyone else."""
    style = request.cookies.get('equipment_images')
    admin = current_user.is_authenticated and getattr(current_user, 'is_admin', False)
    return style if admin and style in EQUIPMENT_STYLES else DEFAULT_EQUIPMENT_STYLE


def equipment_image(item):
    """The symbol of an equipment item (from view.equipment_list) in the chosen style, else the realistic one."""
    return (item.get('images') or {}).get(chosen_equipment_style()) or item.get('image')


def dish_images(recipe):
    """The dish and part images in the chosen style: a trial variant when there is one, else the recipe's own.
    have is False when the chosen style has no images for this recipe yet."""
    own_style = recipe.image_style or 'cutout'
    style = chosen_image_style() or own_style
    variant = (recipe.image_variants or {}).get(style) if style != own_style else None
    if variant:
        files = variant.get('parts') or {}
        parts = [{'name': c.name, 'url': get_image_url(files[c.local_id])} for c in recipe.components if c.local_id in files]
        return {'style': style, 'dish': get_image_url(variant['dish']), 'parts': parts, 'have': True}
    parts = [{'name': c.name, 'url': get_image_url(c.image_filename)} for c in recipe.components if c.image_filename]
    return {'style': style, 'dish': get_recipe_image_url(recipe), 'parts': parts,
            'have': style == own_style and bool(recipe.image_filename)}
