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
   Links and videos are read by `sources.py` (web scraping, or Gemini watching the video). A link the site will not
   let us read leaves a flagged draft without steps (rule `source`); the admin pastes the recipe's text on it in the
   admin chip (`recipe_v2_routes.paste_source`), it is made into the same recipe, and the link stays its source.
   A placeholder's text is saved as soon as it is written: that is how the waiting page knows round 2 has begun.
2. Round 2 (`structure`): Claude turns the text into the graph with structured output. `services/recipe_v2_validator.py`
   checks it; errors go back for at most `MAX_RETRIES = 2` new attempts. A recipe still invalid is saved as a flagged
   draft with its errors.
3. `match_pantry` links lines to pantry items by name only (`services/recipe_service._resolve_ingredient`: exact name,
   alias, fuzzy match). The model's `pantry_id` links nothing: it points at the nearest item, a swap nobody would see. `store.save_v2` writes the graph.
4. `refresh`: `derive.apply` (heat source, main protein, clean-up, total time from the planner, derived meal tags),
   `nutrition.apply`, and the chef's hard rules (`persona.check`, noted with rule `persona`).

In production this runs in Cloud Tasks (`tasks.py`), followed by the **pantry job** (`pantry_fill.py`: for every unlinked line
Claude decides, in this dish: alias (the same food), substitute (another pantry item, changed in this recipe only), ask
(a pending item and a question Pål answers on `/admin/pantry-questions`; the recipe cannot be approved until then, and `weigh`
shares 100 points across adding it and up to five swaps, as advice on that page) or skip; then `generate.recalculate`) and the **image job** (`images.py`:
the dish and its visible parts, each checked by Claude's vision). See `docs/SERVICES_AND_COSTS.md` for the queue.
While the pantry job is queued or at work, a note on the recipe (`mark_checking`) makes the recipe page say so instead of "Not in the pantry", and it reloads when the job is done.
`batch.py` reads the Many recipes at once lines.
`inbox.py` saves video links shared from the phone, one or many (table `video_inbox`, `/admin/inbox`, `docs/VIDEO_INBOX.md`); saving makes nothing, but the video is read in the background, and the recipe is later made from that text.

Recipes choose from the pantry first. A recipe the model writes itself (`idea`, `version`) sees the pantry's names in
round 1 (`choose_pantry.jinja2`), and may go outside it when the dish needs that; one from a source is written as the
source says, and its lines meet the pantry job. `source_text` keeps what the source said after a swap. Only Pål lets new
items in. A swap is never an alias: an alias holds for every recipe, and a swap that is fine in one dish ruins another.

`generate.recalculate(recipe)` is what the Recalculate button and `scripts.fill_pantry` do: link unlinked lines again,
then `refresh`. Run it on saved recipes after changing derive, nutrition or the chefs' rules.

## Showing a recipe

- `view.page(recipe, servings, plan)` builds everything the one recipe page (`templates/recipe_v2_make.html`) shows.
- `planner.plan_v2(v2, mode, kitchen)` schedules the steps (modes `calm`, `prep`, `jit`); equipment capacity comes from
  `data/constraints/equipment.json` (the air fryer has two drawers) and can be overridden per kitchen.
- `mise.py` (Prep: what to set out, the bowls), `whole.py` (timeline and metro map), `delta.py` (the river delta
  drawing), `groups.py` (kitchen groups for the ingredient list), `read.py`.
- Amounts and temperatures are written in the reader's measuring system, metric or US (`services/measures.py`;
  `routes/_shared.unit_choice()`: the user's `unit_system`, else the `units` cookie, else metric, and US once for a
  browser in a US time zone). For a US reader flour, sugar, butter and spices weighed in g become cups and spoons
  (`data/constraints/us_volume.json`), the shopping list sums an item across units (`fmt_total`), and the
  nutrition table is the US label (sodium in mg). Only the display converts: the stored recipe, `gram_weight`,
  nutrition, the planner and Prep's rules read the stored units. Measures in free text (a step's text, short and
  done_when, the chef's note, the yield) are converted by `measures.localize_text` when written metric as number,
  space, unit ("200 °C", "3 cm", "2 dl"; structuring prompt rule 8b). What it cannot convert gives the validator
  warning `us_measure` (US units) or `missed_measure` (metric, but not as number, space, unit: "et par dl"); `scripts/units_report.py` lists it in the saved recipes. Tins sized in cm have `name_us`.
- The page is drawn in the reader's language: `view.page` keeps one build per language, the units, equipment, modes and states take their Norwegian from the catalogs (`measures`, `view.equipment_name`, `states.word`), and `language.shown()` is what they ask, which `force_locale` overrides: `as_text`/`v2_text` go to Claude in English, and the slides are English by their address. The recipe's own text comes from `translation.py`: one `RecipeTranslation` per recipe and language, by `local_id`, laid over `to_v2()` in `build`. When the recipe's words change it no longer matches `source_hash` and the page shows them as written until they are translated again. Lists take their titles with `translation.dress`, one query a page. `translate.py` asks Claude for the words and the pantry's names, with the glossary `data/constraints/glossary_nb.json`; a recipe is translated when it is approved (`tasks.run_translation`, in the queue, with its pantry items that have no Norwegian name), so nothing is paid for a draft that is rejected, and `scripts/translate.py` does what that misses. The recipe list searches the translated title and `name_nb` for a Norwegian reader. `Ingredient.name_nb` is the pantry's Norwegian name (`translation.ingredient_name`), and empty shows `name`.
- `states.py` is the state catalog (`data/constraints/states.json`): what is done to an ingredient before it goes in.

## Rules that are easy to break

- Every function that calls Claude takes `call=None` (default `claude.call`), so tests pass a stand-in; tests must
  never reach Claude, Gemini or Google. Recorded answers are in `data/pilot_v2/`.
- Saved recipes do not change when code changes: derived fields and nutrition change only on `recalculate`.
- Notes on `recipe.validation_errors` have a `rule`. `persona` and the image check flag a recipe for review;
  `ask` flags it too, until Pål answers. `pantry` (what the pantry job did), `substitute` (a swap), `asked` (Pål's answer,
  which Claude sees the next time) and `estimate` (what the source did not say and the model decided, such as an
  amount a video never gives) are information only and do not flag it (`generate.INFORMATION`). The admin chip shows
  the estimates. `chef_note` is the cook's tip and is public, so what the model decided never goes there.
- A line whose amount the source did not give has `RecipeLine.estimated` (`estimated.py`). The reader sees "about" on the
  amount, and a sentence when over half the weight is estimated. Over 30 % a recipe cannot be approved until Pål has tried
  it or accepts it in the admin chip (note `estimates_accepted`). Recipes made before have no marks.
- Nutrition counts the grams that end up in the food (`gram_weight` from the model, else units). Cooked rice, pasta
  and pulses are converted to dry weight (`nutrition.COOKED_GAIN`). A line whose variety says its fat ("4 % fat") counts
  that fat, with the calories and saturated fat that follow. The totals are hidden when under 95 % of the weight is in
  the pantry.
- `derive.main_protein`'s labels are the protein filter's (`data/constraints/main_protein.json`, a test checks).
  Cured meat used for flavour counts at half weight and never beats real meat or fish.
- The `cut` field in old JSON (`line.get('cut')`) is still read as a state by the validator and views; the database
  column is gone.
