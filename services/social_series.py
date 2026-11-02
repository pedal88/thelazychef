"""The post series for TikTok and Instagram (docs/SOCIAL.md "The series"): a fixed promise repeated with a new dish
each time, so there is a reason to follow and the agent can make every post from the database.

Every series is a card, data/social/series/<slug>.yaml: the why at the top (purpose, message, hypothesis, the signal
it is judged on, when to stop) and below it what the code reads: the pick (filter and how many recipes), the slides
in order (SLIDE_KINDS), the CTA group, the approved hook phrasings per group (the first group is the default), the
proposed ones and the retired ones with why. The hook and CTA groups every series shares are data/social/hooks.yaml.
check_cards() says what is wrong with a card (a test runs it).

A post of a series has a number (#7), a hook (the words on the first slide, a phrasing that states the post's own
numbers, drawn with a seed from the series, number and recipes so a post renders the same every time) and a CTA.
Time is said only when it is short (services/social.py SAY_ACTIVE_UNDER and SAY_TOTAL_UPTO): the time facts a
phrasing needs exist only then, so a slow dinner never gets a phrasing with minutes.

Picking: only approved dinners with a dish image, within the series' filter, a recipe at most once in ONCE_A_WEEK
days per series (the post log, SocialPost.series and recipe_ids), never used first, then the longest ago; High-protein
puts the lighter dishes first.
"""
import datetime
import itertools
import os
import random
import re

import yaml
from sqlalchemy import func

from database.models import Ingredient, Recipe, RecipeMealType, RecipeStep, SocialPost, db
from services import social, social_week
from services.recipe_library import FAMILY, one_per_dish
from services.recipe_v2.derive import ACCENT, ANIMAL, FISH_NAMES, MEAT_LABELS, OTHER_PROTEINS, VESSELS

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CARDS = os.path.join(ROOT, 'data', 'social', 'series')
SHARED = os.path.join(ROOT, 'data', 'social', 'hooks.yaml')

PROTEIN_G = 35      # High-protein dinners: at least this much protein per serving
WASH_MAX = 2        # one or two dishes to wash (the contrast hook)
BUY_MAX = 6         # Only 6 things to buy: at most this many
SHARED_MIN = 3      # 3 ingredients, 3 dinners: at least this many shared, staples left out
GUESS_MAX = 15      # Guess the dinner: at most this many things to buy, so the pictures fit a slide (the rest are left out)
# The points game (guess.yaml): the points per slide, the score line and the line at the bottom
GUESS = [('guess_pictures', 5, 'points if you get it from the pictures', 'Not sure? Swipe for the names.'),
         ('guess_names', 4, 'points with the names', 'Still not sure? Swipe for the amounts.'),
         ('guess_amounts', 3, 'points with the amounts', 'Last clue: swipe to see the dish.'),
         ('guess_dish', 2, 'points if you know it now', 'Swipe for the answer.')]
GUESS_KINDS = tuple(k for k, _, _, _ in GUESS)
ONCE_A_WEEK = 7     # days a recipe stays out of a series after a post
NOT_AN_INGREDIENT = ('Vegetarian', 'Other')  # protein labels What to make with cannot ask for
HOOK_WORDS = 8      # a hook is at most this many words, filled in
STATUSES = ('active', 'paused', 'retired')
# The pick filters a card may name (candidates())
FILTERS = ('guess', 'airfryer', 'protein', 'onepot', 'under20', 'only6', 'got', 'three3', 'cuisine')
# The slide kinds a card may list, built in slides(): a kind may stand for several slides (days, shop, grid, steps)
SLIDE_KINDS = ('cover', 'got_cover', 'trio_cover', 'week_cover', 'airfryer', 'numbers', 'delta', 'steps', 'wash',
               'ingredients', 'shop_split', 'days', 'shop', 'grid', 'end',
               'guess_pictures', 'guess_names', 'guess_amounts', 'guess_dish', 'answer')
# The facts a hook phrasing may need, and what they are (facts()); a time fact exists only when the time may be said
FACTS = {
    'n': "the post's number in the series", 'series': "the series' name, filled in", 'dish': 'the dish, short',
    'title': "the dish's full title", 'dishes': 'how many dinners the post has', 'many': 'more than one dinner',
    'count': 'things to buy (one list for several dinners)', 'symbols': "the first dinner's ingredient symbols",
    'total': 'minutes from start to table, one dinner, when short', 'active': 'minutes of work, one dinner, when short',
    'idle': 'minutes the cook is not working, one dinner, when the active time is short',
    'fastest': 'the fastest dinner, minutes, when short', 'doer': 'who does the idle minutes ("the oven")',
    'doer_cap': 'the same, capitalised', 'restful': 'the doer does at least as much as the cook',
    'machine': 'the idle minutes are a heat source, not just waiting',
    'machine_min': "the heat source's own minutes, when short", 'temp': 'the heat source\'s temperature ("200 °C")',
    'stress_active': 'the work is very short (under 10 min)', 'stress_total': 'dinner is very fast (under 20 min)',
    'vessels': 'dishes to wash', 'one_two': 'one or two dishes to wash', 'few': 'at most 15 things to buy',
    'protein': 'g protein per serving', 'kcal': 'kcal per serving',
    'ingredient': 'the shared ingredient (What to make with)', 'ingredient_cap': 'the same, capitalised',
    'ingredients': 'the shared ingredients, named (3 ingredients, 3 dinners)',
    'cuisine': 'the cuisine (the week)', 'meal': '"dinner", or "dish" when the recipe is not a dinner',
    'vessel': 'the one vessel the food is cooked in ("frying pan"), when there is exactly one',
    'one_dish': 'exactly one dish to wash, literally', 'protein_min': 'the lowest g protein per serving of the dinners',
    'only_six': 'at most six things to buy (BUY_MAX)',
}
# The facts every post has (never None), so a phrasing may use them without needing them; the rest must be needed
ALWAYS = ('n', 'series', 'dish', 'title', 'dishes', 'count', 'symbols', 'doer', 'doer_cap', 'vessels', 'meal')


def _phrasings(rows):
    return [(row['text'], tuple(row.get('needs') or ())) for row in rows or []]


def load_shared(path=SHARED):
    """(HOOKS, CTAS) from data/social/hooks.yaml: {group: [(text, needs)]} and {group: [text] | {'one', 'many'}}."""
    with open(path, encoding='utf-8') as f:
        data = yaml.safe_load(f) or {}
    hooks = {group: _phrasings(rows) for group, rows in (data.get('hooks') or {}).items()}
    return hooks, data.get('ctas') or {}


def load_cards(folder=CARDS):
    """{slug: card} from data/social/series/*.yaml, as the code reads a card: the why as written, count and filter
    from pick, the hooks as (text, needs) per group with the first group as the default (hook)."""
    cards = {}
    for name in sorted(os.listdir(folder)):
        if not name.endswith('.yaml'):
            continue
        with open(os.path.join(folder, name), encoding='utf-8') as f:
            card = yaml.safe_load(f) or {}
        pick = card.get('pick') or {}
        hooks = {group: _phrasings(rows) for group, rows in (card.get('hooks') or {}).items()}
        cards[name[:-5]] = {**card, 'slug': name[:-5], 'count': pick.get('count', 1), 'filter': pick.get('filter'),
                            'hooks': hooks, 'hook': next(iter(hooks), None), 'slides': card.get('slides') or [],
                            'proposed_hooks': card.get('proposed_hooks') or [], 'retired_hooks': card.get('retired_hooks') or []}
    return cards


def sample_facts():
    """Facts with every key filled, to try a phrasing's length (check_cards)."""
    return {'n': 12, 'series': 'Air fryer dinners', 'dish': 'Chicken Gyros Plate',
            'title': 'Chicken Gyros Plate with Tzatziki and Greek Salad', 'dishes': 4, 'many': True, 'count': 23,
            'symbols': 12, 'total': 30, 'active': 19, 'idle': 11, 'fastest': 30, 'doer': 'the slow cooker',
            'doer_cap': 'The slow cooker', 'restful': True, 'machine': True, 'machine_min': 19, 'temp': '200 °C',
            'stress_active': True, 'stress_total': True, 'vessels': 2, 'one_two': True, 'few': True, 'protein': 46,
            'kcal': 425, 'ingredient': 'chicken thighs', 'ingredient_cap': 'Chicken thighs', 'cuisine': 'Middle Eastern',
            'ingredients': 'chicken, onion, tomatoes', 'meal': 'dinner', 'vessel': 'frying pan', 'one_dish': True,
            'protein_min': 38, 'only_six': True}


def check_cards(cards=None, hooks=None, ctas=None):
    """What is wrong with the cards and the shared hooks, as sentences; [] when nothing. A hook over HOOK_WORDS
    words (filled with sample facts), a fact no post has, a slide kind that is not one, a CTA group that is not
    one, a status that is not one, and a why field left empty."""
    cards = SERIES if cards is None else cards
    hooks = HOOKS if hooks is None else hooks
    ctas = CTAS if ctas is None else ctas
    problems = []
    sample = sample_facts()

    def check(where, group, text, needs):
        unknown = [k for k in needs if k not in FACTS]
        if unknown:
            problems.append(f'{where}, {group}: "{text}" needs {", ".join(unknown)}, which no post has')
        used = set(re.findall(r'{(\w+)}', text))
        if used - set(FACTS):
            problems.append(f'{where}, {group}: "{text}" uses {", ".join(sorted(used - set(FACTS)))}, which no post has')
        covered = set(needs) | set(ALWAYS) | {f'{k}_cap' for k in needs}
        if used - covered:
            problems.append(f'{where}, {group}: "{text}" uses {", ".join(sorted(used - covered))} without needing it')
        try:
            words = len(text.format(**sample).split())
        except (KeyError, IndexError):
            words = len(text.split())
        if words > HOOK_WORDS:
            problems.append(f'{where}, {group}: "{text}" is {words} words, over {HOOK_WORDS}')

    for group, rows in hooks.items():
        for text, needs in rows:
            check('hooks.yaml', group, text, needs)
    for slug, card in cards.items():
        where = f'{slug}.yaml'
        for key in ('name', 'purpose', 'message', 'hypothesis', 'signal', 'stop_when', 'noun', 'hashtags'):
            if not card.get(key):
                problems.append(f'{where}: {key} is empty')
        if card.get('status') not in STATUSES:
            problems.append(f'{where}: status must be one of {", ".join(STATUSES)}, not {card.get("status")!r}')
        if card.get('filter') not in FILTERS:
            problems.append(f'{where}: pick.filter must be one of {", ".join(FILTERS)}, not {card.get("filter")!r}')
        for kind in card['slides']:
            if kind not in SLIDE_KINDS:
                problems.append(f'{where}: slide kind {kind!r} is not one of {", ".join(SLIDE_KINDS)}')
        if not card['slides'] or card['slides'][-1] not in ('end', 'answer'):
            problems.append(f'{where}: the slides must end with end (or the answer)')
        if card.get('cta') not in ctas:
            problems.append(f'{where}: cta must be one of {", ".join(ctas)}, not {card.get("cta")!r}')
        if not card['hooks']:
            problems.append(f'{where}: no approved hooks')
        for group, rows in card['hooks'].items():
            if group not in hooks:
                problems.append(f'{where}: hook group {group!r} is not in hooks.yaml')
            for text, needs in rows:
                check(where, group, text, needs)
        for row in card['retired_hooks']:
            if not row.get('why'):
                problems.append(f'{where}: retired hook "{row.get("text")}" has no why')
    return problems


HOOKS, CTAS = load_shared()
SERIES = load_cards()


def active():
    """The slugs of the series that run now."""
    return [slug for slug, card in SERIES.items() if card.get('status') == 'active']


def seed(slug, n, ids):
    """The seed a post's phrasings are drawn with: the same post draws the same words every time."""
    return f'{slug}:{n}:{",".join(str(i) for i in ids)}'


def hook(group, facts, seed, slug=None):
    """The words on the first slide for a hook group, or None when the group is not one or has nothing it can say
    about this post. A series' own phrasings for the group come first (its card); a phrasing is drawn only when
    the post has every fact it needs and the filled text is at most HOOK_WORDS words."""
    if group not in HOOKS:
        return None
    phrasings = (SERIES.get(slug) or {}).get('hooks', {}).get(group) or HOOKS[group]
    fits = []
    for text, needs in phrasings:
        if all(facts.get(k) not in (None, False, '') for k in needs):
            filled = text.format(**facts)
            if len(filled.split()) <= HOOK_WORDS:
                fits.append(filled)
    if not fits:
        return None
    return random.Random(seed + ':hook').choice(fits)


def hook_for(group, facts, seed, slug=None):
    """The hook for a series post: the group asked for when it has words for this post, else the series' own group,
    then its other groups, else a number."""
    own = list(SERIES[slug]['hooks']) if slug else []
    for g in [group, *own, 'number']:
        text = g and hook(g, facts, seed, slug)
        if text:
            return g, text
    return 'number', f"{facts['count']} things to buy."


def cta(group, facts, size, address, seed, noun='dinner', slug=None):
    """The last slide's call to action: {'group', 'text'}, or None when the group is not one. A card's own words for
    the group (ctas in the card) come before the shared ones."""
    if group not in CTAS:
        return None
    if group == 'bio' and size != 'ig':
        group = 'site'
    choices = ((SERIES.get(slug) or {}).get('ctas') or {}).get(group) or CTAS[group]
    if isinstance(choices, dict):
        choices = choices['many' if facts.get('many') else 'one']
    text = random.Random(seed + ':cta').choice(choices).format(noun=noun, address=address, dishes=facts.get('dishes'))
    return {'group': group, 'text': text}


CUT = re.compile(r'\s+(with|in|on|and|for|from)\s+|,\s+|\s+\(', re.IGNORECASE)


def short_title(title):
    """The dish in a few words, for a hook: the title up to its first "with", "and", "in", comma or bracket, without
    a leading "Air fryer" ("Chicken Gyros Plate with Tzatziki and Greek Salad" is "Chicken Gyros Plate")."""
    short = CUT.split(title, 1)[0].strip()
    short = re.sub(r'^air[ -]?fryer\s+', '', short, flags=re.IGNORECASE)
    return short or title


def facts(posts, n=None, count=None, ingredient=None, cuisine=None, series=None, ingredients=None):
    """What the hooks can say about a post (FACTS): posts are post_of() dicts; count overrides the things to buy
    (one list for several dinners). Every value is the post's own number, and a time is there only when it is
    short enough to be said (social.said_active, social.said_total)."""
    v = posts[0]['view']
    tiles, _ = social._ingredients(v)
    many = len(posts) > 1
    total_min, active_min = v['total_min'], min(v['active_min'], v['total_min'])
    # One dinner has a time; several have only the fastest of them, so no hook sums or picks the slowest. The
    # hands-off minutes and who does them are the time bar's and the air fryer slide's (social.hands_off), so the
    # viewer meets one number; "you against the air fryer" is said only when the air fryer does at least as much
    total = None if many else social.said_total(total_min)
    active = None if many else social.said_active(active_min)
    idle_min, doer = social.hands_off(v, posts[0]['heat_source']) if not many else (None, social.IDLE)
    machine = doer != social.IDLE
    idle = idle_min if active is not None else None
    fastest = social.said_total(min(p['view']['total_min'] for p in posts))
    vessels = len([e for e in v['equipment'] if e['id'] in VESSELS])
    cooking = social.cooking_vessels(v)
    nutrition = v['nutrition'] or {}
    proteins = [(p['view']['nutrition'] or {}).get('protein') for p in posts]
    f = {'n': n, 'series': series, 'dish': short_title(v['title']), 'title': v['title'], 'dishes': len(posts),
         'meal': 'dinner' if posts[0].get('dinner', True) else 'dish', 'ingredients': ingredients,
         'vessel': cooking[0]['name'].lower() if len(cooking) == 1 else None, 'one_dish': vessels == 1,
         'only_six': (len(tiles) if count is None else count) <= BUY_MAX,
         'protein_min': min(proteins) if many and all(p is not None for p in proteins) else None,
         'many': many, 'count': len(tiles) if count is None else count, 'symbols': len(tiles),
         'total': total, 'active': active, 'idle': idle, 'fastest': fastest, 'doer': doer, 'doer_cap': doer.capitalize(),
         'restful': bool(idle) and idle >= (active or 0), 'machine': machine,
         'machine_min': social.said_active(idle_min) if machine and not many else None,
         'temp': social.machine_temp(v, posts[0]['heat_source']) if machine and not many else None,
         'stress_active': active is not None and active < social.STRESS_ACTIVE_UNDER,
         'stress_total': total is not None and total < social.STRESS_TOTAL_UNDER,
         'vessels': vessels, 'one_two': 1 <= vessels <= WASH_MAX, 'few': (len(tiles) if count is None else count) <= 15,
         'protein': nutrition.get('protein'), 'kcal': nutrition.get('kcal'), 'ingredient': ingredient,
         'ingredient_cap': ingredient[:1].upper() + ingredient[1:] if ingredient else None, 'cuisine': cuisine}
    assert set(f) == set(FACTS), set(f) ^ set(FACTS)
    return f


def post_of(recipe, view, image, equipment_images):
    """One recipe as the series see it: the view (services/recipe_v2/view.page), its dish image, the equipment
    images by id (routes/_shared.equipment_image, which reads the chosen style) and the recipe's own facts."""
    return {'id': recipe.id, 'view': view, 'image': image, 'eq': equipment_images, 'heat_source': recipe.heat_source,
            'protein': recipe.protein_type, 'cuisine': recipe.cuisine,
            'dinner': social_week.WEEK_MEAL in recipe.meal_types_list}


def _protein_label(ingredient):
    """The protein label a pantry ingredient stands for, as derive.main_protein labels a line, or None."""
    name = (ingredient.name or '').lower()
    if ingredient.main_category in ANIMAL:
        if any(word in name for word in ACCENT):
            return None
        sub = (ingredient.sub_category or '').lower()
        return next((lab for s, word, lab in FISH_NAMES if s == sub and word in name), None) or MEAT_LABELS.get(sub, 'Other')
    return next((lab for word, lab in OTHER_PROTEINS if word in name), None)


def shared_ingredient(posts, protein):
    """What to make with [ingredient]: the ingredient the dinners share. The tiles that are this protein (the
    pantry item's category, as derive.main_protein reads it), the name to ask with (the item's shortest name when
    the dinners buy the same one, else the protein: "chicken thighs" or "chicken") and its symbol."""
    tiles = {p['id']: social._ingredients(p['view'])[0] for p in posts}
    keys_all = {t['key'] for ts in tiles.values() for t in ts if t['key']}  # a pantry id, or a name that matches none
    rows = db.session.execute(db.select(Ingredient).where(Ingredient.food_id.in_(keys_all))).scalars().all() if keys_all else []
    keys = {i.food_id for i in rows if _protein_label(i) == protein}
    per_post = {pid: {t['key'] for t in ts if t['key'] in keys} for pid, ts in tiles.items()}
    common = set.intersection(*per_post.values()) if per_post else set()
    name = (protein or '').lower()
    if len(common) == 1:
        key = next(iter(common))
        name = min((t['name'] for ts in tiles.values() for t in ts if t['key'] == key), key=len)
    symbol = next((t['img'] for ts in tiles.values() for t in ts if t['key'] in (common or keys) and t['img']), None)
    return {'keys': keys, 'name': name, 'symbol': symbol}


def shared_trio(posts):
    """3 ingredients, 3 dinners: the ingredients the dinners share (buy keys, staples left out), the names and the
    symbols of the first SHARED_MIN, a protein first; chicken breast and thigh count as one (merge_key)."""
    tiles = {p['id']: social._ingredients(p['view'])[0] for p in posts}
    keys_all = {t['key'] for ts in tiles.values() for t in ts if t['key']}
    rows = db.session.execute(db.select(Ingredient).where(Ingredient.food_id.in_(keys_all))).scalars().all() if keys_all else []
    label = {i.food_id: _protein_label(i) for i in rows}
    merged = {pid: {merge_key(t['key'], label.get(t['key'])) for t in ts} for pid, ts in tiles.items()}
    common = set.intersection(*merged.values()) if merged else set()
    keys = {t['key'] for ts in tiles.values() for t in ts if merge_key(t['key'], label.get(t['key'])) in common}
    by_key = {}
    for ts in tiles.values():
        for t in ts:
            if t['key'] in keys:
                m = merge_key(t['key'], label.get(t['key']))
                # A merged ingredient is named by what it is ("chicken": one dinner has thighs, one breast)
                name = label[t['key']].lower() if m != t['key'] else t['name']
                if m not in by_key or len(name) < len(by_key[m]['name']):
                    by_key[m] = {'name': name, 'img': t['img'], 'protein': bool(label.get(t['key']))}
    chosen = sorted(by_key.values(), key=lambda x: (not x['protein'], x['name'].lower()))[:SHARED_MIN]
    return {'keys': keys, 'names': [c['name'] for c in chosen], 'symbols': chosen}


def merge_key(key, protein):
    """What makes two things to buy the same ingredient for the shared count: chicken breast and chicken thigh are
    both chicken; everything else is its own pantry item (or its name)."""
    return 'protein:Chicken' if protein == 'Chicken' else key


def slides(slug, posts, size, n, hook_group=None, cta_group=None, code=None, hook_text=None, cta_text=None):
    """The slides of a series post, built from its card's slide kinds, with the hook and CTA chosen:
    (slides, facts, hook group, hook text, cta). posts are post_of() dicts, as many as the series takes. hook_text
    and cta_text are an admin's words to try on real recipes (the route lets only an admin pass them): the groups
    are then 'preview'."""
    card = SERIES[slug]
    ids = [p['id'] for p in posts]
    sd = seed(slug, n, ids)
    r = posts[0]
    v = r['view']
    address = social.address(size, code)
    views, images = [p['view'] for p in posts], [p['image'] for p in posts]
    tiles, staples = social._ingredients(v)

    # What the post is about, by how many dinners it has: a shared ingredient (or three), a cuisine, or one dish
    shared = days = shop = shop_staples = None
    if len(posts) > 1:
        if card['filter'] == 'cuisine':
            labels = social_week.WEEK_DAYS[:len(posts)]
        else:
            labels = [f'Dinner {i + 1}' for i in range(len(posts))]
        days = social_week.days_of(views, images, labels)
        shop, shop_staples = social_week.shopping(days, views)
    if card['filter'] == 'got':
        shared = shared_ingredient(posts, r['protein'])
        f = facts(posts, n, count=len(shop), ingredient=shared['name'], series=card['name'].format(ingredient=shared['name']))
    elif card['filter'] == 'three3':
        shared = shared_trio(posts)
        names = ', '.join(shared['names'])
        f = facts(posts, n, count=len(shop), ingredients=names, series=card['name'])
    elif card['filter'] == 'cuisine':
        cuisine = r['cuisine'] or 'the week'
        f = facts(posts, n, count=len(shop), cuisine=cuisine, series=card['name'].format(cuisine=cuisine))
    elif len(posts) > 1:
        f = facts(posts, n, count=len(shop), series=card['name'])
    else:
        f = facts(posts, n, series=card['name'])
    label = f"{f['series']} #{n}"
    if hook_text:
        group, text = 'preview', hook_text
    else:
        group, text = hook_for(hook_group, f, sd, slug)
    if cta_text:
        call = {'group': 'preview', 'text': cta_text}
    else:
        call = (cta(cta_group, f, size, address, sd, card['noun'], slug)
                or cta(card['cta'], f, size, address, sd, card['noun'], slug))

    out = []
    for kind in card['slides']:
        if kind == 'cover':
            out.append({'kind': 'cover', 'eyebrow': label, 'title': text, 'name': v['title'], 'image': r['image'],
                        'tiles': tiles, 'symbols': [t for t in tiles if t['img']][:social.COVER_SYMBOLS],
                        'total': social.clock(f['total']) if f['total'] else None, 'count': len(tiles), 'parts': v['parts']})
        elif kind == 'got_cover':
            out.append({'kind': 'got_cover', 'eyebrow': label, 'title': text, 'symbol': shared['symbol'],
                        'ingredient': shared['name'], 'dishes': images, 'count': len(posts)})
        elif kind == 'trio_cover':
            out.append({'kind': 'trio_cover', 'eyebrow': label, 'title': text, 'symbols': shared['symbols'],
                        'dishes': images, 'count': len(posts)})
        elif kind == 'week_cover':
            cover = social_week.week_slides(views, images, size, eyebrow=label, title=text, cta=call,
                                            labels=[d['day'] for d in days])[0]
            grams = [d['protein'] for d in days if d['protein']]
            if card['filter'] == 'protein' and grams:  # the four-dinner protein post: the protein range, no time
                cover['each'] = f'{min(grams)}–{max(grams)} g protein per serving' if min(grams) != max(grams) \
                    else f'{grams[0]} g protein per serving'
            out.append(cover)
        elif kind == 'days':
            for d in days:
                keep = [t for t in d['tiles'] if not shared or t['key'] not in shared['keys']]
                plus = None
                if shared and len(keep) < len(d['tiles']):
                    plus = f"Plus the {shared['name']}." if 'name' in shared else f"Plus {', '.join(shared['names'])}."
                day = f"{d['day']} · {d['protein']} g protein" if card['filter'] == 'protein' and d['protein'] else d['day']
                out.append({'kind': 'day', **d, 'day': day, 'tiles': keep, 'many': len(keep) > social_week.DAY_MANY, 'note': plus,
                            'cols': max(5, social.columns(len(keep), size, room=social_week.DAY_ROOM_MANY
                                                          if len(keep) > social_week.DAY_MANY else social_week.DAY_ROOM))})
        elif kind == 'shop':
            title = f'One list for all {len(posts)}' if shared else 'The shopping list'
            out += social.shop_slides(shop, shop_staples, size, title)
        elif kind == 'grid':
            grid = social.recipe_slides(v, 'grid', r['image'], size, hook=text, cta=call)[:-1]
            grid[0]['eyebrow'] = label
            out += grid
        elif kind in GUESS_KINDS:
            # The points game: the same pictures in the same places on the first three, then the dish; the score
            # and the five-part bar sit in the same place, so a swipe reads as a countdown. The first slide's score
            # line is the hook (its words after the points)
            _, points, line, nxt = next(g for g in GUESS if g[0] == kind)
            if kind == 'guess_pictures':
                line = text[2:] if text.startswith(f'{points} ') else text
            shown = [{**t, 'amount': None} for t in tiles] if kind == 'guess_names' else tiles
            # The same columns on all three picture slides, as many as keep the names readable beside the score
            out.append({'kind': kind, 'eyebrow': label, 'points': points, 'line': line, 'next': nxt,
                        'tiles': shown, 'labels': kind != 'guess_pictures', 'image': r['image'],
                        'cols': max(4, social.columns(len(tiles), size, room=social.GUESS_ROOM))})
        elif kind == 'answer':
            out.append({**social.end_slide('', call, images), 'kind': 'answer', 'eyebrow': 'The answer',
                        'dish': f['dish']})
        elif kind == 'airfryer':
            out.append(social.airfryer_slide(v, r['eq']))
        elif kind == 'numbers':
            out.append(social.numbers_slide(v, 'Per serving'))
        elif kind == 'delta':
            delta = social.delta_slide(v)  # only the small ones; a big one leaves no slide
            if delta:
                out.append(delta)
        elif kind == 'steps':
            out += social.steps_slides(v, size)
        elif kind == 'wash':
            out.append(social.wash_slide(v, r['eq']))
        elif kind == 'ingredients':
            out.append({'kind': 'ingredients', 'title': 'What you need', 'tiles': tiles, 'staples': staples,
                        'cols': social.columns(len(tiles), size)})
        elif kind == 'shop_split':
            out.append(social.shop_split_slide(v, size))
        elif kind == 'end':
            out.append(social.end_slide('', call, images))
        else:
            raise ValueError(f'{slug}.yaml: slide kind {kind!r} is not one of {", ".join(SLIDE_KINDS)}')
    return out, f, group, text, call


def plural(n, word):
    """'1 dish', '2 dishes'."""
    return f'{n} {word}' if n == 1 else f'{n} {word}{"es" if word.endswith(("s", "sh", "ch")) else "s"}'


def caption(slug, posts, f, text, call, size, code=None):
    """A first draft of a series post's text: what it shows in a sentence, the CTA, the address and the hashtags.
    Minutes only when they may be said (the time facts)."""
    card = SERIES[slug]
    kind = card['filter']
    where = social.address(size, code)
    titles = ', '.join(p['view']['title'] for p in posts)
    v = posts[0]['view']
    in_time = f" in {f['total']} minutes" if f['total'] else ''
    work = f", {f['active']} minutes of work" if f['active'] else ''
    if kind == 'got':
        what = f"What to make with {f['ingredient']}: {titles}. One shopping list for all {len(posts)}: {f['count']} things."
    elif kind == 'three3':
        what = f"{f['ingredients']}: {titles}. One shopping list for all {len(posts)}: {f['count']} things."
    elif kind == 'cuisine':
        what = f"{len(posts)} {f['cuisine']} weeknights: {titles}. Buy {f['count']} things for the whole week."
    elif kind == 'protein' and len(posts) > 1:
        each = f", {f['protein_min']} g protein or more per serving each" if f['protein_min'] else ''
        what = f"{len(posts)} high-protein dinners: {titles}{each}. One shopping list: {f['count']} things."
    elif kind == 'protein':
        what = f"{v['title']}: {f['protein']} g protein and {f['kcal']} kcal per serving."
    elif kind == 'onepot':
        pot = f" in one {f['vessel']}" if f['vessel'] else ''
        what = f"{v['title']}, cooked{pot}, with {plural(f['vessels'], 'dish')} to wash{work}."
    elif kind == 'under20':
        what = f"{v['title']}{work or ': under 20 minutes of work'}{in_time}."
    elif kind == 'only6':
        what = f"{v['title']}: {plural(f['count'], 'thing')} to buy{work}{in_time}."
    elif kind == 'guess':
        what = (f"One {f['meal']}, {f['symbols']} things to buy. 5 points if you know it from the pictures alone, 4 with "
                "the names, 3 with the amounts, 2 from the dish. The answer is on the last slide.")
    else:
        what = f"{v['title']}: the whole dinner in the air fryer{work}{in_time}."
    lines = [what, '', call['text']]
    if call['group'] != 'site':
        lines += [f'Every step with timers: {where}']
    tag = ''.join(c for c in (f.get('ingredient') or f.get('cuisine') or '').lower() if c.isalnum())
    return '\n'.join(lines + ['', card['hashtags'].format(tag=tag or 'dinner')])


def views_used(slides):
    """The slide kinds of a post, for the post log: 'cover airfryer ingredients timebar shop_split end'."""
    return ' '.join(s['kind'] for s in slides)


# Picking

def used_in(slug):
    """{recipe id: the day it last went up in this series}, from the post log, both platforms."""
    last = {}
    posts = db.session.execute(db.select(SocialPost.recipe_ids, SocialPost.recipe_id, SocialPost.posted_on)
                               .where(SocialPost.series == slug)).all()
    for ids, one, day in posts:
        for i in [int(x) for x in (ids or '').split(',') if x.strip().isdigit()] or ([one] if one else []):
            if i not in last or day > last[i]:
                last[i] = day
    return last


def next_n(slug):
    """The number of the next post in a series: one above the highest logged, on either platform."""
    top = db.session.execute(db.select(func.max(SocialPost.series_n)).where(SocialPost.series == slug)).scalar()
    return (top or 0) + 1


def candidates(slug):
    """The recipes a series may draw from: approved, with a dish image, not baby food, one per dish, a dinner (the
    meal type, as the week takes them: social_week.WEEK_MEAL) unless the card's filter is 'guess', within the filter
    (FILTERS). {id: {'protein', 'cuisine', 'kcal', 'buy', 'dinner'}}."""
    kind = SERIES[slug]['filter']
    q = db.select(Recipe.id, FAMILY, Recipe.base_recipe_id).where(
        Recipe.status == 'approved', Recipe.schema_version == 2, Recipe.image_filename.isnot(None),
        Recipe.age_from_months.is_(None),
        Recipe.id.not_in(db.select(RecipeMealType.recipe_id).where(RecipeMealType.meal_type == social_week.NOT_FOR_WEEK)),
    ).order_by(Recipe.id)
    dinners = db.select(RecipeMealType.recipe_id).where(RecipeMealType.meal_type == social_week.WEEK_MEAL)
    if kind != 'guess':
        q = q.where(Recipe.id.in_(dinners))
    if kind == 'airfryer':
        q = q.where(Recipe.heat_source == 'airfryer')
    elif kind == 'protein':
        q = q.where(Recipe.total_protein >= PROTEIN_G * func.coalesce(Recipe.base_servings, 4))
    elif kind == 'onepot':
        q = q.where(Recipe.heat_source != 'airfryer')
    elif kind == 'under20':
        work = db.select(RecipeStep.recipe_id).group_by(RecipeStep.recipe_id).having(
            func.sum(RecipeStep.active_minutes) < social.SAY_ACTIVE_UNDER)
        q = q.where(Recipe.id.in_(work))
    elif kind == 'got':
        q = q.where(Recipe.protein_type.isnot(None), Recipe.protein_type.not_in(NOT_AN_INGREDIENT))
    elif kind == 'cuisine':
        q = q.where(Recipe.cuisine.isnot(None), Recipe.cuisine != '')
    ids = one_per_dish(db.session.execute(q).all())
    if kind == 'onepot' and ids:
        # Exactly one vessel the food is cooked in, over all the steps (social.COOK_VESSELS)
        steps = db.session.execute(db.select(RecipeStep.recipe_id, RecipeStep.equipment)
                                   .where(RecipeStep.recipe_id.in_(ids))).all()
        cooking = {}
        for rid, equipment in steps:
            cooking.setdefault(rid, set()).update(set(equipment or []) & social.COOK_VESSELS)
        ids = [i for i in ids if len(cooking.get(i, ())) == 1]
    buy = social_week.buy_sets(ids) if kind in ('got', 'cuisine', 'only6', 'three3', 'protein', 'guess') and ids else {}
    if kind == 'only6':
        ids = [i for i in ids if 0 < len(buy.get(i, ())) <= BUY_MAX]
    if kind == 'guess':  # the three with more things to buy than fit the pictures are left out
        ids = [i for i in ids if 0 < len(buy.get(i, ())) <= GUESS_MAX]
    if not ids:
        return {}
    is_dinner = set(db.session.execute(dinners.where(RecipeMealType.recipe_id.in_(ids))).scalars())
    rows = db.session.execute(db.select(Recipe.id, Recipe.protein_type, Recipe.cuisine, Recipe.total_calories,
                                        Recipe.base_servings, Recipe.total_protein).where(Recipe.id.in_(ids))).all()
    return {i: {'protein': protein, 'cuisine': cuisine, 'kcal': (kcal or 0) / (servings or 4),
                'protein_g': (grams or 0) / (servings or 4), 'buy': frozenset(buy.get(i, ())), 'dinner': i in is_dinner}
            for i, protein, cuisine, kcal, servings, grams in rows}


def trios(c, among=None):
    """3 ingredients, 3 dinners: every set of three dinners from candidates('three3') (or the ids in among) that
    share at least SHARED_MIN things to buy (staples left out), one of them a protein, with chicken breast and thigh
    as one ingredient, and that are three different dishes: no two share more than social_week.WEEK_SAME of what
    they buy (the week's rule, so three gyros are not a set). [(ids, shared), ...], the most shared first."""
    ids = list(c)
    rows = db.session.execute(db.select(Ingredient).where(Ingredient.id.in_(
        {k for i in ids for k in c[i]['buy'] if isinstance(k, int)}))).scalars().all()
    label = {i.id: _protein_label(i) for i in rows}
    merged = {i: {merge_key(k, label.get(k)) for k in c[i]['buy']} for i in ids}
    out = []
    for three in itertools.combinations(sorted(among if among is not None else ids), 3):
        common = set.intersection(*(merged[i] for i in three))
        if len(common) < SHARED_MIN or not any(k == 'protein:Chicken' or label.get(k) for k in common):
            continue
        if any(len(c[a]['buy'] & c[b]['buy']) / len(c[a]['buy'] | c[b]['buy']) > social_week.WEEK_SAME
               for a, b in itertools.combinations(three, 2)):
            continue
        out.append((list(three), len(common)))
    return sorted(out, key=lambda x: (-x[1], x[0]))


def trio(c, eligible, last):
    """The next set for 3 ingredients, 3 dinners: the one least recently seen, then the one sharing most; [] when
    there is none."""
    sets = trios(c, eligible)
    if not sets:
        return []
    return min(sets, key=lambda x: (max(last.get(i, datetime.date.min) for i in x[0]), -x[1], x[0]))[0]


def pick(slug, today=None):
    """The recipe ids for the next post of a series, or [] when the series has run out (then it pauses)."""
    today = today or datetime.date.today()
    c = candidates(slug)
    last = used_in(slug)
    since = today - datetime.timedelta(days=ONCE_A_WEEK)
    eligible = [i for i in c if i not in last or last[i] < since]
    card = SERIES[slug]
    kind = card['filter']

    def order(i):
        return (last.get(i, datetime.date.min), c[i]['kcal'] if kind == 'protein' else 0, i)
    eligible.sort(key=order)
    if card['count'] == 1:
        return eligible[:1]
    if kind == 'three3':
        return trio(c, eligible, last)
    if kind in ('got', 'cuisine'):
        key = 'protein' if kind == 'got' else 'cuisine'
        by, group_last = {}, {}
        for i in eligible:
            by.setdefault(c[i][key], []).append(i)
        for i in c:
            group_last[c[i][key]] = max(group_last.get(c[i][key], datetime.date.min), last.get(i, datetime.date.min))
        groups = [g for g, ids in by.items() if len(ids) >= card['count']]
        if not groups:
            return []
        # The group least recently seen in the series; among the never seen, the biggest
        group = min(groups, key=lambda g: (group_last[g], -len(by[g]), g))
        eligible = by[group]
    if len(eligible) < card['count']:
        return []
    if kind in ('cuisine', 'protein'):
        # Varied as the week is (proteins, no near-copies, fewest things to buy), else the first in order
        varied = social_week.pick({i: {'protein': (c[i]['protein'] or 'none').lower(), 'buy': c[i]['buy']}
                                   for i in eligible if c[i]['buy']}, card['count'])
        if varied:
            return varied
    return eligible[:card['count']]
