# services/recipe_v2: the recipe model

A recipe is a graph: **components** (the parts of a dish: sauce, rice), **lines** (an ingredient at one moment:
amount, unit, state such as "chopped", grade, variety, pantry link) and **steps** (method, verb, short text,
equipment, active and standing minutes, which lines and earlier steps they use). Tables: `RecipeComponent`,
`RecipeLine`, `RecipeStep` in `database/models.py`; the JSON shape is `schemas/recipe_v2.py`. Design and reasons:
`docs/RECIPE_MODEL_V2.md` (Norwegian).

## Making a recipe

`generate.create_recipe(kind, source, …)`:

1. Round 1 (`write_text`): Claude writes or tidies the recipe as plain text, in the chef persona's voice
   (`persona.spec` + `prompt_block`; idea, link, video, pasted text or a version of another recipe).
   Links and videos are read by `sources.py` (web scraping, or Gemini watching the video).
2. Round 2 (`structure`): Claude turns the text into the graph with structured output. `services/recipe_v2_validator.py`
   checks it; errors go back for at most `MAX_RETRIES = 2` new attempts. A recipe still invalid is saved as a flagged
   draft with its errors.
3. `match_pantry` links lines to pantry items (`services/recipe_service._resolve_ingredient`: the model's pantry id,
   then exact name, alias, fuzzy match). `store.save_v2` writes the graph.
4. `refresh`: `derive.apply` (heat source, main protein, clean-up, total time from the planner, derived meal tags),
   `nutrition.apply`, and the chef's hard rules (`persona.check`, noted with rule `persona`).

In production this runs in Cloud Tasks (`tasks.py`), followed by the **pantry job** (`pantry_fill.py`: Claude decides
alias / new item / skip for every unlinked line, then `generate.recalculate`) and the **image job** (`images.py`:
the dish and its visible parts, each checked by Claude's vision). See `docs/SERVICES_AND_COSTS.md` for the queue.
`batch.py` reads the Many recipes at once lines.

`generate.recalculate(recipe)` is what the Recalculate button and `scripts.fill_pantry` do: link unlinked lines again,
then `refresh`. Run it on saved recipes after changing derive, nutrition or the chefs' rules.

## Showing a recipe

- `view.page(recipe, servings, plan)` builds everything the one recipe page (`templates/recipe_v2_make.html`) shows.
- `planner.plan_v2(v2, mode, kitchen)` schedules the steps (modes `calm`, `prep`, `jit`); equipment capacity comes from
  `data/constraints/equipment.json` (the air fryer has two drawers) and can be overridden per kitchen.
- `mise.py` (Prep: what to set out, the bowls), `whole.py` (timeline and metro map), `delta.py` (the river delta
  drawing), `groups.py` (kitchen groups for the ingredient list), `read.py`.
- `states.py` is the state catalog (`data/constraints/states.json`): what is done to an ingredient before it goes in.

## Rules that are easy to break

- Every function that calls Claude takes `call=None` (default `claude.call`), so tests pass a stand-in; tests must
  never reach Claude, Gemini or Google. Recorded answers are in `data/pilot_v2/`.
- Saved recipes do not change when code changes: derived fields and nutrition change only on `recalculate`.
- Notes on `recipe.validation_errors` have a `rule`. `persona` and the image check flag a recipe for review;
  `pantry` (what the pantry job did) is information only and does not flag it.
- Nutrition counts the grams that end up in the food (`gram_weight` from the model, else units). Cooked rice, pasta
  and pulses are converted to dry weight (`nutrition.COOKED_GAIN`). The totals are hidden when under 95 % of the
  weight is in the pantry.
- `derive.main_protein`'s labels are the protein filter's (`data/constraints/main_protein.json`, a test checks).
  Cured meat used for flavour counts at half weight and never beats real meat or fish.
- The `cut` field in old JSON (`line.get('cut')`) is still read as a state by the validator and views; the database
  column is gone.
