"""Shared test setup: each test starts with an empty cache of built recipe pages, since test databases reuse ids."""
import pytest


@pytest.fixture(autouse=True)
def _fresh_recipe_cache():
    from services.recipe_v2 import view

    view.clear_cache()
    yield
