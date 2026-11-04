# routes: every page and API, as blueprints

- Blueprints split out of the old `app.py` use `FlatBlueprint` (`_flat.py`) so their endpoint names stay un-prefixed:
  `url_for('recipes_list')`, `url_for('recipe_detail', recipe_id=…)`. Newer areas use a normal `Blueprint` and are
  prefixed: `recipe_v2.*` (New recipe, batch, images, the Cloud Tasks endpoints), `queue.*`, `chefs.*` (the public
  chef pages), `content.*` (the home page, guides and Admin -> Pages), `content_api.*` (`/api/content`, drafts from Claude Code), `review_api.*` (`/api/review`, reading for Claude Code), `ingredients_mgmt.*` (admin ingredients), `notes.*` (admin notes on recipes). All are registered in `app.py`.
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
| Ingredients | `pantry_management` `/ingredients`, the sheet `/ingredients/<id>/card` | `pantry_management.html`, `templates/components/ingredient_sheet.html`: what is in recipes first, search, shortcuts and Staples (`services/ingredient_library.py`); the admin's tools are on `/admin/ingredients-management` |
| Chefs | `chefs_routes` | |
| Not found, error | `error_routes` (`app_errorhandler`) | `templates/errors/404.html`, `templates/errors/500.html` (on its own, no database); `/api/`, `/internal/` and `/static/` keep the plain answer. A short address typed differently (`/TikTok/4`, `/tiktok/4/`, `/instagram/4`) is sent to the real one |

Admin: `generate_routes` (`/new-recipe`, the form page), `recipe_v2_routes` (`/new-recipe/v2`, batch `/new-recipe/v2/batch`,
images `/new-recipe/v2/images`, Recalculate), `admin_recipes_routes` (Recipes Management), `admin_ingredients_routes`,
`admin_chefs_routes`, `recipe_notes_routes`, `funnel_routes` (`funnel.*`: the short addresses `/tiktok`, `/ig`,
`/tiktok/<code>` (to the post's recipe when the post log has one, to the post's page `/post/<platform>/<code>` when it showed several, else home) and `?ref=` on any page, kept per session and counted, the admin Funnel page `/admin/funnel` and its
post log `/admin/funnel/posts/…`, the TikTok posts for the phone `/admin/funnel/tiktok`, the weekly report `/admin/funnel/report`; `services/funnel.py`). `video_inbox_routes` (`video_inbox.*`: `/admin/inbox`, cooking videos saved from the phone; its `/admin/inbox/add?url=` is what the iPhone shortcut opens, a page that sends itself; `/admin/inbox/check` reads many links out of text or a file and saves nothing). `pantry_questions_routes` (`pantry_questions.*`: `/admin/pantry-questions`, ingredients the pantry lacks, for Pål to add or swap; `services/recipe_v2/pantry_fill.py`). `social_routes` (`social.*`): the slides of TikTok and Instagram posts, public and noindex
(`docs/SOCIAL.md`).

## Rules

- CSRF: `utils/cross_site.py` runs before every request and refuses POST, PUT, PATCH and DELETE from another site
  (`Sec-Fetch-Site`, else `Origin`), so forms and `fetch` need no token. It only protects writes: never change data on
  a GET, because `SameSite=Lax` cookies follow a link from another site.
- Data-changing endpoints need `@login_required`, admin ones `@admin_required` (`utils/decorators.py`).
  `tests/test_smoke.py` walks every route and fails otherwise; `PUBLIC_WRITE_ENDPOINTS` there is only for real
  exceptions (login, register, a read-only search that uses POST).
- `/internal/tasks/…` (in `recipe_v2_routes.py`) are called by Cloud Tasks, not people: they check the queue's OIDC
  token with `tasks.verified` and return 401 otherwise.
- `/api/content/…` (`content_api_routes.py`) is for Claude Code, not people: `key_required` checks `CONTENT_API_KEY`
  and returns 401 otherwise. It makes drafts only; publishing stays in Admin -> Pages.
- `/api/social/…` (`social_api_routes.py`) is for `scripts/social_batch.py`, with the same key: it logs a day's posts
  as drafts in the post log, series with what the site chose for them, and takes their Instagram slides and caption
  for the Instagram queue. It posts nothing: Pål approves in the queue (`/admin/funnel/queue`), and
  `/internal/tasks/social-publish/<id>` publishes at the time.
- `/api/review/…` (`review_api_routes.py`) is for Claude Code too, with a key of its own (`REVIEW_API_KEY`), checked in the
  blueprint's `before_request`, so a new route cannot forget it. GET only, in a read-only transaction. Recipes and the
  pantry only, each answer built field by field: never add anything about a person, and `tests/test_review_api.py` fails
  if a route is added without its own check there. `scripts/` is not in the production image, so nothing here imports it.
- Seeing the site as someone else (`view_as.switch`, `/view-as`, in the admin chip; `services/view_as.py`): the choice is in the
  signed session and read in `app.load_user`, the one place people are signed in, so `current_user` is an anonymous visitor
  or `SignedInView`, the account without admin. It only goes down: `account()` checks the real account. Anything new that
  saves on a GET goes in `WRITES_ON_GET`, a read-only POST in `ALLOWED_WRITES`, and anything new that counts a visitor must
  also ask `view_as.role()`, as `funnel_routes._a_real_visitor` does.
- Drafts and pending ingredients must not leak to visitors (`tests/test_public_visibility.py`):
  check `status == 'approved'` or `viewer_is_admin()`.
- The language (`services/language.py`): `language.current()` is `en` or `nb`, chosen once per request, and `language.content_code()` is what the content tables call it. A new page that stays English goes in `ENGLISH_ONLY`; a new slide route must be under `/social`. Stored and catalog words stay English in the data and in filters: `services/labels.label` is for showing them.
- Errors shown to users go through `utils/ai_errors.friendly_ai_error`; never a raw Google or Anthropic message.
- Answers are gzipped in `utils/compress.py`, the first `after_request` in `app.py` so that it runs last. A new one that changes the body must be registered after it.
