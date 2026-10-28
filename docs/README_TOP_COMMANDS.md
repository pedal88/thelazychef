# Everyday commands

Run from the repository root with the venv active (`source venv/bin/activate`, Python 3.13).
How a change reaches production and how to work on production data: `docs/OPERATIONS.md`.

## Run the app locally
```bash
python app.py              # http://127.0.0.1:8000 (FLASK_DEBUG=1 for auto-reload); SQLite and static/ by default
```

A local database with the production pantry and five example recipes, to look at the recipe pages:
```bash
python scripts/ingredient_symbols.py export --out pantry.csv     # once, read only, needs production access
python scripts/local_db.py --csv pantry.csv --db ~/code/.thelazychef-local/local.db
DB_BACKEND=local DATABASE_URL=sqlite:///$HOME/code/.thelazychef-local/local.db GOOGLE_API_KEY=x SECRET_KEY=x python app.py
```
It makes an admin `delta@local` with password `pw`. Without `ANTHROPIC_API_KEY` nothing can be generated, and
without `TASKS_QUEUE` generation runs inside the request.

## Create or reset an admin user
```bash
python scripts/seed_admin.py --email you@example.com
```

## Tests and the lint gate CI uses
```bash
GOOGLE_API_KEY=dummy-for-tests python -m pytest tests/
flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
```

## Ship a change
```bash
git checkout -b my-change            # or a worktree
git add -A && git commit -m "Describe the change"
git push -u origin my-change
gh pr create --fill                   # CI runs lint, tests and the migrations on an empty Postgres
gh pr checks <n> --watch
gh pr merge <n> --merge               # only when Pål has said "merge <n>": this deploys to production
gh run list --workflow deploy.yaml --branch main --limit 1
```

## Migrations
```bash
flask db migrate -m "describe the schema change"   # read the file it writes before committing
flask db heads                                      # must be one head
```

Try a chain of migrations on a throwaway local Postgres (they do not run on SQLite):
```bash
export LC_ALL=C
initdb -D /tmp/pg -E UTF8 --locale=C -U postgres && pg_ctl -D /tmp/pg -o "-p 5499 -k ''" -l /tmp/pg.log start
createdb -h 127.0.0.1 -p 5499 -U postgres migtest
DATABASE_URL=postgresql+pg8000://postgres@127.0.0.1:5499/migtest GOOGLE_API_KEY=x FLASK_APP=app.py python -m flask db upgrade
pg_ctl -D /tmp/pg stop
```

## Prompt lab (try prompt changes before they ship)
```bash
python -m promptlab list
python -m promptlab render ingredient_image --vary style=vector --limit 3   # prompts only, no model call
```
More in `docs/PROMPT_LAB.md`.

## Production (Pål runs these; see `docs/OPERATIONS.md` for the environment the scripts need)
```bash
gcloud run services logs read lazy-chef-app --region europe-west1 --project thelazychefai-prod --limit 50
gcloud sql backups create --instance=lazy-chef-db-eu --project=thelazychefai-prod --description="before …"
python -m scripts.review_recipes --ids 337,338        # read-only report
python -m scripts.fill_pantry --ids 1-400 [--apply]   # pantry job and recalculation
```
