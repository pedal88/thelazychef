# The Lazy Chef

AI recipe app: Flask + Jinja templates (Tailwind), Gemini for recipe logic, Imagen/Vertex for dish images.
Production runs on Google Cloud Run with Postgres on Cloud SQL and assets in GCS.

## Layout

- `app.py` – app setup plus many routes (large; new routes go in blueprints under `routes/`, and old ones are moved there gradually)
- `routes/` – Flask blueprints (most admin areas live here)
- `services/` – business logic and AI calls (recipes, images, nutrition, storage, …)
- `ai_engine.py` – Gemini prompt/response handling
- `database/` – SQLAlchemy models and `db_connector.py` (`DB_BACKEND=local` → SQLite, `cloudsql` → Postgres)
- `migrations/` – Alembic migrations via Flask-Migrate
- `templates/` – Jinja; `base.html` holds the shared layout and footer
- `utils/decorators.py` – `admin_required`
- `scripts/` – one-off maintenance and debug scripts, run as modules from the repo root
- `tests/` – pytest; `test_smoke.py` checks every route loads and is protected
- `docs/` – `README_TOP_COMMANDS.md` (everyday commands), `README_TECHNICAL.md`, `README_DEPLOY.md`

## Commands

Requires Python 3.13 (see `requirements.txt`). Copy `.env.example` to `.env` for local runs.

```bash
python app.py                      # http://127.0.0.1:8000
python -m pytest tests/            # tests
flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics   # the lint gate CI uses
flask db migrate -m "message"      # new migration after a model change
```

If Python 3.13 isn't available on the machine, say so and rely on CI (it runs lint and tests on every PR) instead of claiming a local test passed.

## Workflow and production

- Work on a branch and open a PR with `gh pr create`. CI runs lint and tests on the PR.
- **Merging to `main` deploys to production automatically** (`.github/workflows/deploy.yaml`): build image → Trivy scan → run DB migrations against prod → deploy to Cloud Run.
- **Never merge to `main`, push to `main`, or run anything against production (Cloud Run, Cloud SQL, GCS, `gcloud` writes) without explicit approval from Pål.** Opening PRs is fine.
- Migrations run against the production database on every deploy. Point out any migration in a PR clearly, and never write one that drops or rewrites data without asking.
- Trivy blocks the deploy on fixable HIGH/CRITICAL CVEs. The fix is usually bumping the pinned version in `requirements.txt` to the one Trivy reports as fixed.

## Conventions

- Every new endpoint that changes data needs `@login_required`, and admin pages need `@admin_required`. `tests/test_smoke.py` fails otherwise; only add to `PUBLIC_WRITE_ENDPOINTS` there if a route really must be public.
- Secrets (API keys, `SECRET_KEY`, DB credentials) come from environment variables and GitHub secrets. Never commit `.env` or credentials files.
- The repo is public. Don't commit logs, database dumps, archives or personal notes.
- Show users friendly error messages; don't pass raw Google/Gemini errors through to the UI.
