# Posts for TikTok and Instagram

Carousel posts drawn from the recipes themselves, for the first users from TikTok and Instagram (goal: 50 sign-ups
from outside family and friends before 31.01.2027, 10 of them have made a recipe). No video and no faces: what sets the
account apart is that a recipe here is data, so its metro map, its ingredients and the pantry can be drawn.

## The formats

Each is a test for the first weeks; the Funnel page (`/admin/funnel`) says which brings people.

| Format | Slides | Built from |
|---|---|---|
| `map`: Dinner as a subway map | the dish, the metro map, what you need, the steps in one list, the address | the recipe page's view (`services/recipe_v2/view.page`) |
| `grid`: Everything in a dish | every ingredient as a symbol, then with amounts, then the dish, the address | the shopping list |
| `pantry`: The foundation pantry | the foundation by kitchen group, how far it goes, the address | the pantry tiers `staple` and `foundation` |
| `week`: One shop, five dinners | the five dishes and how many things to buy, the shopping list (×3 = in three dinners), the week, each day, the address | five recipes picked across the site (below) |

The week (`services/social_week.py`, `/social/week`) is the five approved dinners with a dish image and at most 40
minutes of work that together need the fewest things to buy, staples left out. Fewest alone gives five near-copies of
one stir-fry, so no two may share more than 40% of their ingredients, no protein (`recipe.protein_type`) may come more
than twice, and there must be at least three. It is found greedily from each recipe and improved by swaps, so the same
recipes always give the same week. `?ids=` (`--ids`) sets the five, in that order, instead. On the shopping list one
pantry item is one thing to buy, under its shortest name, whatever each recipe calls it ("boneless, skinless chicken
thighs" and "chicken thighs").

The pantry post's numbers are the share of ingredient lines the staples, the 60 and the 100 most used cover in 272
dishes home cooks make (`scripts/foundation_sample.py`, 22.10.2026). They are about ingredients, not dinners: the
slides say "covers 84% of what goes into dinner", never "cooks 84% of dinners".

Two sizes: `ig` (1080 × 1350, Instagram's tallest carousel) and `tt` (1080 × 1920, TikTok's photo mode, with wider
margins top and bottom where TikTok lays its buttons). The last slide gives the short address for the platform,
`thelazychef.app/ig` or `/tiktok`, with the post's code (`/tiktok/3`), so the Funnel page counts each post's visits.

## Making a post

The slides are pages at `/social/recipe/<id>/<format>` and `/social/pantry` (`routes/social_routes.py`,
`templates/social/slide.html`, `static/css/social.css`), one per slide with `?slide=n&size=ig&code=3`, and
`?caption=1` for a first draft of the text. They are public like the recipes and kept out of search engines.

```bash
python -m scripts.social_render map 345 --size tt --code 1      # recipe 345 as a subway map, for TikTok
python -m scripts.social_render grid 345 --size ig --code 2
python -m scripts.social_render pantry --size tt --code 3
python -m scripts.social_render map 345 --look d                 # in look D from the style trial
python -m scripts.social_render week --size tt --code 4          # one shop, five dinners: the site picks the five
```

`--look c|d|e|f` (`?look=` on the pages) draws the slides in one of the style trial's looks (`static/css/themes.css`,
the fonts in `routes/_shared.LOOK_FONTS`), to compare the directions on real posts. The slides and the site read the
same look: its colours, fonts, headings and main button are in `themes.css` for both, and the metro map's line colours
are tokens (`--lane-0`…`--lane-3` in `tokens.css`). Post in the look visitors see on the site, today's until one is
chosen.

It reads production (or `--base http://127.0.0.1:8000`), photographs each slide with headless Chrome and writes the
PNGs and `caption.txt` to `~/promptlab-runs/social/`, outside the repo. Nothing is written to production and nothing
costs money. Give every post its own code, and use the same code for the same post on both platforms only if you want
them counted together.

To design slides without production, run the app on a local database (`docs/README_TOP_COMMANDS.md`). The public
ingredient galaxy (`/api/graph/ingredient-galaxy`) has every ingredient's name, category and symbol, enough for the
pantry CSV `scripts/local_db.py` reads when there is no production export at hand.

## Posting

- Pick recipes with a dish image (Discover shows only those).
- Edit the caption: the draft is a start, not the post.
- TikTok: post as a photo carousel and add a sound in the app. The bio has no link before 1,000 followers, so the
  address on the last slide and in the bio is how people come.
- Instagram: post as a carousel; the link in bio is `thelazychef.app/ig`.
- Label AI-generated content where the platform asks: the dish images are made by Gemini.
- Note each post's code, format and recipe, so the Funnel page's rows can be read back.
