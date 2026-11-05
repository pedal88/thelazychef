"""Words that are stored or kept as data, in the reader's language. The data stays English: filters, queries and the
slides go on using the English word, and only what a reader sees goes through label() (in a template, |label).

A catalog word (data/constraints, data/post_processing) has to be listed here to be found by pybabel:
tests/test_language.py fails when one is missing. Words in static/js are in JS_WORDS, and reach tr() through components/script_words.html.
"""
from flask_babel import gettext

from services import language


def N_(text):
    """Marks a word for pybabel; it is translated when it is shown."""
    return text


WORDS = (
    # Cuisines (post_processing/cuisines.json)
    N_('Nordic'), N_('Italian'), N_('Mexican'), N_('American'), N_('Indian'), N_('Thai'), N_('Chinese'),
    N_('Middle Eastern'), N_('Japanese'), N_('French'), N_('Greek'), N_('Korean'), N_('Eastern European'), N_('Other'),
    # Protein groups (constraints/main_protein.json)
    N_('Poultry'), N_('Red Meat'), N_('Seafood'), N_('Vegetarian'), N_('Vegan'),
    # Diets (constraints/diets.json), capitalized as they are shown
    N_('Keto'), N_('Omnivore'), N_('Paleo'), N_('Gluten-free'), N_('Pescatarian'),
    # Meal types (constraints/meal_types.json)
    N_('Breakfast'), N_('Lunch'), N_('Dinner'), N_('Snacks'), N_('Desserts'), N_('Main Dish'), N_('Appetizers'),
    N_('Sides'), N_('Soups'), N_('Salads'), N_('Beverages'), N_('Weeknight'), N_('Weekend'), N_('Guests'),
    N_('Meal Prep'), N_('Christmas'), N_('Easter'), N_('17th of May'), N_('Summer BBQ'), N_('One-Pot'),
    N_('Freezer Friendly'), N_('Slow Cooker'), N_('Baby Food'),
    # Difficulty as readers see it (routes/_shared.DIFFICULTY_LABELS)
    N_('Easy'), N_('Medium'), N_('Challenging'),
    # Settings of a recipe, as a card shows them (services/recipe_v2/persona.SETTINGS)
    N_('Kid friendly'), N_('Low carb'), N_('Baby'),
    # Where it is cooked (services/recipe_v2/derive.HEAT_LABELS)
    N_('Frying pan or wok'), N_('Pot'), N_('Oven'), N_('Grill'), N_('Air fryer'), N_('Slow cooker'), N_('Microwave'),
    N_('Sous vide'), N_('No heat'),
    # The recipe list's choices (services/recipe_library.py)
    N_('Time'), N_('Cooked in'), N_('Protein'), N_('Diet'), N_('Cuisine'), N_('Meal type'), N_('Difficulty'), N_('Heat'),
    N_('Order'), N_('Up to 20 min'), N_('Up to 30 min'), N_('Up to 45 min'), N_('Over 45 min'), N_('Newest'),
    N_('Quickest'), N_('Least hands-on'), N_('Mild'), N_('A little heat'), N_('Hot'), N_('Very hot'), N_('Under 30 min'),
    N_('One-pot'),
    # The lists and the menu (routes/recipes_routes.VIEWS, routes/_shared.MENU)
    N_('All recipes'), N_('Saved'), N_('Made'), N_('Cook next'), N_('Discover'), N_('Discover recipes'), N_('Galaxy map'),
    N_('Recipes'), N_('Recipe Mirror'), N_('Ingredients'), N_('All ingredients'), N_('Ingredient galaxy'),
    # The ingredients page (services/ingredient_library.py, constraints/categories.json capitalized)
    N_('Staples'), N_('Vegetables'), N_('Fruit'), N_('Dairy and eggs'), N_('Grains and bread'), N_('Spices and sauces'),
    N_('Cupboard'), N_('Drinks'), N_('Alcoholic beverages'), N_('Bakery and bread'), N_('Baking ingredients'),
    N_('Canned and preserved'), N_('Cereal grains and pasta'), N_('Dairy and egg'), N_('Fats and oils'),
    N_('Fish and seafood'), N_('Fruit and fruit products'), N_('Meat'), N_('Non-alcoholic beverages'),
    N_('Nuts and seeds'), N_('Sauces and condiments'), N_('Spices and herbs'),
    # The links a page's block can have (services/content/blocks.LINKABLE)
    N_('One dish at a time: save it or pass on it.'), N_('Search and filter every dish.'), N_('Recipe galaxy'),
    N_('The dishes as a map, by cuisine and protein.'), N_('Everything in the pantry, as a map.'),
    N_('What is in the pantry, with nutrition.'),
    # The chefs as the live table has them, on their public pages (routes/chefs_routes.py). Edited in the admin, a chef's
    # words stay English until they are listed here again.
    N_('The Classicist'), N_('The Original'), N_('The Minimalist'), N_('The Essentialist'), N_('The Smart Cook'),
    N_('The Optimizer'),
    N_('Cooks the dish the way it is meant to be, in any cuisine: the classic ingredients and the classic method. Never swaps what makes the dish itself, and takes the time it takes.'),
    N_('As few ingredients, steps and pots as possible, and done fast. Happy to trade a little of the result for a lot less work.'),
    N_('Gets nearly all of the classic result for far less work. Takes a shortcut only when you would hardly taste the difference, and puts the effort where it shows on the plate.'),
    N_('Let the onions take their time; this is where the sauce gets its depth.'),
    N_('Everything on one tray, into the oven, done.'),
    N_('Tinned tomatoes are as good here as fresh; save your effort for browning the meat well.'),
    # The recipe page (services/recipe_v2/view.py, groups.py, persona.py, whole.py)
    N_('Calm'), N_('Prep first'), N_('Just in time'), N_('Prep before cooking, but what can wait is done while something stands.'),
    N_('Everything that needs no heat is done before the first cook step.'),
    N_('Every step as late as possible. Shortest, busiest.'), N_('A little hot'), N_('Kid-friendly'),
    N_('Baby, 6 months+'), N_('Baby, 8 months+'), N_('Baby, 12 months+'),
    N_('Fruit and vegetables'), N_('Meat and fish'), N_('Bread'), N_('Pantry'), N_('Spices and dried herbs'),
    N_('Sauces and flavourings'), N_('Oils and fats'), N_('You probably have'), N_('prep'), N_('cook'), N_('serve'),
    # The main protein of a dish (constraints/main_protein.json, examples)
    N_('Chicken'), N_('Turkey'), N_('Duck'), N_('Beef'), N_('Pork'), N_('Lamb'), N_('Game'), N_('Salmon'), N_('Oily Fish'),
    N_('White Fish'), N_('Shrimp'), N_('Shellfish'), N_('Tofu'), N_('Beans'), N_('Lentils'), N_('Eggs'), N_('Halloumi'),
    N_('Tempeh'), N_('Legumes'), N_('Seitan'),
    # The measuring systems (services/measures.SYSTEMS), and a post's days (services/social_week.WEEK_DAYS)
    N_('Metric'), N_('US'), N_('Mon'), N_('Tue'), N_('Wed'), N_('Thu'), N_('Fri'),
)

# What the scripts say, as tr('…') with %(name)s for values
JS_WORDS = (
    N_('%(n)s recipe'), N_('%(n)s recipes'), N_('Saved'), N_('Passed'), N_('Saved. Thank you.'), N_('Saved. %(note)s'),
    N_('Something went wrong. Please try again.'), N_('Remove the photo'),
    N_('The photos are too large together (20 MB at most). Pick fewer or smaller ones.'),
    N_('%(name)s could not be saved. Try it as JPG or PNG.'),
    N_('%(n)s photos could not be saved. Try them as JPG or PNG.'),
    N_('Added to Cook Next queue!'), N_('Removed from Cook Next queue'),
    N_('Your dish'), N_('Step %(n)s of %(total)s · %(label)s'), N_('%(done)s of %(total)s steps done'),
    N_('%(label)s: %(left)s min left'), N_('%(label)s: time is up'),
    # The recipe page (static/js/steps.js, done.js, ready.js, delta.js)
    N_('once'), N_('twice'), N_('%(n)s times'), N_('You made %(title)s.'), N_('You made %(title)s in %(minutes)s minutes.'),
    N_('You made %(title)s in %(minutes)s minutes, right on the plan.'),
    N_('You made %(title)s in %(minutes)s minutes, %(under)s under the plan.'),
    N_('You made %(title)s in %(minutes)s minutes, the plan said %(plan)s.'), N_('Made it'), N_('Save'), N_('Close'),
    N_('The first time. It goes in your Made list.'), N_('Counted already: %(times)s so far.'),
    N_('You have made it %(times)s before, last on %(when)s.'), N_('You have made it %(times)s before.'),
    N_('Saved. It is in your Made list now.'), N_('Saved. That was your %(nth)s time.'),
    N_('<b>All the bowls are ready.</b> Now the heat can go on.'), N_('%(n)s of %(total)s bowls ready'), N_('shown at %(n)s'),
    N_('Done'), N_('Done <span aria-hidden="true">→</span> next step'), N_('Show the step you are on'), N_('Show all details'),
    N_('The food is ready'), N_('The step you chose'), N_('Next step'), N_('Edit your note'), N_('How did it go?'),
    N_('Looking at step %(n)s of %(total)s'), N_('Step %(n)s of %(total)s'), N_('← Back to step %(n)s'), N_('← Back'),
    N_('At the table about %(time)s'), N_('Bowl %(n)s, ready: open the bowls'), N_('bowl %(n)s · ready'),
    N_('Then: %(what)s'), N_('While you wait, %(n)s min:'), N_('While you wait:'), N_('Bowl %(n)s: %(what)s'),
    N_('Back to the recipe'), N_('Untick step %(n)s'), N_('Mark step %(n)s as done'), N_('Cook it again'),
    N_('Untick all the steps'), N_('Free %(when)s. While you wait: %(what)s'), N_('Free %(when)s'), N_('free %(when)s'),
    N_('Stop the timer for %(what)s'), N_('Start %(n)s min'), N_('Up'), N_('Time is up'), N_('%(n)s min left'),
    N_('Minute %(n)s of %(total)s in the plan.'), N_('Next up: %(what)s.'), N_('Then: %(what)s at minute %(n)s.'),
    N_('The food is ready.'), N_('View: %(what)s'), N_('%(n)s min wait · while you wait: %(what)s'), N_('%(n)s min wait'), N_('✓ ready'), N_('check'),
)


def label(word):
    """The word in the reader's language; a word without a translation, as a new value in the data, stays as it is."""
    return gettext(str(word)) if word else ''


def js_words():
    """The dictionary behind tr() in base.html; English needs none."""
    return {} if language.current() == language.DEFAULT else {word: gettext(word) for word in JS_WORDS}
