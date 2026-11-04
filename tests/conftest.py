"""Shared test setup: each test starts with an empty cache of built recipe pages, since test databases reuse ids."""
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope='session', autouse=True)
def _compiled_translations():
    """The .mo files are not in git; the Dockerfile compiles them for production, this for the tests."""
    from babel.messages.frontend import CommandLineInterface

    CommandLineInterface().run(['pybabel', '--quiet', 'compile', '-d', str(ROOT / 'translations')])


@pytest.fixture(autouse=True)
def _fresh_recipe_cache():
    from services.recipe_v2 import view

    view.clear_cache()
    yield
