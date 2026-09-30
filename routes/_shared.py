"""Helpers shared by the route modules that were split out of app.py."""
from flask import current_app


def get_storage():
    """The storage provider app.py creates at startup (local disk or GCS)."""
    return current_app.extensions['storage_provider']
