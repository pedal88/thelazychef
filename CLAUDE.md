# The Lazy Chef

AI recipe app for home cooks in Norway: Flask + Jinja templates (Tailwind) on Google Cloud Run, Postgres on Cloud SQL,
files in Cloud Storage, background jobs in Cloud Tasks. Recipes are written and structured by **Claude** (recipe model
v2, `services/recipe_v2/`); **Gemini** draws every image and reads videos and new ingredients. There is only one recipe
model: v1 and its tables are gone. Live at <https://thelazychef.app>.

Folders with more to know have their own `CLAUDE.md`, loaded when you work there: `services/recipe_v2/`, `routes/`,
`templates/`, `scripts/`, `migrations/`, `data/`.

## Where things are

- `app.py`: setup only (config, template filters and globals, login, blueprint registration). It re-exports the
  models because scripts do `from app import app, db, Recipe`.
- `routes/`: every route, as Flask blueprints. `routes/_shared.py` holds shared helpers (`get_storage()`, the site
  menu, `icon()`); route modules must not import from `app`.
- `services/recipe_v2/`: the recipe model: generation, the pantry job, the planner, nutrition, the views.
  `services/content/`: the home page and guides, pages made of blocks (`docs/CONTENT.md`).
  `services/`: the rest (AI models in `ai_models.py`, image generation, ingredient symbols, storage, chefs).
- `ai_engine.py`: pantry matching (names to pantry items) and Gemini ingredient analysis.
- `database/models.py`: SQLAlchemy models; `database/db_connector.py` (`DB_BACKEND=local` → SQLite, `cloudsql` →
  Postgres). `migrations/`: Alembic via Flask-Migrate.
- `templates/`, `static/css`, `static/js`: pages; the design system is `static/css/tokens.css` + `library.css`.
- `data/`: catalogs, prompts and seed data the code reads at run time.
- `scripts/`: maintenance and production scripts, run as modules from the repo root. `promptlab/`: the prompt lab.
- `tests/`: pytest, 300+ tests; `test_smoke.py` checks every route loads and that writes are protected.

## Documentation

- `docs/CONTENT.md`: the home page and guides: block kinds, the content package Claude writes, publishing.
- `docs/SERVICES_AND_COSTS.md`: every external service and API, the environment variables, the background jobs,
  and what costs money. Read it before adding a service, a variable or a paid call, and update it in the same PR.
- `docs/OPERATIONS.md`: deploy pipeline, Trivy, migrations, backups, and running scripts against production.
- `docs/README_TOP_COMMANDS.md`: everyday commands (local database, tests, a throwaway Postgres).
- `docs/RECIPE_MODEL_V2.md` and `docs/RECIPE_VISUALIZATIONS.md` (Norwegian): the design decisions behind the recipe
  model and the recipe views. `docs/PROMPT_LAB.md`: the prompt lab. `docs/runbooks/`: secret rotation.
- `docs/archive/`: superseded documents, kept for history. Do not treat them as true.

## Commands

Python 3.13; copy `.env.example` to `.env` for local runs.

```bash
python app.py                                                          # http://127.0.0.1:8000
GOOGLE_API_KEY=dummy-for-tests python -m pytest tests/                 # tests
flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics     # the lint gate CI uses
flask db migrate -m "message"                                          # new migration after a model change
```

If Python 3.13 isn't available, say so and rely on CI rather than claiming a local run passed.

## Workflow and production

- Work on a branch and open a PR with `gh pr create`. CI runs lint, tests and the migrations on an empty Postgres.
- **Merging to `main` deploys to production automatically**: build → Trivy → migrations against prod (when changed)
  → Cloud Run. Details in `docs/OPERATIONS.md`.
- **Never merge to `main`, push to `main`, or run anything that writes to production (Cloud Run, Cloud SQL, GCS,
  `gcloud` writes, scripts with `--apply`) without Pål's explicit approval for that PR or run.** Opening PRs is fine.
- Migrations run against the production database. Point them out clearly in the PR, and never write one that drops
  or rewrites data without asking; recommend a backup first.
- Production scripts run on Pål's other machine (this one usually has no production credentials): give him the whole
  command, with `cd` and `git fetch`/`checkout` of `origin/main` first, as `docs/OPERATIONS.md` shows.
- Trivy blocks the deploy on fixable HIGH/CRITICAL CVEs: bump the pin in `requirements.txt` to the fixed version and
  check that the other pins still fit.

## Conventions

- Every endpoint that changes data needs `@login_required`, and admin pages `@admin_required`; `tests/test_smoke.py`
  fails otherwise. Cloud Tasks endpoints check the queue's OIDC token instead (`tasks.verified`).
- Model names only in `services/ai_models.py`. Claude calls go through `services/recipe_v2/claude.call` (takes a `call`
  argument so tests can stand in for Claude: tests never call a real model or Google service).
- User-facing pages use the design tokens and the line icons (`icon()`), not Tailwind colours or emoji.
- Secrets come from environment variables (Secret Manager in production). Never commit `.env` or credentials.
- The repo is public: no logs, database dumps, recipe exports or personal notes in it.
- Show users friendly error messages (`utils/ai_errors.friendly_ai_error`); never raw Google or Anthropic errors.
- Code and docs in English; the design documents in `docs/` are in Norwegian.
