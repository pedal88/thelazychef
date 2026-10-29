# scripts: maintenance and production scripts

Run as modules from the repo root: `python -m scripts.<name>`. Scripts that touch production are run by Pål on his
other machine with the environment in `docs/OPERATIONS.md` ("Production data from scripts"); give him the whole
command. Output that holds recipe content goes to `~/promptlab-runs/…`, never into the repo.

New production scripts follow `fill_pantry.py` and `review_recipes.py`: a docstring with the command and what it
costs, a dry run by default with `--apply` to save (or a read-only transaction), `getpass` for `DB_PASS` when missing,
and a printed summary that can be pasted back.

## In use

| Script | What |
|---|---|
| `review_recipes` | Read-only report of saved v2 recipes (`--ids`, `--search`): lines and pantry, steps, time, carbs, rules, notes |
| `fill_pantry` | Pantry job for recipes made before it ran, and recalculation (`--ids 1-400 --apply`); `--symbols`, `--looks "name=…"` for the symbols of pantry items it added |
| `category_symbols` | The galaxies' symbols: main ingredient categories, or `--kind cuisine`; `--only`, `--all` |
| `ingredient_symbols` | Ingredient symbols for the whole pantry: make, review, roll out; also `export` (the pantry as CSV, read only) |
| `equipment_symbols` | Symbols for the equipment catalog (`data/constraints/equipment.json`) |
| `ingredient_nutrition` | Nutrition for active ingredients that have none (Claude, USDA values) |
| `pantry_review` | Review the pantry against the core definition (`docs/RECIPE_MODEL_V2.md`) |
| `report_ingredient_states` | Read-only report of states, verbs, methods and the pantry |
| `units_report` | Read-only report of the measures in the recipes' free text that the US view cannot convert |
| `social_render` | Photograph a TikTok or Instagram post's slides from the site, with a caption draft (`docs/SOCIAL.md`) |
| `local_db` | A local SQLite database with the pantry and five example recipes (`docs/README_TOP_COMMANDS.md`) |
| `generate_v2` | Make one v2 recipe from the command line |
| `seed_admin` | Create or reset an admin user |
| `debug/verify_setup`, `debug/list_models`, `debug/check_db` | Check the Gemini key and models, the database |
| `setup_wif.sh` | Workload Identity Federation for GitHub Actions (done once) |

## Done, kept for the record

`retire_v1` (v1 recipes archived 27.10.2026), `convert_states` and `compare_states` (the state catalog, 26–27.10),
`chef_trial`, `foundation_sample`, `dish_image_samples`, `pilot_v2`, `pilot_v2b`, `pilot_v2_export_fasit.mjs`,
`make_planner_golden.mjs` (pilots and samples behind design decisions).

## Outdated: from before recipe model v2, may not run

`admin_reset`, `audit_transparency`, `backfill_nutrition_full` (Edamam, ended), `check_ingredient`, `cleanup_users`,
`create_admin`, `export_pantry`, `fix_missing_chefs`, `generate_ingredient_embeddings` (Vertex),
`get_admin_hash`, `init_prod_db`, `seed_data`, `seed_db`, `setup_gcs_cors`, `deploy.sh`, `setup_infra.sh`,
`maintenance/seed_data`. Read one before using it; prefer deleting it in its own PR over fixing it.
