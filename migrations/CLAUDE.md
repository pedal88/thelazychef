# migrations: Alembic via Flask-Migrate

Every migration runs against the **production database** when it is merged (the deploy runs the Cloud Run job
`lazy-chef-db-migration` when this folder changed). Read `docs/OPERATIONS.md` ("Migrations") before writing one.

- `flask db migrate -m "…"` after a model change, then read the file: it is often wrong about types, server defaults
  and enum changes. Keep one head (`flask db heads`); set `down_revision` to the current head.
- CI runs the whole chain on an empty Postgres with pgvector and then `flask db check` (models and migrations must
  agree). The migrations do not run on SQLite; try them on a throwaway local Postgres
  (`docs/README_TOP_COMMANDS.md`).
- **Data migrations**: name each row by what it is expected to be (name and current category, not only an id) and
  leave rows that differ alone, so a drifted or fresh database is safe; write a downgrade that moves back. Don't
  import app code (it changes later and breaks old migrations); use `sa.text`. Pattern:
  `versions/b3d7e9f1a2c4_taxonomy_cleanup.py`, tested by `tests/test_taxonomy_migration.py`.
- **Dropping or rewriting data needs Pål's yes, and a backup first** (the command is in `docs/OPERATIONS.md`). Say
  so at the top of the PR.
- Recent history: the v1 recipe tables were dropped in `e8b4d2f6a1c3`, the taxonomy cleanup is `b3d7e9f1a2c4`, and
  `recipe_line.cut` was dropped in `c5e8a1d3f9b2`.
