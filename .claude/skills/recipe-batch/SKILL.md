---
name: recipe-batch
description: Plan, make and review a batch of new recipes for The Lazy Chef (Many recipes at once, then the review report and approval). Use when Pål wants new dishes added, a dish catalog turned into recipes, or a batch checked before approval.
---

# A batch of recipes, from lines to approved

## 1. Write the lines

One line per recipe for Admin → Many recipes at once (`services/recipe_v2/batch.py` reads them):

```text
<idea, one line, at most 200 characters> | <chef> | <settings>
```

- **The idea** says what makes the dish: main ingredients, how it is cooked, sides, servings ("for 4"), and time
  ("ready in 30 minutes"). Write it in English unless Pål asks otherwise, and pick English under Language.
  Details that matter must be in the line ("no salt" for baby food, "in the air fryer", "silicone cups").
- **Chef**: `classicist` (the original, takes the time it takes), `smart` (at most 60 minutes, 10 ingredients),
  `minimalist` (few ingredients, little hands-on time). The live rules are in the `chef` table (Admin → Chefs), not
  in `data/agents/chefs.json`.
- **Settings**: `vegetarian`, `kid`, `low carb`, `baby 6` / `baby 8` / `baby 12`.
- Check the lines with the real parser before giving them to Pål (no database needed):
  `batch.parse(text, chefs)` with the chefs from `data/agents/chefs.json`; every line should have no error.
- Give the lines in one ```text block, and say which machine: the batch page runs in the browser.

## 2. What happens by itself

For each line the queue writes and structures the recipe (Claude), fills the pantry for unlinked lines (alias, new
item with nutrition and symbol, or skip), recalculates, and draws the dish and its parts. Cost: about $0.25–0.85 a
recipe with images (`docs/SERVICES_AND_COSTS.md`). The batch status page follows them; Admin → Images for recipes
retries failed images.

## 3. Review

When the batch status page shows all done, have Pål run the read-only report (use the prod-script skill for the
command): `python -m scripts.review_recipes --ids <first>-…` (comma-separated ids) and copy the report back.

Read every recipe in the report and sort them:
- **Approve**: no flags, or flags that are honest information (a Smart Cook dish over 60 minutes that really takes
  that long, image check remarks that do not matter).
- **Fix**: a rule that matters is broken (salt for a baby, low carb over the limit, a line that should not be
  there), nutrition missing or implausible (check the lines: dry vs cooked weights, a missing pantry link),
  the wrong cuisine. Most fixes are "make it again" with a better line (Many recipes at once with
  "Make lines again"), then set the old one to Rejected.
- Look across the batch for patterns (a chef rule broken by most dishes means the rule may be wrong).

Give Pål the approve list (ids) and the fix list with the action for each. He approves in Admin → Recipes
Management (tick and approve).

## 4. After rule or code changes

Changing a chef's rules, nutrition, derive or the pantry does not change saved recipes. Recalculate them with
`python -m scripts.fill_pantry --ids <range> --apply` (prod-script skill).
