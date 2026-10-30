# Content: pages made of blocks

The home page and the guides ("Five pans compared", "The only five knives you need") are pages made of blocks.
Pål does not write them: he asks Claude for a piece, iterates on it and publishes it. This file is what Claude needs
to make one. Decided 29.10.2026; the old Learn articles and collections were removed the day before.

## The idea

- **Formats live in the app, content is data.** A block kind (a comparison matrix, a row of recipes) is designed once
  (in Claude Design, on the Lazy Chef style sheet) and built as a template that works on a phone and a wide screen, in
  every language. A guide is then only data in those kinds: text, rows, scores, images, links.
- **A format wanted twice becomes a block kind.** Until then a one-off can be an `interactive`: a self-contained HTML
  page in a sandboxed frame (the escape hatch). It does not follow the app's look by itself, cannot read the app's data
  and must be made again for each language, so it stays the exception.
- **Content points at the app.** Blocks name recipes, pages and (soon) ingredients and equipment by id, so what they
  show is live (titles, images, nutrition) and checked when saved.

## The model

- `Page` (`database/models.py`): `slug`, `kind` (`home`, `guide`, `landing`).
- `PageText`: one version of a page in one language (`en`, `no`): `title`, `summary`, `hero_image` (an image), `blocks`
  (JSON), `note` (what changed), `published_at`. Every save is a new version; visitors see the newest published one in
  their language, else in English (`services/content/pages.live_text`). Publishing an old version publishes a copy of it.
- `PageEmbed`: the HTML of an interactive, served from `/content/interactive/<id>`.
- `ContentAsset`: an image of a page, by the page's slug and the file name the package uses
  (`services/content/assets.py`).
- Code: `services/content/blocks.py` (the kinds), `services/content/pages.py` (versions, publishing, rendering),
  `routes/content_routes.py` (pages and Admin -> Pages), `templates/page.html` and `templates/blocks/<kind>.html`,
  `static/css/content.css`, `static/js/content.js`.

## Addresses

- `/` is the page `home` once it is published; until then Discover, which is also at `/discover`.
- `/guides/<slug>` is any other page. `?lang=no` asks for Norwegian.
- Admin -> Pages (`/admin/pages`): import a package, preview and publish versions, upload images and interactives.

## The content package

What Claude makes, sent with the content API (below) or pasted in Admin -> Pages -> Import. It becomes a draft
version; nothing is shown until published.

```json
{
  "slug": "frying-pans",
  "kind": "guide",
  "lang": "en",
  "title": "Which frying pan? Five kinds, side by side",
  "summary": "What each one does well, and what you give up.",
  "hero_image": null,
  "note": "First draft",
  "blocks": [
    {"kind": "text", "settings": {"markdown": "No pan is best at everything ..."}},
    {"kind": "recipes", "settings": {"title": "Put a pan to work", "filter": {"heat_source": "pan"}}, "audience": "all"}
  ]
}
```

The pilot guide is the example to start from: `docs/content/frying-pans/` holds its package in English
(`frying-pans.json`) and Norwegian (`frying-pans.no.json`) and its five images. `docs/content/home.json` is the home
page as published. `tests/test_content.py` keeps them valid as the block kinds change. The database is what is shown:
when a page is changed in Admin -> Pages, update its file here in the same round.

- `slug`: lower case words joined by `-`; it is the page's address and identity (a package with the same slug is a
  new version of that page).
- Each block: `kind`, `settings`, and `audience` (`all`, `signed_in`, `signed_out`; default `all`).
- A package that names something missing (a recipe that is not approved, an unknown page, an embed) is refused with
  the reasons. Write in plain, concrete English (or Norwegian with `"lang": "no"`), as the rest of the app.

## The block kinds

| Kind | Settings | Shows |
|---|---|---|
| `text` | `markdown` (headings, lists, tables, links), `style`: `prose` or `intro` (the big opening of a page) | Cleaned Markdown |
| `recipes` | `title`, `text`, `ids` (approved recipe ids, in order) or `filter` (`time` `20`/`30`/`45`/`long`, `protein`, `diet`, `cuisine`, `meal_type`, `difficulty`, `heat_source`, `spice`: the recipe list's choices), `sort` (`new`, `quick`, `active`), `limit` (1-12, default 6), `more` (true: "See all" to the list with that filter) | A row of recipe cards, only approved ones with a picture; nothing when none match. Always one line: on a wide screen as many as fit (3, 4 or 5), on a phone swiped. Ask for 5 or 6 so a wide screen fills its line |
| `continue` | `title` | The dish you are in the middle of on this device, with the next step and a running timer; hidden when none |
| `cook_next` | `title`, `limit` | The person's Cook next queue; nothing for visitors or an empty queue |
| `links` | `title`, `items`: [{`to`: an app part (`discover`, `recipes_list`, `explore_galaxy`, `explore_ingredient_galaxy`, `pantry_management`) or `page:<slug>`, and optionally `title`, `text`, `icon`, `label`}], `style`: `tiles` or `cards` | Tiles; a page's tile takes its title, summary and image, and is left out until the page is published. `cards` puts the image across the top of a card, with `label` ("Guide · 6 knives") over the title: give the page a wide `hero_image` |
| `compare` | `title`, `text`, `layout` (`cards`: a card per item with bars; `table`: one table with dots, cards on a phone), `scale` (default 5), `criteria` [{`key`, `label`}] (1-8), `facts` [{`key`, `label`}] (things said in words), `items` (2-8) [{`name`, `tag`, `image`, `scores` {criterion: 0..scale, every one}, `facts` {key: text}, `pick` ("Pick it if …"), `avoid` ("Skip it if …")}], `note` | Things compared on the same criteria: pans, knives, oils |
| `task_picker` | `title`, `text`, `tasks` (2-8) [{`label`, `hint`, `answer`, `why`, `tip`, `cost` (what you give up), `alt`, `alt_why`}] | "What are you cooking?": the reader picks a job and sees the answer; works without script |
| `interactive` | `embed` (an uploaded interactive's id), `title`, `caption`, `height` (px, until the page reports its own) | A one-off interactive in a sandboxed frame |

## Images

A package names images by file name: `"image": "cast-iron.svg"` in a block, `"hero_image"`, or `![A cast iron
pan](cast-iron.svg)` in Markdown. Upload them in Admin -> Pages -> Images under the page's slug (the page need not exist
yet); they are stored at `content/<slug>/` in the bucket. The same name again replaces the image. A package naming an
image that is not uploaded is refused, so upload the images first. A full address (`https://…`) is used as it is.
Lower case file names, `.svg`, `.png`, `.jpg`, `.webp` or `.gif`, at most 5 MB. Line drawings as SVG suit the cards;
photos as WebP.

### Drawing style

The guides' drawings are flat line drawings, so a new guide's set sits next to the frying pans and the knives
(`docs/content/frying-pans/`, `docs/content/knives/`):

- One dark outline, `#2B2F2C`, with round caps and joins. Flat fills: no gradients, shadows or text in the drawing (the
  card carries the name, so one file serves both languages).
- Steel `#E6E7E3` and `#D3D4D0`, plastic `#A3A6A1`, wood `#EAD7C2`, white for holes. Other colour only when it is what
  tells the items apart, like a pan's coating.
- One frame per guide: every drawing in a set has the same `viewBox` and the same view, so they line up in the cards.
  Draw to scale when size matters: the knives are 1 unit to 1 mm in a 380 × 70 frame.
- The outline comes out at about 2 px in a card: 2.2 in a 220-wide frame, 2.6 in a 380-wide one. Details (rivets, the
  edge bevel) at about half that.
- The view that shows the difference: the pans from a little above to show the inside, the knives side on to show the
  blade.
- An `aria-label` on the `<svg>` that says what sets this one apart.

## Interactives

Upload in Admin -> Pages -> Interactives (a file or pasted HTML, at most 2 MB); the reply gives the block to paste.
The HTML must stand alone: everything inline, or scripts and fonts from public CDNs. It runs in a sandbox with its own
origin: no cookies, no access to the app, and `localStorage` throws (wrap it in try/catch). The frame takes the height
the page reports. A Claude Design canvas is not self-contained (it needs its runtime): ask Claude for a standalone HTML
version of the board.

## The content API

Claude Code sends content to production as drafts with `scripts/content.py`, so nothing is pasted. It calls
`/api/content` (`routes/content_api_routes.py`) with the key in `CONTENT_API_KEY` (Secret Manager in production; on
Pål's MacBook in the Keychain item `thelazychef-content-api`). The API makes drafts only: publishing stays a click by
Pål in Admin -> Pages.

```bash
python -m scripts.content pages                                     # every page, its versions, which is live
python -m scripts.content get frying-pans --lang no -o frying-pans.no.json   # the newest version (--live: what is shown)
python -m scripts.content push docs/content/knives/knives.en.json   # the images next to it, then a draft
python -m scripts.content interactive board.html --title "Knife picker"     # prints the block to use
```

`push` uploads the images the package names that lie in its folder, then the package, and prints the preview and
publish addresses. A refused package prints the reasons. `get` is how Claude starts from what is in the app (Pål may
have edited a version in Admin -> Pages) rather than from the file in `docs/content/`.

| Endpoint | What |
|---|---|
| `GET /api/content/pages` | Every page with its versions per language |
| `GET /api/content/pages/<slug>?lang=&version=&live=1` | One version as a package, its preview address and the page's images |
| `POST /api/content/packages` | A package (JSON) -> a draft version |
| `POST /api/content/pages/<slug>/images` | Images (multipart `images`) for a page |
| `POST /api/content/interactives` | `{"title", "html"}` -> an embed id and its block |

## Working on content with Claude

1. Pål says what to make (topic, formats, images).
2. Claude writes the package in `docs/content/<slug>/` and makes its images (and an interactive if one is needed),
   with ids checked against the app, then sends it with `python -m scripts.content push`.
3. Pål previews the draft on a phone and a wide screen (the address `push` prints) and asks for changes; Claude pushes
   each round as a new version.
4. Pål publishes in Admin -> Pages. A Norwegian version is a package with `"lang": "no"`, made from the English one
   and read before publishing.
5. Commit the files in `docs/content/` in a PR, so the repo keeps what is shown.

Coming next (not built yet): a language switch for visitors and a translation flow, ingredient and equipment links,
and "Read more" on recipes.
