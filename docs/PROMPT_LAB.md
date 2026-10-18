# Prompt lab

Try prompt variants side by side on a small set of samples, keep a log of every run, and score the results. Prompts are files in the repo, edited in an editor or Claude Code and versioned in git. This replaces the old Prompt Studio and Style Center pages.

## Tasks

A task is a folder in `data/prompts/lab/`:

```
data/prompts/lab/ingredient_image/
  task.toml        kind (image or text), model, layer order
  brief/           default.j2 (empty), style_center.j2
  style/           one file per variant: default.j2, vector.j2, isometric.j2, cutout.j2, …
  category/        default.toml, none.toml
  item/            default.j2
  samples.toml     sample sets to run on
```

The prompt is the layers joined in the order `task.toml` lists them. For ingredient images that is an optional brief for every image, the style, what an ingredient category needs, and notes for this one ingredient.

The style variants include the exact styles from the old Style Center (isometric, vector, cutout, flatlay, editorial, macro, flat_vector_icon), recovered from a backup on 18.10.2026. To reproduce what it made, add its brief and leave out the newer layers: `--vary brief=style_center --vary category=none --sample style_center`. It used Imagen 4 Ultra; the lab uses the Gemini image model, so the same prompt gives a different image.

A layer variant is either:

- a Jinja template (`.j2`) rendered with the sample's fields, for example `{{ name }}`, or
- a lookup table (`.toml`) with `by` (a sample field, or a list of fields tried in order), a `[values]` table and a `default`. The text can use the same fields. An optional `override` names a sample field whose text replaces the lookup, for the odd ingredient that does not fit its category (a stock cube filed under sauces).

A layer that renders empty is left out. A missing field is an error, so a typo does not silently produce a worse prompt. `model` names a constant in `services/ai_models.py`.

## Commands

```bash
python -m promptlab list                                             # tasks, layers, variants, sample sets
python -m promptlab render ingredient_image --vary style=vector --limit 3   # print prompts, no model call
python -m promptlab run ingredient_image --vary style=default,vector,isometric
python -m promptlab run ingredient_image --vary style=vector --vary category=default,none --sample style_center
python -m promptlab run ingredient_image --vary style=vector --dry-run      # prompts and sheet only
python -m promptlab run ingredient_image --vary style=vector --models GEMINI_IMAGE,gemini-3.1-flash-image,gemini-3-pro-image
python -m promptlab score ~/promptlab-runs/<run> ~/Downloads/scores-<run>.json
```

`--vary` takes every combination of the variants given. Layers you do not vary use `default`. `--models` runs every prompt on each model (a constant from `services/ai_models.py` or a model ID), one column per model. `--sample` picks a set from `samples.toml` and `--limit` takes the first N.

A run needs the model's key in the environment (`GOOGLE_API_KEY` for Gemini; text tasks will use Claude from step 5 of the v2 plan). It costs real money: an image run is samples x combinations images.

## Runs and scores

Each run gets a folder in `PROMPTLAB_DIR` (default `~/promptlab-runs`), outside the repo, because the repo is public and outputs can be large:

- `run.json`: task, model, the variants, git commit (and whether the prompts had uncommitted changes), and for each cell the full prompt, the output and timings.
- `outputs/`: the images.
- `sheet.html`: one row per sample, one column per combination. Give cells 1 to 5, mark the best in each row, then "Export scores" (the file is named after the run) and run `python -m promptlab score`, which refuses a file from another run. Scores are stored in `run.json`, so later runs can be compared and an automated judge can be added on top.
