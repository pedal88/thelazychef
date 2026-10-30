# data: catalogs, prompts and seed data the code reads

These files are part of the app: the code reads them at run time, and a change here changes behaviour in production
on the next deploy. Several are checked by tests (the protein labels, the category and cuisine symbol descriptions,
every migration move ending in the category catalog).

## constraints/ (the catalogs)

| File | What |
|---|---|
| `states.json` | The state catalog: what is done to an ingredient before it goes in (chopped, grated…), with grades, synonyms, the step methods that leave a line in that state, and the drawing signs. Read by `services/recipe_v2/states.py`, the structuring prompt and the validator |
| `methods.json`, `equipment.json`, `units.json` | Step methods (with `heat`), the equipment bank (role, `exclusive`, `capacity`: the air fryer has 2), units with grams/ml |
| `us_volume.json` | What US recipes measure by volume although the recipe weighs it (flour, sugar, butter, spices), with grams per ml: rules on the pantry name or sub-category (`services/measures.density`) |
| `categories.json` | The pantry's main and sub categories, the only allowed values (New ingredient and the pantry job) |
| `main_protein.json` | The protein labels the recipe filter offers (they must cover what `derive.main_protein` writes) and `symbol_from`, the pantry item whose symbol stands for each label in the galaxy |
| `graph_metadata.json` | The cuisines (`CUISINES` in `schemas/recipe_v2.py`) with notes for the prompt; retired cuisines |
| `category_symbols.json`, `cuisine_symbols.json` | What the galaxies' category and cuisine symbols show (`scripts/category_symbols.py`) |
| `age_stages.json` | Baby food stages (6, 8, 12 months): what a recipe for that age must avoid |
| `diets.json`, `meal_types.json`, `difficulty.json` | Controlled vocabularies for tags |
| `pantry_seed.json` | The pantry as seeded for a fresh database (production has moved on; it is not the truth for prod) |
| `taxonomy_contexts.json` | Descriptions per tag type; nothing in the code reads it today |

`post_processing/` (cuisines, cooking methods, taste, clean-up, time intervals) feeds the older vocabulary loader
(`ai_engine.load_controlled_vocabularies`), the admin filters and the recipe list's cuisine filter. Its
`cuisines.json` must list the same cuisines as `graph_metadata.json`; change both together.

## agents/chefs.json

The seed of the chef personas. **The live personas are in the `chef` table** (edited in Admin → Chefs); this file
only seeds a fresh database. Rules such as the Minimalist's limits are changed in the admin, not here.

## prompts/

- `recipe_v2/`: the generation prompts (Jinja): `text` (round 1), `structure` (round 2, with the catalogs, the
  pantry and two example recipes), `idea`, `version`, `video_text`, `normalize`, `appearance`, `component_image`,
  `image_check`, `pantry_fill`, and `idea_helper.txt` (the prompt users copy to their own AI).
- `lab/`: prompt lab tasks (`ingredient_image`, `dish_image`, `equipment_image`), built from layers; the `[final]`
  table in each `task.toml` is what the app uses. Try changes with `python -m promptlab` first (`docs/PROMPT_LAB.md`).
- The other folders (`factory`, `ingredient_*`, `pantry`, `resource_*`, `social`) are prompts for the admin tools.

## pilot_v2/

`fasit/`: hand-made reference recipes, used as examples in the structuring prompt and as test fixtures. `inputs/`,
`results*/`: the pilots behind the choice of Claude for generation (`docs/pilot/`).
