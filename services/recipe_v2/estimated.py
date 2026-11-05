"""Amounts the source did not give (RecipeLine.estimated, set by the structuring prompt).

A recipe from a video with no amounts is in practice the model's own guess at the dish, so the reader is told and it is
not published on trust. The reader sees "about" on each such amount (view.said_about), and a sentence when over SAY_SHARE of
the weight is estimated. Over HOLD_SHARE the recipe cannot be approved until Pål has tried it or accepts it. Salt, pepper
and garnish "to taste" have no amount and do not count. Recipes made before this have no marks, and nothing holds them.
"""
import datetime

from services.recipe_v2.generate import ACCEPTED
from services.recipe_v2.nutrition import grams

HOLD_SHARE = 0.3
SAY_SHARE = 0.5


def share(lines):
    """The part of the lines' weight that has an estimated amount, from 0 to 1."""
    weights = [(grams(line) or 0, line.estimated) for line in lines]
    total = sum(g for g, _ in weights)
    return sum(g for g, said in weights if said) / total if total else 0


def accepted(recipe):
    return any(e.get('rule') == ACCEPTED for e in recipe.validation_errors or [])


def holds(recipe):
    """True when the recipe cannot be approved yet."""
    return share(recipe.lines) > HOLD_SHARE and not accepted(recipe)


def accept(recipe):
    """Note that Pål has tried it or accepts it. The caller commits."""
    if not accepted(recipe):
        recipe.validation_errors = list(recipe.validation_errors or []) + [{
            'rule': ACCEPTED, 'message': 'Tried or accepted with its estimated amounts',
            'at': datetime.datetime.now(datetime.UTC).isoformat()}]
