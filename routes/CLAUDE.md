# routes: every page and API, as blueprints

- Blueprints split out of the old `app.py` use `FlatBlueprint` (`_flat.py`) so their endpoint names stay un-prefixed:
  `url_for('recipes_list')`, `url_for('recipe_detail', recipe_id=…)`. Newer areas use a normal `Blueprint` and are
  prefixed: `recipe_v2.*` (New recipe, batch, images, the Cloud Tasks endpoints), `queue.*`, `chefs.*` (the public
  chef pages), `content.*` (the home page, guides and Admin -> Pages), `content_api.*` (`/api/content`, drafts from Claude Code), `ingredients_mgmt.*` (admin ingredients), `notes.*` (admin notes on recipes). All are registered in `app.py`.
- Never import from `app` here (circular import). Shared helpers are in `_shared.py`: `get_storage()`,
  `get_recipe_image_url()`, `viewer_is_admin()`, `icon()` (the line icon sprite), and `MENU` / `site_menu()`, the one
  list the top bar and the phone menu are drawn from (add a page to the menu there).

## The pages people see

| Page | Route | Template |
|---|---|---|
| Home | `content.home` `/` | The page `home` made of blocks once it is published, else Discover (`routes/content_routes.py`, `docs/CONTENT.md`) |
| Guides | `content.page` `/guides/<slug>` | `page.html` with `templates/blocks/`; Admin -> Pages imports, previews and publishes them |
| Discover | `recipes_routes.discover` `/discover` | `landing.html`, cards from `/api/feed/recipes` (approved recipes with an image only, one per dish: `recipe_library.feed_ids`) |
| Recipe list, Saved, Made, Cook next | `recipes_list` `/recipes` | `recipes_list.html`; which recipes, one card per dish with its versions, search, time and pages: `services/recipe_library.py`; the filter drawer's live count: `/api/recipes/count` |
| The recipe page | `recipe_detail` `/recipe/<id>` | `recipe_v2_make.html` (overview, `#prep`, `#cook` on one page; `/prep`, `/cook`, `/make` redirect there) |
| Galaxies | `explore_routes` `/explore/galaxy`, `/explore/ingredient-galaxy` | `explore_*.html`, data from `/api/graph/*` |
| Ingredients, chefs | `pantry_routes`, `chefs_routes` | |

Admin: `generate_routes` (`/new-recipe`, the form page), `recipe_v2_routes` (`/new-recipe/v2`, batch `/new-recipe/v2/batch`,
images `/new-recipe/v2/images`, Recalculate), `admin_recipes_routes` (Recipes Management), `admin_ingredients_routes`,
`admin_chefs_routes`, `recipe_notes_routes`, `funnel_routes` (`funnel.*`: the short addresses `/tiktok`, `/ig`,
`/tiktok/<code>` (to the post's recipe when the post log has one, else home) and `?ref=` on any page, kept per session and counted, the admin Funnel page `/admin/funnel` and its
post log `/admin/funnel/posts/…`; `services/funnel.py`). `social_routes` (`social.*`): the slides of TikTok and Instagram posts, public and noindex
(`docs/SOCIAL.md`).

## Rules

- Data-changing endpoints need `@login_required`, admin ones `@admin_required` (`utils/decorators.py`).
  `tests/test_smoke.py` walks every route and fails otherwise; `PUBLIC_WRITE_ENDPOINTS` there is only for real
  exceptions (login, register, a read-only search that uses POST).
- `/internal/tasks/…` (in `recipe_v2_routes.py`) are called by Cloud Tasks, not people: they check the queue's OIDC
  token with `tasks.verified` and return 401 otherwise.
- `/api/content/…` (`content_api_routes.py`) is for Claude Code, not people: `key_required` checks `CONTENT_API_KEY`
  and returns 401 otherwise. It makes drafts only; publishing stays in Admin -> Pages.
- `/api/social/…` (`social_api_routes.py`) is for `scripts/social_batch.py`, with the same key: it suggests a day's
  posts and logs them as drafts in the post log. It posts nothing.
- Drafts and pending ingredients must not leak to visitors (`tests/test_public_visibility.py`):
  check `status == 'approved'` or `viewer_is_admin()`.
- Errors shown to users go through `utils/ai_errors.friendly_ai_error`; never a raw Google or Anthropic message.
