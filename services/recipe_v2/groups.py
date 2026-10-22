"""Kitchen groups for the ingredient lists on Overview and Prep (RECIPE_VISUALIZATIONS.md 9.16).

The pantry's 15 main categories are too fine and sometimes wrong for a shop or a kitchen: fresh basil is a
herb like dried oregano, and canned tomatoes stand on their own. They are folded into a few groups in the
order you walk a shop. Staples (pantry tier 'staple': salt, pepper, oil, water, sugar, flour) are their own
group last: you probably have them.
Lines that are not in the pantry go under Other.
"""
GROUPS = (
    ('produce', 'Fruit and vegetables'),
    ('meat', 'Meat and fish'),
    ('dairy', 'Dairy and eggs'),
    ('bread', 'Bread'),
    ('dry', 'Pantry'),  # pasta, grains, flour, sugar, nuts and tins
    ('spices', 'Spices and dried herbs'),
    ('sauces', 'Sauces and flavourings'),
    ('fats', 'Oils and fats'),
    ('drinks', 'Drinks'),
    ('other', 'Other'),
    ('staples', 'You probably have'),
)
LABELS = dict(GROUPS)
MAIN = {
    'vegetables': 'produce', 'fruit and fruit products': 'produce',
    'meat': 'meat', 'fish and seafood': 'meat',
    'dairy and egg': 'dairy',
    'bakery and bread': 'bread',
    'cereal grains and pasta': 'dry', 'baking ingredients': 'dry', 'nuts and seeds': 'dry', 'canned and preserved': 'dry',
    'spices and herbs': 'spices',
    'sauces and condiments': 'sauces',
    'fats and oils': 'fats',
    'alcoholic beverages': 'drinks', 'non-alcoholic beverages': 'drinks',
}
SUB = {'fresh herbs': 'produce'}


def group_of(ingredient, is_staple=False):
    """The group key for a pantry ingredient (None when the line is not in the pantry)."""
    if is_staple:
        return 'staples'
    if ingredient is None:
        return 'other'
    sub = (ingredient.sub_category or '').strip().lower()
    main = (ingredient.main_category or '').strip().lower()
    return SUB.get(sub) or MAIN.get(main) or 'other'


def grouped(items, key=lambda item: item['group']):
    """[{'key', 'label', 'items'}] in shop order; the items keep their order within a group."""
    out = {g: [] for g, _ in GROUPS}
    for item in items:
        out[key(item) if key(item) in out else 'other'].append(item)
    return [{'key': g, 'label': LABELS[g], 'items': out[g]} for g, _ in GROUPS if out[g]]
