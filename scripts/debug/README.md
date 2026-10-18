# Debug & one-off scripts

Ad-hoc checks that used to live in the repo root. They import app modules
(`app`, `database`, `services`), so run them as modules from the repo root:

```bash
python -m scripts.debug.check_db
python -m scripts.maintenance.backfill_nutrition
```

`scripts/maintenance/` holds backfills and seeders. One-off scripts are deleted once they have run; they stay in git history.
