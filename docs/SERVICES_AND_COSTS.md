# External services, configuration and costs

Every service the app talks to, what it is used for, the configuration it needs, and what costs money.
Last checked against the code: 28.10.2026. When you add a service, an environment variable or a paid call,
update this file in the same PR (`tests/test_docs.py` checks that `.env.example` lists every variable the app reads).

## AI models

All model names live in `services/ai_models.py`; change a model there, never at the call site.

| What | Model | Where | Used for |
|---|---|---|---|
| Claude (Anthropic API) | `claude-opus-5-5`, effort `low` (`RECIPE_V2_MODEL`, `RECIPE_V2_EFFORT`) | `services/recipe_v2/claude.py` (`call`, streamed, structured output, cached system prompt) | Recipe text (round 1) and structure (round 2) in `generate.py`, chef versions, the dish's appearance (`appearance.py`), the vision check of every generated image (`images.py`), the pantry job (`pantry_fill.py`), and scripts (`ingredient_nutrition`, `pantry_review`, `foundation_sample`, `chef_trial`, `generate_v2`) |
| Gemini text (Google GenAI, API key) | `GEMINI_TEXT`, `GEMINI_TEXT_FAST` | `ai_engine.py`, `services/ingredient_evaluation_service.py`, `services/recipe_v2/sources.py` | Ingredient analysis on the New ingredient page, ingredient QA scores, and watching a recipe video (file upload) |
| Gemini image | `GEMINI_IMAGE` (`gemini-2.5-flash-image`) | `services/image_generation.py` (every image path goes through it) | Dish and component images (`services/recipe_v2/images.py`), ingredient symbols (`ingredient_symbols.py`), equipment symbols, category and cuisine symbols for the galaxies |
| Vertex AI | text embeddings | `scripts/generate_ingredient_embeddings.py` only | pgvector embeddings on `ingredient.embedding`; not part of the running app |

Imagen and Edamam are no longer used (Imagen 4 was retired from the Gemini API; nutrition now comes from Claude with
USDA values, `scripts/ingredient_nutrition.py`).

## Google Cloud (project `thelazychefai-prod`)

| Service | What | Code |
|---|---|---|
| Cloud Run | The app (`lazy-chef-app`, europe-west1) and the migration job (`lazy-chef-db-migration`) | `.github/workflows/deploy.yaml` |
| Cloud SQL | Postgres `lazy-chef-db-eu` (europe-north2), with pgvector | `database/db_connector.py` (Cloud SQL Python Connector + pg8000) |
| Cloud Storage | Bucket `thelazychef-assets`: dish images (`recipes/`), ingredient symbols (`pantry/symbols/`), category and cuisine symbols (`pantry/categories/`, `pantry/cuisines/`), the Instagram queue's slides as public JPEGs (`social/`) | `services/storage_service.py` (`get_storage()` in routes) |
| Cloud Tasks | Queue `recipe-generation` (europe-west1): recipe generation, the pantry job and the image job | `services/recipe_v2/tasks.py` (REST calls with google.auth, no client library) |
| Secret Manager | `GOOGLE_API_KEY`, `ANTHROPIC_API_KEY`, `DB_PASS`, `SECRET_KEY`, `CONTENT_API_KEY`, `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET`, `INSTAGRAM_ACCESS_TOKEN`, mounted into Cloud Run by the deploy | `deploy.yaml` (`--update-secrets`); rotation: `docs/runbooks/ROTATE_SECRETS.md` |
| Cloud Scheduler | Jobs (europe-west1) with an OIDC token from `TASKS_SERVICE_ACCOUNT`: `social-stats`, daily at 06:00 Oslo, `POST /internal/tasks/social-stats`; `social-report`, Sundays at 07:00 Oslo, `POST /internal/tasks/social-report` (Claude, `SOCIAL_REPORT_MODEL` = Sonnet, one short call, a few cents a week) | `routes/funnel_routes.py`, `services/social_report.py`; the commands: `docs/runbooks/ROTATE_SECRETS.md`, "Instagram" |
| Artifact Registry | Docker images (europe-north2) | `deploy.yaml` |
| Google sign-in (OAuth client, Google Auth Platform) | Continue with Google on log in and sign up: the OAuth client "The Lazy Chef web" (Web application), redirect URI `https://thelazychef.app/login/google/done`, scopes `openid` and `email` only, so the app needs no verification by Google. Free | `services/google_signin.py` (token exchange with `requests`, the ID token checked with google-auth) |
| Workload Identity Federation | GitHub Actions authenticates to Google without a key | `deploy.yaml`, `scripts/setup_wif.sh` |

### The background jobs (Cloud Tasks)

New Recipe and Many recipes at once save a placeholder recipe (status `generating`) and queue a task. Cloud Tasks
calls the app back with an OIDC token from the `TASKS_SERVICE_ACCOUNT`, checked by `tasks.verified`:

1. `/internal/tasks/recipe-v2/<id>`: both Claude rounds, save, derive, nutrition (`tasks.run` → `generate.create_recipe`).
2. `/internal/tasks/recipe-v2-pantry/<id>`: only when some lines matched nothing in the pantry. Claude decides alias / new
   item / skip per line, then the recipe is recalculated and new items get their symbol (`tasks.run_pantry` → `pantry_fill`).
3. `/internal/tasks/recipe-v2-images/<id>`: the dish and component images with their vision check (`tasks.run_images`).
   Queued after 2 (or straight after 1), unless the form said "Skip the images".

The same queue also holds the Instagram queue's posts: `/internal/tasks/social-publish/<id>`, one task per approved post,
waiting until its time (`scheduleTime`; `services/social_publish.py`). It is not retried on a failure: the post goes back
to draft with the reason.

Each job retries up to `MAX_ATTEMPTS = 3` (600 s deadline); the last failure is noted on the recipe instead of raising.
Without `TASKS_QUEUE` (local runs) the generation runs inside the request and the pantry and image jobs do not run.

## Other external resources

- Web pages and video: `requests` + BeautifulSoup for recipe links, `yt_dlp` (and ffmpeg in the image) for videos
  (`services/recipe_v2/sources.py`, `services/social_media_service.py`).
- Instagram (Meta Graph API, `graph.facebook.com/v26.0`): each post's numbers into the post log, once a day
  (`services/social_stats.py`, `docs/SOCIAL.md`), and publishing the approved posts of the Instagram queue
  (`services/social_publish.py`). The Meta app "The Lazy Chef stats", in development mode with the business
  portfolio "The Lazy Chef" and the account thelazychef.ai as Instagram Tester, no App Review. Its Unified login configuration
  gives a system-user token that never expires. The code uses its `instagram_basic`, `instagram_manage_insights` and
  `instagram_content_publish`. A new Graph API version every few months; each lasts about two years. The accounts and
  access on both platforms, TikTok's included: `docs/SOCIAL_ACCOUNTS.md`.
- Front-end from CDNs: Tailwind (`cdn.tailwindcss.com`, `templates/base.html`), D3 v7 (the galaxies),
  ECharts (jsdelivr, ingredients admin), Google Fonts.
- Stock photos from images.unsplash.com only as backgrounds on two admin pages (`index.html`, `new_ingredient.html`).
  Never as a stand-in for a dish: Discover shows only recipes with their own image.

## Environment variables

Read by the app (all listed in `.env.example`):

| Variable | Needed | What |
|---|---|---|
| `SECRET_KEY` | on Cloud Run (`K_SERVICE` set) | Session signing; a random key is used locally if missing |
| `FLASK_DEBUG` | no | Debug mode for `python app.py` |
| `GOOGLE_API_KEY` | yes (app.py checks it) | Gemini. Scripts that do not call Gemini set a dummy value |
| `ANTHROPIC_API_KEY` | to generate recipes | Claude |
| `INSTAGRAM_ACCESS_TOKEN`, `INSTAGRAM_USER_ID` | to fetch Instagram's numbers | The Meta app's system-user token (Secret Manager) and the account's id (`deploy.yaml`); without them nothing is fetched and the numbers are typed in by hand |
| `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET` | for Continue with Google | The OAuth client (above); without both there is no Google button and `/login/google` is 404 |
| `CONTENT_API_KEY` | for the content and social APIs | The key Claude Code sends content drafts with (`/api/content`, `docs/CONTENT.md`) and `scripts/social_batch.py` logs a day's posts with (`/api/social`, `docs/SOCIAL.md`); without it both answer 401 |
| `DB_BACKEND` | no | `local` (SQLite, default) or `cloudsql` |
| `DATABASE_URL` | no | Overrides the database URL (tests use `sqlite://`; a local Postgres with `postgresql+pg8000://…`) |
| `INSTANCE_CONNECTION_NAME`, `DB_USER`, `DB_PASS`, `DB_NAME` | with `cloudsql` | Cloud SQL connection |
| `STORAGE_BACKEND`, `GCS_BUCKET_NAME` | no | `local` (static/, default) or `gcs` with the bucket |
| `TASKS_QUEUE`, `TASKS_LOCATION`, `TASKS_SERVICE_ACCOUNT`, `APP_BASE_URL` | on Cloud Run | The Cloud Tasks queue; without `TASKS_QUEUE` jobs run in the request |
| `GOOGLE_CLOUD_PROJECT` | no | Defaults to `thelazychefai-prod` (Cloud Tasks) |

Scripts only: `GOOGLE_APPLICATION_CREDENTIALS`, `GOOGLE_CLOUD_LOCATION` (embeddings, GCS CORS setup),
`PROMPTLAB_DIR`, `PROMPTLAB_NO_OPEN`, `PILOT0B_DIR`, `PANTRY_FILE`. `EDAMAM_*` belong to a dead script.

## Costs

Every Claude and Gemini call costs money; nothing else in the code does per request (the Instagram Graph API is free, and
one Cloud Scheduler job is within the free tier of three). Rough numbers, from the
constants in the code and measured runs:

| What | Cost | Where it is set or measured |
|---|---|---|
| Claude prices | Opus $4 / $20, Sonnet $2 / $10 per million tokens in / out; cache write ×1.25, cache read ×0.1 | `services/recipe_v2/claude.py` `PRICES`, `usage_of` |
| One recipe, text and structure | $0.10–0.40 (about $0.15 typical) | `services/recipe_v2/batch.py` `COST_EACH` |
| One recipe's images (dish + parts, with checks) | $0.15–0.45 | `routes/recipe_v2_routes.py` `IMAGES_COST`; one image ≈ $0.039 (`images.py` `IMAGE_COST`) |
| Pantry job | about $0.01–0.05 per recipe with unlinked lines | `pantry_fill.fill` returns `cost_usd` |
| A symbol (ingredient, category, cuisine) | about $0.04 | `scripts/category_symbols.py`, `fill_pantry --symbols` |
| Batch page estimate | text + images per line, shown before "Make" | `routes/recipe_v2_routes.py` `batch_new` |

`generate.create_recipe` and `pantry_fill.fill` report `cost_usd`; the batch page and scripts print estimates.
Fixed monthly costs are Cloud Run, Cloud SQL (small instance), Cloud Storage and Artifact Registry; there is no
budget alert in the code (see `docs/RECIPE_MODEL_V2.md` section 12 for the budget reasoning).
