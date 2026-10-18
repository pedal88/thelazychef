"""pantry cleanup 2026-10-18

Applies the cleanup Pål approved on 18.10.2026 (step 3 in
docs/RECIPE_MODEL_V2.md): merges duplicates and names with a cut or size
into the clean ingredient, renames odd names, activates pending and
missing ingredients with a category, fills nutrition for six of them
with estimates, fixes one unit, deletes one meaningless ingredient, and
writes every ingredient name in lower case.

A merge works like services/ingredient_service.merge_ingredients: recipe
lines and aliases move to the winner, the loser's name becomes an alias,
a sub-recipe link is kept, and the loser is deleted. A rename keeps the
old name as an alias. Recipe nutrition totals are not recalculated here;
the recipes are regenerated in v2 anyway.

Every ID is checked against the name it had in the export first. If one
differs, the migration stops and nothing is changed (one transaction).

Downgrade does nothing. Restore the Cloud SQL backup taken before the
deploy to undo this.

Revision ID: f22c269feda5
Revises: 2f46e44cc1ae
Create Date: 2026-10-18

"""
import datetime

from alembic import op
import sqlalchemy as sa


revision = 'f22c269feda5'
down_revision = '2f46e44cc1ae'
branch_labels = None
depends_on = None

EXPECTED_NAMES = {
    11: 'beef ground beef',
    23: 'lamb boneless lamb roast',
    24: 'lamb sliced leg of lamb',
    25: 'lamb lamb ribs',
    26: 'lamb lamb shank',
    28: 'lamb ground lamb',
    29: 'lamb sliced lamb meat',
    32: 'pork shoulder',
    33: 'pork diced shoulder',
    34: 'pork rolled pork shoulder roast',
    35: 'pork ground pork',
    39: 'pork sirloin',
    40: 'pork sliced sirloin',
    44: 'chicken breast',
    91: 'tomatoes',
    108: 'garlic',
    191: 'feta',
    193: 'cottage cheese',
    207: 'clarified butter (ghee)',
    217: 'whole eggs',
    235: 'cilantro',
    293: 'quinoa',
    323: 'sourdough',
    372: 'ghee (clarified butter)',
    419: 'canned tuna in water',
    477: 'basil pesto',
    503: 'mustard',
    610: 'Water',
    613: 'Pizza Base, pre-baked',
    618: 'Beef Stock, Cube',
    620: 'canned tuna',
    621: 'lemon juice',
    623: 'jalapeños, diced',
    624: 'yellow mustard',
    625: 'cilantro, chopped',
    626: 'lime juice',
    628: 'adobo paste',
    629: 'chipotle peppers, pureed',
    630: 'sourdough slices',
    631: 'pesto',
    632: 'avocado, sliced',
    633: 'tomatoes, sliced',
    635: 'Cottage Cheese (2% or full-fat)',
    636: 'Eggs',
    637: 'Onion Powder',
    638: 'Garlic Powder',
    639: 'Italian Seasoning',
    641: 'Kosher pepper',
    642: 'quinoa, uncooked',
    644: 'English cucumber, diced',
    645: 'Roma tomatoes, chopped',
    646: 'feta cheese, crumbled',
    647: 'kalamata olives, pitted',
    648: 'garlic clove, minced',
    649: 'boneless skinless chicken breasts',
    650: 'red onion, medium, diced',
    651: 'lemons, juiced',
    652: 'chicken breasts, boneless skinless',
    653: 'Cucumber',
    654: 'Garlic Powder',
    655: 'Ground Onion',
    658: 'Avocado',
    661: 'Cottage Cheese (2% Fat)',
    665: 'Italian seasoning',
    667: 'Guanciale',
    668: 'Pecorino Romano',
    669: 'guanciale',
    671: 'Wasabi Paste',
    672: 'Saffron threads',
    673: 'Bean Sprouts',
    674: 'Crushed Peanuts',
    675: 'Star Anise',
    676: 'Saffron Threads',
    678: 'prosciutto',
    679: 'balsamic vinegar',
    680: 'boiled ham',
    682: 'chilli paste',
    683: 'bay leaf',
    684: 'Everything Bagel',
    694: 'Breadcrumbs',
    695: 'Pomegranate molasses',
    699: 'hamburger buns',
}

# (loser, winner)
MERGES = [
    (638, 654),  # Garlic Powder (inaktiv duplikat)
    (639, 665),  # Italian Seasoning (inaktiv duplikat)
    (669, 667),  # guanciale (duplikat)
    (676, 672),  # Saffron Threads (duplikat)
    (372, 207),  # ghee (clarified butter) -> clarified butter (ghee)
    (620, 419),  # canned tuna -> canned tuna in water
    (625, 235),  # cilantro, chopped -> cilantro
    (630, 323),  # sourdough slices -> sourdough
    (631, 477),  # pesto -> basil pesto
    (632, 658),  # avocado, sliced -> avocado
    (633, 91),  # tomatoes, sliced -> tomatoes
    (645, 91),  # Roma tomatoes, chopped -> tomatoes
    (635, 193),  # Cottage Cheese (2% or full-fat) -> cottage cheese
    (661, 193),  # Cottage Cheese (2% Fat) -> cottage cheese
    (636, 217),  # Eggs -> whole eggs
    (642, 293),  # quinoa, uncooked -> quinoa
    (644, 653),  # English cucumber, diced -> cucumber
    (646, 191),  # feta cheese, crumbled -> feta
    (648, 108),  # garlic clove, minced -> garlic
    (649, 44),  # boneless skinless chicken breasts -> chicken breast
    (652, 44),  # chicken breasts, boneless skinless -> chicken breast
    (624, 503),  # yellow mustard -> mustard
    (637, 655),  # Onion Powder -> Ground Onion (heter onion powder etterpå)
    (651, 621),  # lemons, juiced -> lemon juice
    (628, 629),  # adobo paste -> chipotle peppers in adobo sauce
    (33, 32),  # pork diced shoulder -> pork shoulder
    (40, 39),  # pork sliced sirloin -> pork sirloin
]

# (id, new name)
RENAMES = [
    (207, 'ghee'),
    (217, 'eggs'),
    (655, 'onion powder'),
    (23, 'boneless lamb roast'),
    (24, 'leg of lamb'),
    (29, 'lamb meat'),
    (25, 'lamb ribs'),
    (26, 'lamb shank'),
    (11, 'ground beef'),
    (28, 'ground lamb'),
    (35, 'ground pork'),
    (34, 'rolled pork shoulder roast'),
    (618, 'beef stock cube'),
    (613, 'pre-baked pizza base'),
    (674, 'peanuts'),
    (623, 'jalapeños'),
    (650, 'red onion'),
    (629, 'chipotle peppers in adobo sauce'),
    (647, 'kalamata olives'),
]

# (id, main category, sub category, is_staple)
ACTIVATE = [
    (610, 'non-alcoholic beverages', 'water', True),  # Water
    (621, 'fruit and fruit products', 'juices', False),  # lemon juice
    (626, 'fruit and fruit products', 'juices', False),  # lime juice
    (623, 'vegetables', 'nightshade vegetables', False),  # jalapeños, diced
    (650, 'vegetables', 'bulb vegetables', False),  # red onion, medium, diced
    (629, 'canned and preserved', 'canned vegetables', False),  # chipotle peppers, pureed
    (647, 'canned and preserved', 'pickled foods', False),  # kalamata olives, pitted
    (667, 'meat', 'pork', False),  # Guanciale
    (668, 'dairy and egg', 'cheese', False),  # Pecorino Romano
    (671, 'sauces and condiments', 'savory condiments', False),  # Wasabi Paste
    (672, 'spices and herbs', 'whole spices', False),  # Saffron threads
    (673, 'vegetables', 'legumes & pulses', False),  # Bean Sprouts
    (674, 'nuts and seeds', 'nuts', False),  # Crushed Peanuts
    (675, 'spices and herbs', 'whole spices', False),  # Star Anise
    (678, 'meat', 'pork', False),  # prosciutto
    (679, 'sauces and condiments', 'other sauces & condiments', False),  # balsamic vinegar
    (680, 'meat', 'pork', False),  # boiled ham
    (682, 'sauces and condiments', 'savory condiments', False),  # chilli paste
    (683, 'spices and herbs', 'dried herbs', False),  # bay leaf
    (684, 'bakery and bread', 'bread', False),  # Everything Bagel
    (694, 'bakery and bread', 'bread', False),  # Breadcrumbs
    (695, 'sauces and condiments', 'sweet condiments & spreads', False),  # Pomegranate molasses
    (699, 'bakery and bread', 'bread', False),  # hamburger buns
]

# id: (kcal, protein, carbs, fat) per 100 g, estimates
NUTRITION = {
    682: (40, 1.5, 8, 0.5),  # chilli paste
    683: (313, 7.6, 75, 8.4),  # bay leaf (dried)
    684: (270, 10, 52, 2.5),  # everything bagel
    694: (395, 13.4, 72, 5.3),  # breadcrumbs
    695: (260, 0.5, 65, 0),  # pomegranate molasses
    699: (279, 9.5, 50, 4.2),  # hamburger buns
}

UNITS = [(654, 'tsp')]

DELETE = [641]  # "Kosher pepper", unused


def _norm(name):
    return " ".join((name or "").split()).lower()


def upgrade():
    conn = op.get_bind()
    run = lambda sql, **kw: conn.execute(sa.text(sql), kw)  # noqa: E731
    now = datetime.datetime.utcnow()

    current = dict(run("SELECT id, name FROM ingredient WHERE id = ANY(:ids)", ids=list(EXPECTED_NAMES)).all())
    wrong = {i: (n, current.get(i)) for i, n in EXPECTED_NAMES.items() if current.get(i) != n}
    if wrong:
        raise RuntimeError(f"Pantry changed since the export, nothing applied: {wrong}")

    def name_of(i):
        return run("SELECT name FROM ingredient WHERE id = :i", i=i).scalar()

    def add_alias(i, alias):
        alias = _norm(alias)
        if not alias or alias == _norm(name_of(i)):
            return
        if run("SELECT 1 FROM ingredient_alias WHERE name = :a", a=alias).first() is None:
            run("INSERT INTO ingredient_alias (ingredient_id, name, created_at) VALUES (:i, :a, :t)", i=i, a=alias, t=now)

    for loser, winner in MERGES:
        run("UPDATE recipe_ingredient SET ingredient_id = :w WHERE ingredient_id = :l", w=winner, l=loser)
        run("DELETE FROM ingredient_alias WHERE ingredient_id = :l AND name = :n", l=loser, n=_norm(name_of(winner)))
        run("UPDATE ingredient_alias SET ingredient_id = :w WHERE ingredient_id = :l", w=winner, l=loser)
        run("""UPDATE ingredient SET sub_recipe_id = (SELECT sub_recipe_id FROM ingredient WHERE id = :l)
               WHERE id = :w AND sub_recipe_id IS NULL""", w=winner, l=loser)
        loser_name = name_of(loser)
        run("DELETE FROM ingredient WHERE id = :l", l=loser)
        add_alias(winner, loser_name)

    for i, new_name in RENAMES:
        old_name = name_of(i)
        run("UPDATE ingredient SET name = :n WHERE id = :i", n=new_name, i=i)
        run("DELETE FROM ingredient_alias WHERE ingredient_id = :i AND name = :n", i=i, n=_norm(new_name))
        add_alias(i, old_name)

    for i, main, sub, staple in ACTIVATE:
        run("""UPDATE ingredient SET status = 'active', main_category = :m, sub_category = :s, is_staple = :st
               WHERE id = :i""", m=main, s=sub, st=staple, i=i)

    for i, (kcal, protein, carbs, fat) in NUTRITION.items():
        run("""UPDATE ingredient SET calories_per_100g = :k, kj_per_100g = :kj, protein_per_100g = :p,
               carbs_per_100g = :c, fat_per_100g = :f, data_source = 'ai_estimate' WHERE id = :i""",
            k=kcal, kj=round(kcal * 4.184, 1), p=protein, c=carbs, f=fat, i=i)

    for i, unit in UNITS:
        run("UPDATE ingredient SET default_unit = :u WHERE id = :i", u=unit, i=i)

    for i in DELETE:
        if run("SELECT 1 FROM recipe_ingredient WHERE ingredient_id = :i", i=i).first():
            raise RuntimeError(f"Ingredient {i} is used in a recipe, not deleting")
        run("DELETE FROM ingredient WHERE id = :i", i=i)

    clashes = run("SELECT lower(name) FROM ingredient GROUP BY lower(name) HAVING count(*) > 1").scalars().all()
    if clashes:
        raise RuntimeError(f"Lower-casing would create duplicate names: {clashes}")
    lowered = run("UPDATE ingredient SET name = lower(name) WHERE name <> lower(name)").rowcount

    print(f"Pantry cleanup: {len(MERGES)} merged, {len(RENAMES)} renamed, {len(ACTIVATE)} activated, "
          f"{len(NUTRITION)} nutrition estimates, {len(DELETE)} deleted, {lowered} names lower-cased")


def downgrade():
    # Data changes only; restore the Cloud SQL backup taken before the deploy.
    pass
