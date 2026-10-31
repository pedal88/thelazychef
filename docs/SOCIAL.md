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

The slides come in the site's look (`routes/_shared.SITE_LOOK`, D Safran for now). `--look today|c|d|e|f` (`?look=`
on the pages) draws them in another of the style trial's looks (`static/css/themes.css`,
the fonts in `routes/_shared.LOOK_FONTS`), to compare the directions on real posts. The slides and the site read the
same look: its colours, fonts, headings and main button are in `themes.css` for both, and the metro map's line colours
are tokens (`--lane-0`…`--lane-3` in `tokens.css`). Post in the look visitors see on the site, today's until one is
chosen.

It reads production (or `--base http://127.0.0.1:8000`), photographs each slide with headless Chrome and writes the
PNGs and `caption.txt` to `~/promptlab-runs/social/`, outside the repo. Nothing is written to production and nothing
costs money.

Give every post its own code: the Funnel page shows the next free one (one above every number used so far). The code
is per platform, since `/tiktok/5` and `/ig/5` are the ref codes `tiktok-5` and `instagram-5`, so the same post on
both platforms can share its number and still be counted apart. With `--code` the script ends with the address of the
post log's form, filled in with the platform, code, format and recipe.

To design slides without production, run the app on a local database (`docs/README_TOP_COMMANDS.md`). The public
ingredient galaxy (`/api/graph/ingredient-galaxy`) has every ingredient's name, category and symbol, enough for the
pantry CSV `scripts/local_db.py` reads when there is no production export at hand.

## The accounts

The Lazy Chef on TikTok and on Instagram, in English. Both use `static/brand/avatar.png` (the chef's hat on saffron)
as the profile picture. The TikTok bio gives `thelazychef.app/tiktok` as text (a bio link needs 1,000 followers); the
Instagram bio links to `thelazychef.app/ig`. Links in captions can be read but not tapped on either platform, so people
come only by typing an address or through the Instagram bio link.

## A post, from start to finish

1. **Pick the format and recipe.** One with a dish image (Discover shows only those). For `map`, a recipe with three
   or four parts, so the lines on the map meet: with one part it is one straight line and the caption's promise falls
   flat.
2. **Take the next free code** from the Funnel page (`/admin/funnel`, Per post).
3. **Render both sizes** with that code, `--size tt` and `--size ig`, and look over every slide: words broken badly,
   names that run off the slide, numbers that disagree.
4. **Write the caption** from the draft in `caption.txt`: what the post shows in a sentence or two, `Every step with
   timers: thelazychef.app/tiktok/<code>` (or `/ig/<code>`), and five hashtags. Save it as `caption-final.txt` in the
   post's folder, one for each size, so the address is right for each platform.
5. **Move the files to the phone** with AirDrop: the PNGs and `caption-final.txt` from each folder (Universal
   Clipboard also works, once Handoff is on for both the Mac and the iPhone).
6. **TikTok:** check that the profile is The Lazy Chef (the hat), then + → Upload → the five or so slides in order →
   photo mode (a strip of slides at the bottom, not a timeline) → a sound → Next. Give a short hook as the title (up to
   90 characters, shown in bold above the caption: "4 lines, 1 plate, 42 minutes"), paste the caption, turn on
   AI-generated content under More options, and post. A draft keeps the caption it was saved with: check that the
   address carries this post's code.
7. **Instagram:** check the profile, then + → Post → select several, in order → 4:5, not square → Next → music →
   paste the caption (the `/ig/` address) → turn on the AI label under advanced settings → Share.
8. **Log both posts** in the post log: the address the render script ends with, or Log a post. Put the title or hook
   in What it tries, and the sound and the post's link.
9. **Copy in the numbers** 2 and 7 days later (a reminder task in meOS for each), and once a week read them as below.
   With many posts a day, use **Copy in numbers** on the Funnel page (`/admin/funnel/numbers`): every post that went
   up on one date in one table, Day 2 or Day 7, one or both platforms, saved at once. Drafts are left out until they
   are marked posted.

The dish images are made by Gemini: label every post as AI-generated where the platform asks.

## A day of posts

At five posts a day on each platform, steps 1–5 and 8 above are one command the evening before:

```bash
python -m scripts.social_batch 2026-11-03                    # five posts the site suggests for the day
python -m scripts.social_batch 2026-11-03 --plan day.txt     # or the posts in a plan
python -m scripts.social_batch 2026-11-03 --dry-run          # show the plan only
```

A plan has a post per line: `map 345 | 4 lines, 1 plate, 42 minutes`, `grid 297 | Guess the dinner`,
`week 320,324,334,341,353`, `week` or `pantry`; after the `|` comes the hook. Without a plan the site suggests the
posts (`funnel.suggest`): weeknight dinners with a dish image that no post has drawn on in the last 60 days, map and
grid by turn, a map only from a recipe with three or four parts. A week or pantry post the same every day would be the
same post again, so those come only from a plan.

The script logs each post in the post log as a **draft** on both platforms under one code (through the social API,
`/api/social`, with the content API's key: `CONTENT_API_KEY` or the Keychain item, as `scripts/content.py`), then
renders both sizes with that code into `~/promptlab-runs/social/<day>/`, with `day.txt` listing the posts and, per
post and size, the slides, `caption.txt` (the address already carries the code) and `title.txt` (the hook, for
TikTok's title). It copies each folder to the phone through iCloud Drive (`The Lazy Chef/<day>/` there, or `--phone`),
so AirDrop is not needed. Run the same day again and it keeps the codes and renders only what is missing (`--force`
renders again). It reads production and writes only the drafts; it costs nothing.

Look over every slide, post as in steps 6–7, and press **Mark posted today** beside the draft on the Funnel page (or
set Status on the post's page, with its link). A draft's day is the day it was planned for until then.

## Learning from the posts

The Funnel page's post log (`SocialPost`, `services/funnel.py`) has a row per post: what it is, what it tries (the
words on the first slide, the sound) and the platform's numbers, copied by hand from the post's analytics 2 and 7 days
after it went up (views, likes, comments, saves, shares, profile visits). Beside them are the visits, sign-ups and
cooks its code brought, and visits per 1000 views, the number that says whether a post sends people on rather than
only being seen.

A visit counts once the page has been in view for three seconds, not when the address is fetched. When a post goes
up, Meta fetches every address in its caption from some twenty machines within the minute, as a link preview robot and
as browsers that never stay; until 31.10.2026 they counted, and gave each Instagram post 7–8 visits that were no one.

Once a week: see which posts won and lost, pick one thing to change in the next ones (format, first slide, kind of
recipe, time), and change only that. Judge a format on at least three posts, not one: what TikTok shows a post to
varies a lot. Comments that ask for something the app lacks go in the post's notes.

With dozens of posts a week, read **Per format and hook** on the Funnel page instead of the rows: for the last 7 and 28
days, per platform, each format and each hook used on two posts or more, with the number of posts, the median views,
and saves and visits per 1000 views (summed over the posts with views, so a post seen by many weighs more). Give posts
that try the same thing the same hook, word for word, so they are summed together.

To see who opened a code's address, read the production request logs (read only, on a machine with production
credentials). Meta's fetches come in the minute a post goes up, as `facebookexternalhit` or with `fbclid`; people come
later, from a phone:

```bash
gcloud logging read 'resource.type="cloud_run_revision" AND httpRequest.requestUrl:"/ig/1"' \
  --project thelazychefai-prod --limit 100 --format='value(timestamp,httpRequest.userAgent)'
```

## What the first posts said

- **Guess the dinner** (`grid`, code 2, 30.10.2026): 444 views, 6 likes and 1 save on TikTok in its first day, the
  account's most viewed post, and no one typed its address. The step from seeing a post to opening the site is where the
  funnel leaks first: watch visits per 1000 views as formats and hooks change.
