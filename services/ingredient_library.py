"""The ingredients page (templates/pantry_management.html, routes/pantry_routes.py): finding an ingredient, and which
dishes it is in. What the recipes use comes first and alone until someone asks for all of it or searches."""
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlencode

from database.models import Ingredient, Recipe, RecipeLine, db
from services.labels import label
from services.recipe_library import FAMILY, PAGE, one_per_dish

# The shortcuts, each a set of Ingredient.main_category (data/constraints/categories.json)
GROUPS = {
    'protein': ('Protein', ('meat', 'fish and seafood')),
    'vegetables': ('Vegetables', ('vegetables',)),
    'fruit': ('Fruit', ('fruit and fruit products',)),
    'dairy': ('Dairy and eggs', ('dairy and egg',)),
    'grains': ('Grains and bread', ('cereal grains and pasta', 'bakery and bread')),
    'seasoning': ('Spices and sauces', ('spices and herbs', 'sauces and condiments')),
    'cupboard': ('Cupboard', ('fats and oils', 'baking ingredients', 'canned and preserved', 'nuts and seeds')),
    'drinks': ('Drinks', ('alcoholic beverages', 'non-alcoholic beverages')),
}
RECIPES_ON_CARD = 6


@dataclass
class Filters:
    q: str = ''
    group: str = ''
    staples: bool = False
    everything: bool = False  # also what no recipe uses yet


def from_args(args):
    group = args.get('group', '')
    return Filters(q=args.get('q', '').strip(), group=group if group in GROUPS else '',
                   staples=args.get('staples') == '1', everything=args.get('all') == '1')


def address(f, **changed):
    """The query string for these filters with some changed; a change starts the list from the top again."""
    values = {'q': f.q, 'group': f.group, 'staples': '1' if f.staples else '', 'all': '1' if f.everything else '',
              **changed}
    query = urlencode({k: v for k, v in values.items() if v})
    return f'?{query}' if query else ''


def _clean(text):
    """A category as one plain string: some were saved with non-breaking spaces."""
    return ' '.join((text or '').replace('\xa0', ' ').split())


def dishes_using(ingredient_id=None):
    """{ingredient id: [recipe ids]}: the approved recipes with it, one per dish, by title."""
    stmt = (db.select(RecipeLine.ingredient_id, Recipe.id, FAMILY, Recipe.base_recipe_id)
            .join(Recipe, Recipe.id == RecipeLine.recipe_id)
            .where(Recipe.status == 'approved', RecipeLine.ingredient_id.is_not(None))
            .order_by(Recipe.title, Recipe.id))
    if ingredient_id is not None:
        stmt = stmt.where(RecipeLine.ingredient_id == ingredient_id)
    rows = {}
    for ing, rid, family, base in db.session.execute(stmt):
        rows.setdefault(ing, []).append((rid, family, base))
    return {ing: one_per_dish(found) for ing, found in rows.items()}


def page(f, shown=PAGE, admin=False):
    """What the page shows: the ingredients on it with how many dishes each is in, the shortcuts, and how many more
    there are behind Show more and behind Show all."""
    stmt = db.select(Ingredient.id, Ingredient.name, Ingredient.main_category, Ingredient.image_url,
                     Ingredient.is_staple, Ingredient.status)
    if not admin:
        stmt = stmt.where(Ingredient.status == 'active')
    uses = {ing: len(ids) for ing, ids in dishes_using().items()}
    needle = f.q.casefold()
    found = []
    for row in db.session.execute(stmt):
        if needle and needle not in row.name.casefold():
            continue
        if f.group and _clean(row.main_category) not in GROUPS[f.group][1]:
            continue
        if f.staples and not row.is_staple:
            continue
        found.append(row)
    found.sort(key=lambda r: (-uses.get(r.id, 0), r.name.casefold()))
    # A search looks through everything; only a list needs the ones in recipes first
    listed = found if f.everything or f.q else [r for r in found if uses.get(r.id)]
    on_page = listed[:max(shown, 1)]
    return {'items': [{'row': r, 'uses': uses.get(r.id, 0)} for r in on_page], 'total': len(listed),
            'hidden': len(found) - len(listed), 'found': len(found),
            'more_url': address(f, shown=shown + PAGE) if len(listed) > shown else None}


def shortcuts(f):
    """[(label, address, on)]: the groups and Staples, each one a switch that keeps the other choices."""
    out = [(label(text), address(f, group='' if f.group == key else key), f.group == key)
           for key, (text, _) in GROUPS.items()]
    out.insert(0, (label('Staples'), address(f, staples='' if f.staples else '1'), f.staples))
    return out


def card(ingredient_id, admin=False) -> Optional[dict]:
    """One ingredient for its sheet: itself and the dishes it is in, or None when this viewer may not see it."""
    ingredient = db.session.get(Ingredient, ingredient_id)
    if not ingredient or (ingredient.status != 'active' and not admin):
        return None
    ids = dishes_using(ingredient_id).get(ingredient_id, [])
    recipes = db.session.execute(db.select(Recipe).where(Recipe.id.in_(ids[:RECIPES_ON_CARD]))).scalars().all()
    recipes.sort(key=lambda r: ids.index(r.id))
    return {'ingredient': ingredient, 'recipes': recipes, 'uses': len(ids)}
