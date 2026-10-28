---
name: prod-script
description: Run one of the repo's scripts against The Lazy Chef's production database, bucket or AI keys (review_recipes, fill_pantry, category_symbols, a backup). Use when a task needs production data read or changed outside a deploy.
---

# Running a script against production

Production credentials (database password, Anthropic and Gemini keys, bucket writes) are only on Pål's machine with
`gcloud` access to `thelazychefai-prod`. Unless this session runs on that machine with those credentials, **Pål runs
the command and pastes the output back**. Writing to production needs his yes for that run.

## Steps

1. Say what the script will do, whether it writes, and roughly what it costs (`docs/SERVICES_AND_COSTS.md`).
   Prefer a dry run first: most scripts save nothing without `--apply`.
2. If the script was changed in a PR, it must be merged first: the command checks out `origin/main`.
3. Give **one** command he can paste, always starting in his checkout for production scripts, so the code matches
   what is deployed:

   ```bash
   cd <his prod checkout> && git fetch origin main && git checkout --detach origin/main && \
   <environment> <venv>/bin/python -m scripts.<name> <arguments>
   ```

   The environment, depending on what the script needs (from `docs/OPERATIONS.md`):
   - database: `SSL_CERT_FILE=$(<venv>/bin/python -m certifi) DB_PASS="$(gcloud secrets versions access latest --secret=DB_PASS)" DB_BACKEND=cloudsql INSTANCE_CONNECTION_NAME=thelazychefai-prod:europe-north2:lazy-chef-db-eu DB_USER=postgres DB_NAME=lazy-chef-db`
   - Claude: `ANTHROPIC_API_KEY="$(gcloud secrets versions access latest --secret=ANTHROPIC_API_KEY --project=thelazychefai-prod)"`
   - Gemini images to the bucket: `GOOGLE_API_KEY="$(gcloud secrets versions access latest --secret=GOOGLE_API_KEY --project=thelazychefai-prod)" STORAGE_BACKEND=gcs GCS_BUCKET_NAME=thelazychef-assets` (and `gcloud auth application-default login` once on that machine, with the project's Google account)

   Write out the whole command every time; do not ask him to combine pieces.
4. Before a script that drops or rewrites data, ask for a backup first:
   `gcloud sql backups create --instance=lazy-chef-db-eu --project=thelazychefai-prod --description="before …"`.
5. Read the pasted output carefully: check the `HEAD is now at …` line (wrong commit means stale code), the summary
   line, and anything unexpected. Reports that hold recipe content are written to `~/promptlab-runs/…` on his
   machine and copied to the machine Claude runs on; they never go into the repo.
6. Verify the result where you can without credentials: the public JSON (`/api/feed/recipes`,
   `/api/graph/galaxy`, `/api/graph/ingredient-galaxy`) or the pages on <https://thelazychef.app>.
