# The Lazy Chef 🍳

> **Turn a craving, a link or a video into a complete, photographed recipe — built from real ingredients.**

The Lazy Chef is an AI recipe platform. Google Gemini writes structured recipes in the voice of a chef persona, every ingredient is matched against a curated ingredient database (with nutrition data), and Google Imagen produces a photo of the finished dish. An admin back office handles quality control, curation and content production (social images, podcasts, videos).

---

## 🌟 Core Features

**For cooks**
*   **Discover & browse** approved recipes, filter by cuisine, diet, difficulty, protein and meal type.
*   **Kitchen mode**: step-by-step cooking view.
*   **Favorites, "I made this" feedback and a personal queue** (requires an account).
*   **Collections** and interactive **recipe/ingredient "galaxy" graphs**.

**For admins**
*   **Recipe generation** from an idea, a web page, pasted text, or a TikTok/Instagram video.
*   **Ingredient database**: nutrition, synonyms, merging, vector embeddings and AI-generated ingredient images.
*   **Missing-ingredient resolution**: when the AI uses an ingredient that isn't in the database, a human maps, substitutes or creates it.
*   **Quality control**: AI evaluator scores recipes; recipes move from `draft` to `approved`.
*   **Photo studio & style center**: generate, remix and approve dish photography.
*   **Media hub**: renders social-media image sets, podcasts and videos from recipes.

## 🚀 How It Works

1.  **Ask**: an admin enters an idea ("something spicy with chicken"), a URL, text or a video link.
2.  **Write**: Gemini generates a structured recipe, constrained by the ingredient database, the chef persona and fixed vocabularies (diets, cuisines, …).
3.  **Validate**: each ingredient is matched to the database; unmatched ones go to a resolution screen.
4.  **Save**: the recipe, steps and gram-weighted ingredients are stored and nutrition is calculated.
5.  **Photograph**: Imagen generates the dish photo from a visual brief.
6.  **Publish**: after review, the recipe is approved and appears on the site.

See [docs/README_TECHNICAL.md](docs/README_TECHNICAL.md) for the architecture.

## ⚡ Quick Start (local)

### Prerequisites
*   **Python 3.13** (the pinned requirements don't install on older versions)
*   A Google Gemini API key ([AI Studio](https://aistudio.google.com/apikey))
*   `ffmpeg` (only needed for video import and the media hub)

### Setup

```bash
git clone https://github.com/pedal88/thelazychef.git
cd thelazychef

python3.13 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env   # then fill in GOOGLE_API_KEY (and optionally SECRET_KEY)

python scripts/seed_admin.py --email you@example.com   # creates kitchen.db (SQLite) + an admin user
python app.py                                          # http://127.0.0.1:8000
```

*   The local database starts empty (no ingredients or recipes).
*   Alembic migrations (`flask db upgrade`) target production Postgres; some use Postgres-only features (pgvector), so locally the tables are created with `db.create_all()` instead.
*   Set `FLASK_DEBUG=1` in `.env` for auto-reload and debug pages.

### Tests

```bash
python -m pytest tests/
```

The smoke tests (`tests/test_smoke.py`) check that every page loads and that write/admin routes reject anonymous and non-admin users. They run in CI on every pull request.

## ☁️ Deployment

Merging to `main` deploys automatically to Google Cloud Run via GitHub Actions. See [docs/README_DEPLOY.md](docs/README_DEPLOY.md).

## 📚 Documentation

| Doc | Contents |
|---|---|
| [README_TECHNICAL.md](docs/README_TECHNICAL.md) | Architecture, components, data model, configuration |
| [README_DEPLOY.md](docs/README_DEPLOY.md) | CI/CD pipeline, secrets, production infrastructure |
| [README_TOP_COMMANDS.md](docs/README_TOP_COMMANDS.md) | Everyday commands |
| [PROMPT_ENGINEERING_GUIDE.md](docs/PROMPT_ENGINEERING_GUIDE.md) | How the prompt templates are assembled |
| [mediahub.md](docs/mediahub.md) | Media hub / social image rendering |
| [INGREDIENT_IMAGES.md](docs/INGREDIENT_IMAGES.md) | Ingredient image pipeline |

`docs/README_CLOUD_DEPLOYMENT.md` holds historical notes from the original manual deployment.

---
*Built with Flask, Tailwind CSS, Google Gemini and Imagen.*
