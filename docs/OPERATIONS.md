# Operations: deploy, migrations, production data and scripts

How changes reach production, and how to work on production data safely. Last checked: 28.10.2026.
Services, environment variables and costs are in `docs/SERVICES_AND_COSTS.md`; everyday commands in
`docs/README_TOP_COMMANDS.md`.

## The rules

- Work on a branch and open a PR. Opening PRs is always fine.
- **Merging to `main` deploys to production.** Merge only when Pål has said so for that PR ("merge 201"); approval of
  one PR does not cover the next. The same goes for anything that writes to production: Cloud SQL, GCS, Cloud Run,
  `gcloud` writes, and scripts run with `--apply`.
- A migration runs against the production database on deploy. Say so clearly in the PR, and ask before writing one
  that drops or rewrites data. Take a backup first (below).
- The repository is public: no secrets, logs, dumps, recipe exports or personal notes. Script output that holds
  recipe content goes outside the repo (`~/promptlab-runs/…`).

## From PR to production (`.github/workflows/deploy.yaml`)

On every PR (and on `main`):

1. **Lint & Test**: the flake8 gate (`--select=E9,F63,F7,F82`) and `pytest tests/` on Python 3.13.
2. **Migrations on empty Postgres**: a pgvector container, `flask db upgrade` from scratch, then `flask db check`
   (the models and the migrations must agree).

On `main` only, after both pass:

3. **Build & Scan**: the Docker image (Buildx with cache), then **Trivy**. A fixable HIGH or CRITICAL CVE stops the
   deploy. The fix is to bump the pinned version in `requirements.txt` to the one Trivy names as fixed; check that its
   own requirements still fit the other pins (rembg 2.0.82–2.0.85 wanted pillow below 13, 2.0.86 did not) with
   `pip install --dry-run -r requirements.txt`, and run the tests in a clean venv.
4. **Deploy to Prod** (one at a time: concurrency group `production-deploy`): if `migrations/` changed since the last
   deploy, the Cloud Run job `lazy-chef-db-migration` runs `flask db upgrade` against Cloud SQL first; then
   `gcloud run deploy` with the secrets from Secret Manager and the environment variables.

`image-check.yaml` builds the image and runs Trivy on PRs that touch the Dockerfile or `requirements.txt`, so a CVE
is found before the merge.

Follow a deploy with `gh run list --workflow deploy.yaml --branch main --limit 1`, then check
<https://thelazychef.app>. A failed Build & Scan leaves production on the previous version; nothing is half-deployed.

## Migrations

- `flask db migrate -m "…"` after a model change; read the generated file, it is often wrong about types and
  server defaults. Keep `down_revision` linear (`flask db heads` shows one head).
- Data migrations (moving ingredients, cleaning names): name each row by what it is expected to be and leave rows
  that differ alone, so a database that has drifted, or a fresh one, is safe. Write a downgrade that moves back.
  `migrations/versions/b3d7e9f1a2c4_taxonomy_cleanup.py` is the pattern; `tests/test_taxonomy_migration.py` shows
  how to run a migration's `upgrade()` and `downgrade()` in a test.
- The migrations use Postgres features (pgvector), so `flask db upgrade` does not run on SQLite. To try a chain
  locally, start a throwaway Postgres (see `docs/README_TOP_COMMANDS.md`) and use
  `DATABASE_URL=postgresql+pg8000://…`.
- Before a migration that drops or rewrites data: a manual backup, run by Pål:
  `gcloud sql backups create --instance=lazy-chef-db-eu --project=thelazychefai-prod --description="before …"`.

## Production data from scripts

Scripts that read or write production run on **Pål's other machine**, which has `gcloud` access to the project; the
machine Claude usually runs on has no database password or API keys. Give Pål the whole command, including `cd`
and `git fetch origin main && git checkout --detach origin/main` in the checkout he uses for this, so the script
matches the deployed code. He pastes the output back.

The environment the scripts need (the `gcloud` account must be the project's, and Python packages that write to
GCS need `gcloud auth application-default login` once):

```bash
# database (every prod script)
SSL_CERT_FILE=$(…/venv/bin/python -m certifi) DB_PASS="$(gcloud secrets versions access latest --secret=DB_PASS)" \
DB_BACKEND=cloudsql INSTANCE_CONNECTION_NAME=thelazychefai-prod:europe-north2:lazy-chef-db-eu DB_USER=postgres DB_NAME=lazy-chef-db
# + Claude
ANTHROPIC_API_KEY="$(gcloud secrets versions access latest --secret=ANTHROPIC_API_KEY --project=thelazychefai-prod)"
# + Gemini images saved to the bucket
GOOGLE_API_KEY="$(gcloud secrets versions access latest --secret=GOOGLE_API_KEY --project=thelazychefai-prod)" \
STORAGE_BACKEND=gcs GCS_BUCKET_NAME=thelazychef-assets
```

The scripts that matter now (see `scripts/CLAUDE.md` for all of them):

| Script | Writes? | What |
|---|---|---|
| `scripts.review_recipes --ids … / --search …` | no (read-only transaction) | A report per recipe: lines and pantry match, steps, time, carbs, the chef's rules and all notes. To `~/promptlab-runs/recipe-review/report.md` |
| `scripts.fill_pantry --ids 1-400` | with `--apply` | Pantry job for recipes made before it existed, and a recalculation of every v2 recipe in the range (needed after changes to nutrition, derive or the chefs' rules). Dry run by default |
| `scripts.fill_pantry --symbols` / `--looks "name=…"` | yes (bucket + DB) | Symbols of pantry items added by the pantry job; set how one item looks and redraw it |
| `scripts.category_symbols [--kind cuisine] [--only …] [--all]` | yes | The galaxies' category and cuisine symbols |
| `scripts.retire_v1`, `scripts.convert_states` | done | One-off steps of the v2 move, kept for the record |

## Checking production

- The site: <https://thelazychef.app>. Public JSON that shows the state without logging in:
  `/api/feed/recipes` (what Discover shows), `/api/graph/galaxy`, `/api/graph/ingredient-galaxy`.
- Cloud Run logs: `gcloud run services logs read lazy-chef-app --region europe-west1 --project thelazychefai-prod`
  (needs the same `gcloud` access, so Pål runs it).
