"""Helpers shared by the route modules that were split out of app.py."""
import json
import os

from flask import current_app, url_for

from services.storage_service import GoogleCloudStorageProvider


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
