"""The week post for TikTok and Instagram: "One shop, five dinners" (docs/SOCIAL.md, services/social.py).

Five approved dinners chosen so that together they need the fewest things to buy, and one shopping list for all five.
Fewest alone gives five near-copies of the same stir-fry, so a week also has to vary:

- no two dinners are nearly the same dish (more than WEEK_SAME of their ingredients in common, by Jaccard),
- at most WEEK_PER_PROTEIN dinners with the same main protein, and at least WEEK_PROTEINS different ones,
- every dinner is a weeknight dinner: marked as a WEEK_MEAL and not baby food (age_from_months, or the meal type
  NOT_FOR_WEEK; the generation marks baby food as dinner too), at most WEEK_HANDS_ON minutes of work
  (prep_time_mins), with a dish image, one version per dish.

Staples (salt, pepper, oil, sugar, flour, water) are not bought, so they do not count. All combinations of five are too
many to try in a request (48 recipes give 1.7 million), so the week is found greedily from each recipe in turn, adding
the dinner that adds the fewest new things, and then improved by swapping one dinner at a time while it gets smaller.
The same recipes always give the same week.
"""
import itertools
from collections import Counter

from database.models import Ingredient, Recipe, RecipeLine, RecipeMealType, db
from services.recipe_library import FAMILY, one_per_dish
from services.recipe_v2 import mise

WEEK_DAYS = ('Mon', 'Tue', 'Wed', 'Thu', 'Fri')
WEEK_SAME = 0.4
WEEK_PER_PROTEIN = 2
WEEK_PROTEINS = 3
WEEK_HANDS_ON = 40
WEEK_MEAL = 'Dinner'
NOT_FOR_WEEK = 'Baby Food'
# A day's slide: the room the dish, title and margins leave the tiles; above DAY_MANY tiles the dish gets smaller
DAY_ROOM = 640
DAY_ROOM_MANY = 420
DAY_MANY = 10


def candidates():
    """{recipe id: {'protein', 'buy': frozenset of what to buy}} for the recipes a week can be made of."""
    rows = db.session.execute(
        db.select(Recipe.id, FAMILY, Recipe.base_recipe_id)
        .where(Recipe.status == 'approved', Recipe.schema_version == 2, Recipe.image_filename.isnot(None),
               Recipe.age_from_months.is_(None),
               Recipe.id.in_(db.select(RecipeMealType.recipe_id).where(RecipeMealType.meal_type == WEEK_MEAL)),
               Recipe.id.not_in(db.select(RecipeMealType.recipe_id).where(RecipeMealType.meal_type == NOT_FOR_WEEK)),
               (Recipe.prep_time_mins.is_(None)) | (Recipe.prep_time_mins <= WEEK_HANDS_ON))
        .order_by(Recipe.id)).all()
    ids = one_per_dish(rows)
    lines = db.session.execute(
        db.select(RecipeLine.recipe_id, RecipeLine.name, Ingredient.id, Ingredient.tier, Ingredient.name)
        .outerjoin(Ingredient, Ingredient.id == RecipeLine.ingredient_id)
        .where(RecipeLine.recipe_id.in_(ids))).all()
    buy = {i: set() for i in ids}
    for recipe_id, written, ingredient_id, tier, pantry_name in lines:
        line = {'name': written, 'pantry_tier': tier} if tier else {'name': written, 'pantry_name': pantry_name or ''}
        if mise.staple(line):
            continue
        buy[recipe_id].add(ingredient_id or written.strip().lower())
    proteins = dict(db.session.execute(db.select(Recipe.id, Recipe.protein_type).where(Recipe.id.in_(ids))).all())
    return {i: {'protein': (proteins.get(i) or 'none').lower(), 'buy': frozenset(buy[i])} for i in ids if buy[i]}


def _fits(week, c, complete=False):
    proteins = Counter(c[i]['protein'] for i in week)
    if max(proteins.values()) > WEEK_PER_PROTEIN or (complete and len(proteins) < WEEK_PROTEINS):
        return False
    for a, b in itertools.combinations(week, 2):
        if len(c[a]['buy'] & c[b]['buy']) / len(c[a]['buy'] | c[b]['buy']) > WEEK_SAME:
            return False
    return True


def _size(week, c):
    return len(frozenset().union(*(c[i]['buy'] for i in week)))


def pick(c, k=len(WEEK_DAYS)):
    """The k recipe ids from candidates() with the fewest things to buy that still vary, or [] when none do."""
    ids = sorted(c)
    best = None
    for start in ids:
        week = [start]
        while len(week) < k:
            options = [i for i in ids if i not in week and _fits(week + [i], c)]
            if not options:
                break
            week.append(min(options, key=lambda i: (_size(week + [i], c), i)))
        if len(week) == k and _fits(week, c, complete=True) and (
                best is None or (_size(week, c), sorted(week)) < (_size(best, c), sorted(best))):
            best = week
    if best is None:
        return []
    better = True
    while better:
        better = False
        for at, out in itertools.product(range(k), ids):
            if out in best:
                continue
            trial = best[:at] + [out] + best[at + 1:]
            if _fits(trial, c, complete=True) and _size(trial, c) < _size(best, c):
                best, better = trial, True
    return sorted(best)


def week_slides(views, images, size='ig'):
    """The slides for five recipes' views (services/recipe_v2/view.page) and dish images, in the days' order."""
    from services.social import _ingredients, columns
    days = []
    for day, view, image in zip(WEEK_DAYS, views, images):
        tiles, staples = _ingredients(view)
        days.append({'day': day, 'title': view['title'], 'total': view['total'], 'total_min': view['total_min'],
                     'image': image, 'tiles': tiles, 'staples': staples})
    used = Counter(t['name'].lower() for d in days for t in {t['name'].lower(): t for t in d['tiles']}.values())
    shop = {}
    for d in days:
        for t in d['tiles']:
            shop.setdefault(t['name'].lower(), {**t, 'amount': None, 'times': used[t['name'].lower()]})
    shop = sorted(shop.values(), key=lambda t: (-t['times'], t['name'].lower()))
    for d in days:
        for t in d['tiles']:
            t['also'] = [o['day'] for o in days if o is not d and t['name'].lower() in
                         {x['name'].lower() for x in o['tiles']}]
            t['shared'] = used[t['name'].lower()] > 1
    staples = sorted({s for d in days for s in d['staples']})
    lines = sum(len(d['tiles']) for d in days)
    times = [d['total_min'] for d in days]
    return [
        {'kind': 'week_cover', 'count': len(shop), 'days': days, 'lines': lines,
         'fastest': min(times), 'slowest': max(times)},
        {'kind': 'shop', 'title': 'The shopping list', 'tiles': shop, 'staples': staples,
         'cols': columns(len(shop), size)},
        {'kind': 'week', 'title': 'The week', 'days': days},
        # A day's tiles say which other days use them too, a line more under each; many tiles leave the dish smaller
        *({'kind': 'day', **d, 'many': len(d['tiles']) > DAY_MANY,
           'cols': max(5, columns(len(d['tiles']), size,
                                  room=DAY_ROOM_MANY if len(d['tiles']) > DAY_MANY else DAY_ROOM))}
          for d in days),
        {'kind': 'end', 'line': 'All five recipes, step by step, with timers'},
    ]
