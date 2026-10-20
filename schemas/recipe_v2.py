"""Gemini response schema for recipe model v2 (docs/RECIPE_MODEL_V2.md).

Same style as RecipeSchema in ai_engine.py: TypedDicts passed as
`response_schema`. Scope is phase 0/2: components, ingredient lines and
steps as a graph. Not included: mise elements (phase 3), `waits` (derived from
setup steps on the same cookware), `{sN}` references and `output_label`.
"""
import json
import os

import typing_extensions as typing

_CONSTRAINTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'constraints')


def _load(name):
    with open(os.path.join(_CONSTRAINTS, name), encoding='utf-8') as f:
        return json.load(f)


# Closed lists, so structured output can only answer with values the app knows.
CUTS = tuple(c['id'] for c in _load('cuts.json')['cuts'])
CUISINES = tuple(_load('graph_metadata.json')['cuisines'])
DIFFICULTIES = tuple(_load('difficulty.json')['difficulty'])
MEAL_TYPES = tuple(m for group in ('Standard', 'Courses') for m in _load('meal_types.json')['meal_classification'][group])
Cut = typing.Literal[CUTS]
Cuisine = typing.Literal[CUISINES]
Difficulty = typing.Literal[DIFFICULTIES]
MealType = typing.Literal[MEAL_TYPES]


class ComponentV2(typing.TypedDict):
    local_id: str  # "c1", "c2", ...
    name: str  # what you can point at on the plate: "Kjøttsaus", "Ris"


class IngredientLineV2(typing.TypedDict):
    local_id: str  # "i1", "i2", ... referenced as {i3} in step text
    component_id: str  # local_id of a component
    name: str
    # Omitted (null) only for "etter smak" / "to taste"; then prep_style says so.
    amount: typing.NotRequired[float]
    unit: typing.NotRequired[str]  # id from data/constraints/units.json
    prep_style: typing.NotRequired[str]  # "finhakket", "i terninger", "etter smak"
    cut: typing.NotRequired[Cut]  # id from data/constraints/cuts.json; omitted when the line is not cut
    gram_weight_estimate: typing.NotRequired[float]
    pantry_id: typing.NotRequired[str]


class StepV2(typing.TypedDict):
    local_id: str  # "s1", "s2", ...
    component_id: str
    phase: str  # "prep" | "cook" | "serve"
    short: str  # max ~4 words, used in metro map, table and cards
    verb: typing.NotRequired[str]  # the action in short, with its particle: "kok opp", "stir in", "la dampe"
    text: str  # template text with {iN} for ingredient lines, no time words like "mens"
    uses: list[str]  # ingredient local_ids added in this step
    after: list[str]  # step local_ids whose result goes into this step
    active_minutes: int
    passive_minutes: int
    holds_minutes: typing.NotRequired[int]  # how long the result keeps; omitted = no limit
    method: str  # id from data/constraints/methods.json
    equipment: list[str]  # ids from data/constraints/equipment.json, first is the cookware
    temp_c: typing.NotRequired[int]  # applies to equipment[0]
    mode: typing.NotRequired[str]  # mode id from equipment.json, applies to equipment[0]
    setup: bool  # heating equipment: preheat oven, light grill, bring water to boil
    done_when: typing.NotRequired[str]  # sensory checkpoint


class RecipeV2Schema(typing.TypedDict):
    title: str
    servings: int
    components: list[ComponentV2]
    ingredients: list[IngredientLineV2]
    steps: list[StepV2]
    chef_note: typing.NotRequired[str]
    cuisine: typing.NotRequired[Cuisine]
    difficulty: typing.NotRequired[Difficulty]
    meal_types: typing.NotRequired[list[MealType]]
