# The Lazy Chef

An AI recipe app for home cooks in Norway: turn an idea, a link, a video or pasted text into a complete recipe with
its steps planned, its ingredients matched to a curated pantry, its nutrition and its pictures.

Live at <https://thelazychef.app>.

## What it does

**For cooks**
- Discover dishes one at a time, browse and filter the recipe list (cuisine, diet, protein, meal type, time),
  and two galaxies that map the recipes and the pantry.
- One recipe page with the overview, the prep (what to set out, in bowls) and the cooking steps, with timers, a
  timeline and a drawing of the whole dish. Servings scale everything.
- Favorites, "made it", a Cook next queue, and Recipe Mirror (the recipes two people both like).

**For admins**
- New Recipe and Many recipes at once: Claude writes the recipe in the voice of a chef persona (The Classicist,
  The Smart Cook, The Minimalist) with settings such as low carb, kid-friendly or baby food, and structures it as a
  graph of components, ingredient lines and steps (recipe model v2).
- In the background the app links every line to the pantry (adding what is missing), works out nutrition and
  derived facts (time, main protein, clean-up), and draws the dish and its parts. Each image is checked by a vision
  model.
- Recipe and ingredient management, chef personas, notes on recipes.

## How it is built

Flask with Jinja templates and Tailwind, SQLAlchemy and Alembic, on Google Cloud Run with Postgres (Cloud SQL), files
in Cloud Storage, and background jobs in Cloud Tasks. Recipes are written by Claude (Anthropic API); images, video
reading and ingredient analysis use Gemini.

- `CLAUDE.md`: the map of the code and the rules for changing it (start here, also as a person).
- `docs/SERVICES_AND_COSTS.md`: external services, configuration and what costs money.
- `docs/OPERATIONS.md`: deploy, migrations, production data and scripts.
- `docs/README_TOP_COMMANDS.md`: everyday commands.
- `docs/RECIPE_MODEL_V2.md` (Norwegian): the recipe model and why it is so; `docs/RECIPE_VISUALIZATIONS.md`
  (Norwegian): the recipe views and the decisions behind them.

## Run it locally

```bash
python3.13 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # fill in GOOGLE_API_KEY, and ANTHROPIC_API_KEY to generate recipes
python app.py               # http://127.0.0.1:8000
```

Without a database setting it uses SQLite and `static/` for files. `docs/README_TOP_COMMANDS.md` shows how to get a
local database with the pantry and a few recipes.
