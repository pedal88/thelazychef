"""Admin notes on a recipe (database.models.RecipeNote) as text to paste elsewhere: to Claude, in an issue, in a chat.

    Recipe 298: Teriyaki salmon (The Smart Cook; vegetarian; draft; rev 3)
    https://thelazychef.app/recipe/298
    - [make · step 5] The timer should start when the sauce boils (23.10 18:40)
"""
import datetime
from zoneinfo import ZoneInfo

from services.recipe_v2.persona import SETTINGS

OSLO = ZoneInfo('Europe/Oslo')


def when(note):
    """The time a note was written, in Norwegian time (stored in UTC)."""
    return note.created_at.replace(tzinfo=datetime.timezone.utc).astimezone(OSLO).strftime('%d.%m %H:%M')


def heading(recipe):
    about = [recipe.chef.name] if recipe.chef else []
    about += [SETTINGS[s][0].lower() for s in (recipe.settings or []) if s in SETTINGS]
    if recipe.status != 'approved':
        about.append(recipe.status)
    if recipe.schema_version == 2:
        about.append(f'rev {recipe.revision}')
    return f"Recipe {recipe.id}: {recipe.title}" + (f" ({'; '.join(about)})" if about else '')


def line(note):
    text = '\n  '.join(note.text.strip().splitlines())
    return f"- {f'[{note.place}] ' if note.place else ''}{text} ({when(note)})"


def as_text(recipe, notes, url):
    """One recipe's notes as a block of text; url is the recipe's address."""
    return '\n'.join([heading(recipe), url] + [line(n) for n in notes])
