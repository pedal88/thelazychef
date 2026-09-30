# Top Commands Cheat Sheet 🚀

## Run locally 💻
```bash
source venv/bin/activate
python app.py              # http://127.0.0.1:8000  (FLASK_DEBUG=1 in .env for auto-reload)
```

## Create or reset an admin user 👤
```bash
python scripts/seed_admin.py --email you@example.com
```

## Run tests 🧪
```bash
python -m pytest tests/
```

## Ship a change 🚢
```bash
git checkout -b my-change
git add -A && git commit -m "Describe your change"
git push -u origin my-change
gh pr create --fill        # CI runs tests on the PR
gh pr merge --merge        # merging to main deploys to production
gh run watch               # follow the deploy
```

## Database migrations 🗄️
```bash
flask db migrate -m "describe the schema change"   # generates a file in migrations/versions/
# review and commit it; production applies it automatically on deploy
```

## Production logs 📋
```bash
gcloud run services logs read lazy-chef-app --region europe-west1 --project thelazychefai-prod --limit 50
```

## Connect to the production database (careful!) ⚠️
```bash
gcloud auth application-default login
export DB_BACKEND=cloudsql
export INSTANCE_CONNECTION_NAME=thelazychefai-prod:europe-north2:lazy-chef-db-eu
export DB_USER=... DB_PASS=... DB_NAME=...
python -c "from app import app, db; from database.models import *; import code; ctx = app.app_context(); ctx.push(); code.interact(local=locals())"
```

## Debug scripts 🔍
```bash
python -m scripts.debug.verify_setup     # run any script in scripts/debug or scripts/maintenance as a module from the repo root
```
