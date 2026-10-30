# templates and static: pages and the design system

Jinja templates with Tailwind from the CDN (`base.html`), and the app's own design system on top. User-facing pages
share one look: paper surfaces, thin lines, mono labels, serif titles, and line icons.

## The design system

- `static/css/tokens.css`: colours, fonts, spacing, radius (`--color-ink`, `--color-paper`, `--color-accent`,
  `--font-serif`, `--space-4`, …), including dark mode. Use the tokens, not Tailwind colour classes or hex values.
- `static/css/library.css`: the parts the browsing pages share: `lib-head` (page head with eyebrow, serif title and a
  line), `rcard` (the recipe card), `lib-empty`, `lib-go`, Discover's card stack (`dcard`), and the recipe list's bar
  (`lbar`: the title that switches list, search, shortcuts, Filters), its filter drawer (`lib-drawer`, `lib-chip`) and
  the feedback drawer (`fb`); the list's script is `static/js/library.js`. Loaded on every page by `base.html`.
- `static/css/galaxy.css`: both galaxies (`/explore/*`).
- `static/icons/icons.svg`: the line icon sprite (Lucide). In templates `{{ icon('pot') }}`
  (`routes/_shared.icon`); add a symbol to the sprite to add an icon. No emoji in the interface.
- `templates/components/`: shared macros. `cards.html` (`recipe_preview_card`), `site_menu.html` (the menu, drawn
  from `routes/_shared.MENU`), `admin_tools.html` (the floating admin chip on a recipe), `trial_chip.html` (the admin
  chip with the style trial's look on every other page, from `base.html`), `look_switch.html` (the look switch in the
  menu's Admin group).
- The style trial (`static/css/themes.css`, temporary): a look's colours and fonts, and what makes it more than them
  (headings, the main button, lines), for every page and the social slides alike. Kept on the device; visitors who
  have not chosen one see today's look.

## The recipe page

One page, `recipe_v2_make.html`, from `services/recipe_v2/view.page`: the overview, then Prep (`#prep`, the bowls,
`components/prep_board.html`, `static/js/ready.js`) and Cook (`#cook`, the steps, `components/step_list.html`,
`static/js/steps.js`), with the timeline and metro map (`components/whole_dish.html`) and the river delta
(`components/delta.html`, `static/js/delta.js`). Its CSS is split by part: `recipe_v2.css`, `ready.css`, `cook.css`,
`make.css`, `cook_views.css`, `delta.css`, `rail.css`, `overview_layouts.css`. Design decisions:
`docs/RECIPE_VISUALIZATIONS.md` (Norwegian), section 9.

- `steps.js` owns which steps are done (`st.done`) and announces it (`steps:done`); the bowls ask for it
  (`ready:steps`), so the bowls and the step list always agree.
- Servings scale every amount (`static/js/servings.js`).
- When the last step is ticked off, `steps.js` says `steps:finished` and the celebration opens (`#sheet-done`,
  `static/js/done.js`): the dish, how long it took, and for a signed-in cook "I made this" (counted once per meal,
  `/api/interactions/recipe/<id>/cooked`) with stars, comment and photos. Those fields are shared with the recipe
  list's drawer: `components/feedback_fields.html` and `static/js/feedback.js`.
- What the cook saved there comes back the next time (`mine` from `recipe_detail`; `components/overview_layouts.html`):
  the note and stars as a card above the ingredients, the cook's own photo as a small round one in the corner of the
  AI image (which stays the dish's picture, also on the Made list's card), all of it in the sheet at `#more-mine`,
  and a note button among the floating controls while cooking.
- `docs/prototypes/*.html` are the prototypes the views were built from; they are not served by the app.

## Pages made of blocks

The home page and the guides: `page.html` renders a page's blocks, each `blocks/<kind>.html`, styled in
`static/css/content.css` with `static/js/content.js` (Carry on cooking, the frames of interactives). The kinds and how
content is made: `docs/CONTENT.md`.

## Other pages

`landing.html` (Discover), `recipes_list.html`,
`explore_galaxy.html` / `explore_ingredient_galaxy.html`, `recipe_v2_new.html` / `recipe_v2_batch*.html` (admin:
making recipes), `admin/` (management pages, still mostly plain Tailwind), `recipe_print.html`, `social/slide.html` (one
slide of a TikTok or Instagram post, `static/css/social.css`; `docs/SOCIAL.md`).

Check a visual change in the browser on desktop and at phone width (375 px, no sideways scroll) before calling it done.
