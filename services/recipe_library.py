"""The recipe library (/recipes): which recipes a list shows, filtered, searched, sorted and a page at a time; and
Discover's stack (feed_ids), one dish at a time.

A dish and its versions by chef personas (Recipe.base_recipe_id) are one card in All: the base recipe when it is
approved and matches, else the first version that matches, so a vegetarian version still shows under a vegetarian
filter. Saved, Made and Cook next show the very recipe the person saved, so they are not grouped.

Two queries for a page: one for the ids of everything that matches (small rows), one for the recipes on the page.
"""
import json
import random
from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy import func, or_
from sqlalchemy.orm import aliased, selectinload

from database.models import (
    Ingredient,
    Recipe,
    RecipeDiet,
    RecipeLine,
    RecipeMealType,
    RecipeStep,
    UserQueue,
    UserRecipeInteraction,
    db,
)
from services.recipe_v2.derive import HEAT_LABELS

PAGE = 48
DATA = Path(__file__).resolve().parent.parent / 'data'

# Total time (Recipe.prep_time_mins, the planner's start to table) -> (at least, at most) minutes
TIMES = {'20': (None, 20), '30': (None, 30), '45': (None, 45), 'long': (46, None)}
TIME_LABELS = {'20': 'Up to 20 min', '30': 'Up to 30 min', '45': 'Up to 45 min', 'long': 'Over 45 min'}
SORT_LABELS = {'new': 'Newest', 'quick': 'Quickest', 'active': 'Least hands-on'}
SPICE_LABELS = {'0': 'Mild', '1': 'A little heat', '2': 'Hot', '3': 'Very hot'}  # Recipe.spice_level

# The hands-on minutes: the cook's time at the steps, what the planner calls A (services/recipe_v2/planner.py)
ACTIVE = (db.select(func.coalesce(func.sum(RecipeStep.active_minutes), 0))
          .where(RecipeStep.recipe_id == Recipe.id).correlate(Recipe).scalar_subquery())
FAMILY = func.coalesce(Recipe.base_recipe_id, Recipe.id)


@dataclass
class Filters:
    """What the person chose. An empty list does not filter."""
    cuisines: list = field(default_factory=list)
    diets: list = field(default_factory=list)
    meal_types: list = field(default_factory=list)
    difficulties: list = field(default_factory=list)
    proteins: list = field(default_factory=list)
    heat_sources: list = field(default_factory=list)
    spice: list = field(default_factory=list)  # levels as text, '0'-'3'
    time: str = ''
    q: str = ''


@dataclass
class Page:
    recipes: list
    total: int  # cards in the whole list
    more: bool  # are there cards after these


def _filtered(stmt, f):
    if f.cuisines:
        stmt = stmt.where(Recipe.cuisine.in_(f.cuisines))
    if f.diets:
        stmt = stmt.where(Recipe.diets.any(RecipeDiet.diet.in_(f.diets)))
    if f.meal_types:
        stmt = stmt.where(Recipe.meal_types.any(RecipeMealType.meal_type.in_(f.meal_types)))
    if f.difficulties:
        stmt = stmt.where(Recipe.difficulty.in_(f.difficulties))
    if f.proteins:
        # the derived main protein, or any line with that ingredient
        stmt = stmt.where(or_(Recipe.protein_type.in_(f.proteins), *(
            Recipe.lines.any(RecipeLine.ingredient.has(Ingredient.name.icontains(p, autoescape=True)))
            for p in f.proteins)))
    if f.heat_sources:
        stmt = stmt.where(Recipe.heat_source.in_(f.heat_sources))
    levels = [int(x) for x in f.spice if x in SPICE_LABELS]
    if levels:
        stmt = stmt.where(func.coalesce(Recipe.spice_level, 0).in_(levels))
    if f.time in TIMES:
        low, high = TIMES[f.time]
        if low is not None:
            stmt = stmt.where(Recipe.prep_time_mins >= low)
        if high is not None:
            stmt = stmt.where(Recipe.prep_time_mins <= high)
    q = f.q.strip()
    if len(q) >= 2:
        stmt = stmt.where(or_(Recipe.title.icontains(q, autoescape=True),
                              Recipe.lines.any(RecipeLine.name.icontains(q, autoescape=True)),
                              Recipe.lines.any(RecipeLine.ingredient.has(Ingredient.name.icontains(q, autoescape=True)))))
    return stmt


def _catalog(path, key):
    return json.loads((DATA / path).read_text(encoding='utf-8'))[key]


def from_args(args, difficulty_labels=None):
    """The person's choices in the address (request.args) -> (Filters, the chip groups for the page).
    difficulty_labels: stored difficulty -> what readers see (routes/_shared.DIFFICULTY_LABELS).
    A group: {'key' (the parameter), 'label', 'options': [(value, label, chosen)], 'single', 'more'} where single is
    one choice (radio) and more puts it behind More filters. Protein is chosen by group (Poultry, Seafood, ...) and
    filters on the group's labels (data/constraints/main_protein.json)."""
    proteins = {p['category']: p['examples'] for p in _catalog('constraints/main_protein.json', 'protein_types')}
    groups = [
        ('time', 'Time', TIME_LABELS, True, False),
        ('heat_source', 'Cooked in', HEAT_LABELS, False, False),
        ('protein', 'Protein', {c: c for c in proteins}, False, False),
        ('diet', 'Diet', {d: d.capitalize() for d in sorted(_catalog('constraints/diets.json', 'diets'))}, False, False),
        ('cuisine', 'Cuisine', {c: c for c in sorted(_catalog('post_processing/cuisines.json', 'cuisines'))}, False, True),
        ('meal_type', 'Meal type', {m: m for m in dict.fromkeys(_catalog('constraints/meal_types.json', 'meal_types'))},
         False, True),
        ('difficulty', 'Difficulty', {d: (difficulty_labels or {}).get(d, d) for d in _catalog('constraints/difficulty.json', 'difficulty')},
         False, True),
        ('spice', 'Heat', SPICE_LABELS, False, True),
    ]
    chosen = {key: [v for v in args.getlist(key) if v in options] for key, _, options, _, _ in groups}
    filters = Filters(cuisines=chosen['cuisine'], diets=chosen['diet'], meal_types=chosen['meal_type'],
                      difficulties=chosen['difficulty'], heat_sources=chosen['heat_source'], spice=chosen['spice'],
                      proteins=[e for c in chosen['protein'] for e in proteins[c]],
                      time=(chosen['time'] or [''])[0], q=args.get('q', '').strip())
    shown = [{'key': key, 'label': label, 'single': single, 'more': more,
              'options': [(v, text, v in chosen[key]) for v, text in options.items()]}
             for key, label, options, single, more in groups]
    return filters, shown


# The shortcuts over the list in the drawer layout (trial): (parameter, value, label), the choices people make most
QUICK = [('time', '30', 'Under 30 min'), ('diet', 'vegetarian', 'Vegetarian'), ('protein', 'Seafood', 'Seafood'),
         ('heat_source', 'oven', 'Oven'), ('meal_type', 'One-Pot', 'One-pot'), ('meal_type', 'Weeknight', 'Weeknight')]
SINGLE = {'time'}  # parameters with one value


def quick(args):
    """The shortcuts for the address args: [(label, the args with it switched, on)]. Switching a single-value
    parameter replaces its value; the page starts from the top again (no shown)."""
    out = []
    for key, value, label in QUICK:
        on = value in args.getlist(key)
        new = args.copy()
        new.pop('shown', None)
        rest = [v for v in args.getlist(key) if v != value and key not in SINGLE]
        new.setlist(key, rest if on else rest + [value])
        out.append((label, new, on))
    return out


def _ordered(stmt, view, sort):
    if view == 'saved':
        return stmt.order_by(UserRecipeInteraction.is_super_like.desc(), UserRecipeInteraction.timestamp.desc())
    if view == 'made':
        return stmt.order_by(UserRecipeInteraction.timestamp.desc())
    if view == 'next':
        return stmt.order_by(UserQueue.position.asc())
    if sort == 'quick':
        return stmt.order_by(Recipe.prep_time_mins.asc().nulls_last(), Recipe.id.desc())
    if sort == 'active':
        return stmt.order_by(ACTIVE.asc(), Recipe.prep_time_mins.asc().nulls_last(), Recipe.id.desc())
    return stmt.order_by(Recipe.id.desc())


def one_per_dish(rows):
    """[(id, family, base_recipe_id)] in list order -> the ids to show, one per dish, in the order of the one shown."""
    first, chosen = {}, {}
    for i, (rid, family, base) in enumerate(rows):
        first.setdefault(family, (i, rid))
        if base is None:  # the base recipe itself matches
            chosen[family] = (i, rid)
    return [rid for _, rid in sorted(chosen.get(fam, pos) for fam, pos in first.items())]


def feed_ids(user=None, limit=10, rng=random):
    """Discover's stack: up to limit dishes in random order, one recipe each, approved and with a dish image.
    A signed-in person gets the dishes they have not saved or passed yet, in any version; when there are none left,
    the ones they passed, again."""
    pictured = (db.select(Recipe.id, FAMILY, Recipe.base_recipe_id)
                .where(Recipe.status == 'approved', Recipe.image_filename.isnot(None)).order_by(Recipe.id))
    if user is None:
        rows = db.session.execute(pictured).all()
    else:
        other = aliased(Recipe)  # its own name, so the subquery is not tied to the outer recipe
        seen = (db.select(func.coalesce(other.base_recipe_id, other.id))
                .join(UserRecipeInteraction, UserRecipeInteraction.recipe_id == other.id)
                .where(UserRecipeInteraction.user_id == user.id))
        rows = db.session.execute(pictured.where(FAMILY.not_in(seen))).all()
        if not rows:
            passed = db.select(UserRecipeInteraction.recipe_id).where(UserRecipeInteraction.user_id == user.id,
                                                                       UserRecipeInteraction.status == 'pass')
            rows = db.session.execute(pictured.where(Recipe.id.in_(passed))).all()
    ids = one_per_dish(rows)
    return rng.sample(ids, min(limit, len(ids)))


def versions_count(recipes):
    """{family id: approved recipes in the dish} for the dishes that have more than one."""
    families = {r.base_recipe_id or r.id for r in recipes}
    if not families:
        return {}
    rows = db.session.execute(
        db.select(FAMILY, func.count()).where(Recipe.status == 'approved', FAMILY.in_(families))
        .group_by(FAMILY).having(func.count() > 1)).all()
    return dict(rows)


def recipe_page(view, f, sort='new', shown=PAGE, user=None):
    """The recipes a list shows: view is 'discover' (All), 'saved', 'made' or 'next' (the last three need user).
    shown is how many cards to show from the start (Show more adds a page). Each recipe gets active_mins,
    version_count (approved recipes in its dish, 1 when alone) and, for a signed-in user, interaction and is_super_liked."""
    stmt = db.select(Recipe.id, FAMILY, Recipe.base_recipe_id).where(Recipe.status == 'approved')
    if view == 'saved':
        stmt = stmt.join(UserRecipeInteraction).where(UserRecipeInteraction.user_id == user.id,
                                                      UserRecipeInteraction.status == 'favorite')
    elif view == 'made':
        stmt = stmt.join(UserRecipeInteraction).where(UserRecipeInteraction.user_id == user.id,
                                                      UserRecipeInteraction.is_made.is_(True))
    elif view == 'next':
        stmt = stmt.join(UserQueue).where(UserQueue.user_id == user.id)
    rows = db.session.execute(_ordered(_filtered(stmt, f), view, sort)).all()
    ids = one_per_dish(rows) if view == 'discover' else [r[0] for r in rows]

    on_page = ids[:max(shown, 1)]
    by_id = {r.id: (r, active) for r, active in db.session.execute(
        db.select(Recipe, ACTIVE).where(Recipe.id.in_(on_page))
        .options(selectinload(Recipe.diets), selectinload(Recipe.meal_types))).tuples()} if on_page else {}
    recipes = []
    for rid in on_page:
        r, active = by_id[rid]
        r.active_mins = active
        recipes.append(r)

    counts = versions_count(recipes) if view == 'discover' else {}
    marks = {}
    if user is not None and recipes:
        marks = {i.recipe_id: i for i in db.session.execute(
            db.select(UserRecipeInteraction).where(UserRecipeInteraction.user_id == user.id,
                                                   UserRecipeInteraction.recipe_id.in_(on_page))).scalars()}
    for r in recipes:
        r.version_count = counts.get(r.base_recipe_id or r.id, 1)
        r.interaction = marks.get(r.id)
        r.is_super_liked = bool(r.interaction and r.interaction.is_super_like)
    return Page(recipes=recipes, total=len(ids), more=len(ids) > len(on_page))
