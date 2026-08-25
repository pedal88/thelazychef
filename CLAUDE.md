# The Lazy Chef — working context

AI recipe app. Live at **https://thelazychef.app**. Solo project, Python/Flask, deployed to Google Cloud Run.

This file is the onboarding context for development sessions. It replaces the lost `ONBOARDING_NEW_SESSION.md`.
Last verified against live infrastructure: 2026-08-24.

---

## 1. What it does

Generates recipes with an LLM, then generates a photorealistic image of the finished dish, and organises
everything under a taxonomy (cuisine, diet, difficulty, protein, meal type). Around that core sit an
ingredient database with nutrition and vector embeddings, an editorial "Become a Chef" article section,
and a Media Hub that renders recipes into social-media assets.

Recipes enter from four sources (`recipe.source_type`): `manual`, `description` (free text), `web`
(URL scrape), `social` (TikTok).

---

## 2. Infrastructure

Everything lives in Google Cloud project **`thelazychefai-prod`** (project number 454410555150), owned by
the **`thelazychefai@gmail.com`** Google account — *not* `pedal88@gmail.com`, which owns the GitHub repo.
That split is the single most confusing thing about this setup.

| Thing | Value |
|---|---|
| Repo | `github.com/pedal88/thelazychef` (public) |
| Cloud Run | `lazy-chef-app`, region `europe-west1` |
| Cloud SQL | `lazy-chef-db-eu`, Postgres 15, `europe-north2-b`, db-f1-micro |
| Connection name | `thelazychefai-prod:europe-north2:lazy-chef-db-eu` |
| Database | `lazy-chef-db`, user `postgres` |
| Assets bucket | `thelazychef-assets` (note: *not* `thelazychefai-assets`, which also exists and is unused) |
| Artifact Registry | `europe-north2-docker.pkg.dev/thelazychefai-prod/app-repo` |
| CI auth | Workload Identity Federation — no service-account keys |

`pgvector` 0.8.1 is installed on the instance and used by `ingredient.embedding`.

### Orphaned / costing money

- `lazy-chef-db` — a **db-custom-1-3840** Postgres instance in us-central1 that nothing uses. The expensive one.
- `lazy-chef-app` in **europe-north2** — duplicate service on `:latest`, still serving, nothing points at it
- `bym-db-migration` jobs in both regions — leftovers from the predecessor app
- Separate project `gen-lang-client-0770637546` ("ai-chef-2026") still runs the whole **buildyourmeal**
  predecessor: `bym-app` Cloud Run + a `buildyourmeal` Postgres instance + `buildyourmeal-assets`

---

## 3. Architecture

Flask monolith with blueprints bolted on as it grew. ~19,700 lines of Python, ~24,900 lines of Jinja templates.

```
app.py            3721 lines — the monolith: public routes, most /api, some admin
ai_engine.py       899 lines — all Gemini calls for text/recipe generation
routes/           3328 lines — 8 blueprints (newer code lives here)
services/         2701 lines — business logic
media_hub/        2359 lines — social asset generation
database/          614 lines — models + Cloud SQL connector
utils/             200 lines
scripts/          3532 lines — one-off migrations and backfills, not part of the app
tests/              61 lines — ONE test. See §10.
```

The architectural direction was clearly *away* from `app.py` toward `routes/` + `services/`. That
refactor was unfinished when work stopped, and the branch continuing it was lost (§9).

### Blueprints

| Blueprint | Prefix | File |
|---|---|---|
| `prompts` | `/admin/prompts` | `routes/studio_routes.py` |
| `collections` | `/admin/collections` | `routes/admin_collections_routes.py` |
| `ingredients_mgmt` | `/admin/ingredients-management` | `routes/admin_ingredients_routes.py` |
| `queue` | — | `routes/queue_routes.py` |
| `media_hub` | `/admin/media-hub` | `routes/media_hub_routes.py` |
| `tiktok_sidecar` | `/admin/tiktok-sidecar` | `routes/admin_tiktok_routes.py` |
| `admin_concept` | `/admin/concept-visuals` | `routes/admin_concept_routes.py` |
| `admin_style_center` | `/admin/style-center` | `routes/admin_style_center.py` |

Blueprint URLs use **hyphens**; `app.py` routes are a mix of hyphens and underscores.

### Storage abstraction

`services/storage_service.py` defines `StorageProvider` with `LocalStorageProvider` (filesystem,
`./static/`) and `GoogleCloudStorageProvider` (GCS). Selected by `STORAGE_BACKEND` (`local` | `gcs`).

### Database selection

`database/db_connector.py` switches on `DB_BACKEND`:
- `local` → SQLite at `kitchen.db`
- `cloudsql` → Postgres via `cloud-sql-python-connector` + `pg8000`, injected as a SQLAlchemy `creator`

---

## 4. Data model — 26 tables

Verified against production.

**Core**
- `recipe` (30 cols) — title, chef_id, cuisine, difficulty, protein_type, taste_level, base_servings,
  prep_time_mins, cleanup_factor, status, source_type/source_input, image_filename, component_images,
  social_hooks, primary_resource_id, plus 11 denormalised `total_*` nutrition columns
- `instruction` — steps with `phase`, `component`, `step_number`, `global_order_index`, `estimated_minutes`
- `recipe_ingredient` — join with `amount`, `unit`, `gram_weight`, `component`, `prep_style`
- `ingredient` (31 cols) — nutrition per 100g, `aliases`, `food_id`, `main_category`/`sub_category`,
  `image_url`, `has_transparent_image`, `is_staple`, `sub_recipe_id`, **`embedding`** (pgvector)
- `chef` — AI personas: archetype, cooking_style, ingredient_logic, instruction_style, constraints
- `recipe_meal_type`, `recipe_diet` — many-to-many tags

**Editorial**
- `resource` — the "Become a Chef" articles: slug, title, summary, `content_markdown`, tags, status
- `resource_relations` — related-article graph

**Users & social**
- `user` — email, password_hash, is_admin (Flask-Login)
- `user_recipe_interaction` — rating, is_made, is_super_like, comment, user_photos
- `user_queue`, `user_link` (the "Mirror" pairing feature), `recipe_collection`, `collection_item`

**Media Hub**
- `social_media_post` — platform, status, video_url, voiceover_script, template_name
- `tiktok_source` — tiktok_url, dish_name, entity_type, format_type, raw_caption, status
- `sequence_template` — `fragments_sequence` for the video timeline editor
- `concept_visual`, `visual_style_guide`, `style_sandbox_preset`, `style_sandbox_run`

**Quality**
- `recipe_evaluation`, `ingredient_evaluation` — LLM-as-judge scores across several dimensions

**Orphaned**
- `system_config` — has live data, **no code references it anywhere in the repo**. See §9.

---

## 5. AI layer

`ai_engine.py` uses `google-genai` with `GOOGLE_API_KEY`. Images go through Vertex AI.

**Models actually in the code** (the README's claim of "Gemini 1.5 / Imagen 3" is out of date):

| Purpose | Model |
|---|---|
| Recipe generation, web/video extraction | `gemini-flash-latest` |
| Social hooks | `gemini-2.5-flash` |
| Visual prompts, vision | `gemini-2.0-flash` |
| Image generation | `imagen-4.0-generate-001`, `imagen-4.0-fast-generate-001` |

Structured output is enforced with `TypedDict` schemas (`RecipeSchema`, `IngredientAnalysisSchema`,
`NutrientExtractionSchema`, `HookGenerationSchema`).

### Pantry resolution

The interesting bit. Generated ingredient names are matched back to the real `ingredient` table via
`normalize_ingredient_name` → `get_pantry_id` → `_fuzzy_match` (Levenshtein/RapidFuzz), with
`add_synonym` to teach it. `services/recipe_service.py::sanitize_ai_ingredients` is the human-in-the-loop
gate that stops the LLM inventing ingredients.

### Config lives in `data/`, not code

```
data/agents/chefs.json           chef personas
data/agents/photographer.json    image-generation persona
data/constraints/*.json          categories, diets, difficulty, main_protein, meal_types,
                                 pantry_seed, taxonomy_contexts, graph_metadata
data/post_processing/*.json      cleanup_factors, cooking_methods, cuisines, taste, time_intervals
data/prompts/                    versioned prompt library, editable via /admin/prompts
```

Taxonomy: diets `keto, vegan, omnivore, vegetarian, paleo, gluten-free, pescatarian` ·
difficulty `Simplistic, Moderate, Elevated` · protein `Poultry, Red Meat, Seafood, Vegetarian, Vegan`.

---

## 6. Media Hub

Turns a recipe into social assets.

- `snapshotter.py` (1064 lines) — renders Jinja **fragments** (`templates/fragments/`: hero, ing-grid,
  comp, nutr, galaxy, chef, shop, hook-social, hook-cinematic, end) to HTML, screenshots them with
  **Playwright**, paginates content to fit. This is how recipe cards are produced.
- `orchestrator.py` — builds LLM context from a recipe/ingredient/resource and generates articles
- `podcast_engine.py` — script generation + Google TTS audio
- `video_engine.py` — **currently inert.** See §10.

---

## 7. Content in production

| | |
|---|---|
| Recipes | 90 — 56 approved, 34 draft |
| Cuisines | American 28, Mediterranean 10, Other 10, Norwegian 8, Thai 7, French 7, Mexican 6, Italian 6 |
| By chef | The Gourmet 76, Low Carb 5, Meta-Learner 4, Speezy 3, Moribyan 1 |
| Sources | manual 53, description 22, web 13, social 2 |
| Ingredients | 682 — 635 active, 634 with images, **680 with embeddings** |
| Articles | 17 total — only **4 published**, 10 draft, 3 with null status |
| Collections | 1 published ("Meats, chicken and beef") |
| Users | 6 (1 admin) |
| Social posts | 7 tiktok ready, 5 instagram ready, 7 podcasts ready |

Note the article backlog: 13 of 17 written but unpublished.

---

## 8. Deployment

`.github/workflows/deploy.yaml`, triggered on push to `main`.

```
Lint & Test  →  Build & Push image  →  Trivy scan  →  Update migration job
             →  Execute migration (flask db upgrade)  →  Deploy to Cloud Run
```

- Trivy **fails the build** on fixable HIGH/CRITICAL CVEs (`ignore-unfixed: true`). This is a real gate
  and it will fire again as the Debian base and Python deps drift.
- **Scan locally before pushing** — the CI scan covers the whole image, not just `requirements.txt`:
  ```
  docker build --platform linux/amd64 -t lc:scan .
  docker run --rm -v /var/run/docker.sock:/var/run/docker.sock aquasec/trivy:latest \
    image --severity HIGH,CRITICAL --ignore-unfixed lc:scan
  ```
- The Dockerfile runs `apt-get upgrade` and strips `pip`/`setuptools`/`ensurepip` from the final image
  (pip vendors its own vulnerable copies, which no pin can fix).

### Rollback

```
gcloud run services update-traffic lazy-chef-app --project thelazychefai-prod \
  --region europe-west1 --to-revisions <OLD_REVISION>=100
```

### Backups

Daily at 02:00 + point-in-time recovery, 7-day transaction logs, 7 retained backups.
These were **off entirely** until 2026-08-23 — the database had never been backed up.

---

## 9. History and traps

Read this before trusting anything about migrations.

**Migrations were fake for the entire life of the project.** The pipeline ran `flask db stamp head`,
which writes the head revision into `alembic_version` without applying any schema change. Every deploy
declared the DB up to date while changing nothing. It failed silently because `stamp` never needs to
resolve the current revision. Fixed 2026-08-23 → now `flask db upgrade`.

**Production's `alembic_version` pointed at `39d657a9b965`**, a revision present in no commit in the
repository. Generated locally, applied to prod, never committed. This made `db upgrade` permanently
impossible. Reconciled: the one genuinely missing column (`style_sandbox_preset.scope` + its indexes and
unique constraint) was applied by hand and `alembic_version` set to the real head `698f1c8b3e3d`.

**CI was broken from 2026-03-04 to 2026-08-23** — five months, 141 commits that never reached production.
Root cause was a `pip freeze` from a Python 3.13 machine (pinning `audioop-lts`, which requires 3.13)
while CI ran 3.12.

**The old Mac was factory reset** with an unpushed branch on it:
`refactor-constraint-and-taxonomy-categories-combing-routes-and-separateing-concerns`. No Time Machine,
no cloud copy. Lost for good. Its surviving trace is the `system_config` table, whose data is dumped to
`docs/recovered/system_config_prod_dump.json` — an `ai_model_registry` (task→model mapping), a
`global_style_context` image-generation preamble, and pinned sandbox test state. **The data exists in prod
but no code reads it.** If you want the model registry back, that dump is the spec.

**`db.create_all()` never runs in production.** It sits under `if __name__ == '__main__':` in `app.py`,
so it only fires under `python app.py` locally, never under gunicorn.

---

## 10. Known gaps

- **One test.** `tests/test_ai_normalization.py`. A green CI means "it imports and one normalization test
  passes" — nothing about whether the app works.
- **Video generation is disabled.** `moviepy` was removed because it pins `pillow<12.0` while pillow needs
  12.x to clear 13 HIGH CVEs. `video_engine.py` guards the import and sets `MOVIEPY_AVAILABLE = False`.
  Restore when moviepy supports pillow 12.
- **`GOOGLE_CLOUD_LOCATION` is ambiguous** — `.env.example` says `us-central1`, the onboarding notes say
  `europe-west1`. Unresolved.
- **The DB password was exposed in plaintext** (chat + an Antigravity log on the reset Mac) and should be
  rotated, along with the `DB_PASS` GitHub secret.
- **`app.py` is 3721 lines** and was mid-extraction into `routes/` + `services/` when work stopped.

---

## 11. Local development

```bash
cd ~/code/thelazychef
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```

`.env` in the repo root:

```
FLASK_APP=app.py
FLASK_ENV=development
STORAGE_BACKEND=local          # or gcs
GCS_BUCKET_NAME=thelazychef-assets
GOOGLE_API_KEY=<gemini key>
GOOGLE_CLOUD_PROJECT=thelazychefai-prod
GOOGLE_CLOUD_LOCATION=europe-west1
DB_BACKEND=local               # 'cloudsql' to hit production data — be careful
INSTANCE_CONNECTION_NAME=thelazychefai-prod:europe-north2:lazy-chef-db-eu
DB_USER=postgres
DB_NAME=lazy-chef-db
DB_PASS=<password>
```

```bash
gcloud auth login                 # thelazychefai@gmail.com
gcloud config set project thelazychefai-prod
gcloud auth application-default login
python app.py                     # http://127.0.0.1:8000
```

**Do not put this project inside OneDrive.** A January 2026 postmortem
(`DEPLOYMENT_TROUBLESHOOTING_POSTMORTEM.md`) records 2+ hours lost to `gcloud` deadlocking against
OneDrive's file sync. It lives at `~/code/thelazychef` for that reason.

### Git

The repo is owned by the `pedal88` GitHub account while the active `gh` account may be a different one.
To push without switching accounts globally:

```bash
GH_TOKEN=$(gh auth token -u pedal88) gh <command>
git push "https://x-access-token:$(gh auth token -u pedal88)@github.com/pedal88/thelazychef.git" HEAD:<branch>
```

### Reading production safely

To inspect prod without handling the password, override the migration job's args — it already holds the
credentials. Restore it to `flask` / `db,upgrade` afterwards.

```bash
gcloud run jobs update lazy-chef-db-migration --project thelazychefai-prod --region europe-west1 \
  --command python --args="^|^-c|<python>"
gcloud run jobs execute lazy-chef-db-migration --project thelazychefai-prod --region europe-west1 --wait
```
