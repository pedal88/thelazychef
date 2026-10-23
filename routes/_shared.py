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


# Ingredient list trial (temporary): four ways to show the ingredients on Overview, for admins (cookie ing_list).
# Everyone else sees the list as it is ('now').
LIST_STYLES = {'now': 'Now', 'a': 'A', 'b': 'B', 'c': 'C', 'd': 'D'}


def chosen_list_style():
    style = request.cookies.get('ing_list')
    admin = current_user.is_authenticated and getattr(current_user, 'is_admin', False)
    return style if admin and style in LIST_STYLES else 'now'


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
