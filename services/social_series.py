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
import os
import random
import re

import yaml
from sqlalchemy import func

from database.models import Ingredient, Recipe, RecipeMealType, SocialPost, db
from services import social, social_week
from services.recipe_library import FAMILY, one_per_dish
from services.recipe_v2.derive import ACCENT, ANIMAL, FISH_NAMES, MEAT_LABELS, OTHER_PROTEINS, VESSELS

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CARDS = os.path.join(ROOT, 'data', 'social', 'series')
SHARED = os.path.join(ROOT, 'data', 'social', 'hooks.yaml')

PROTEIN_G = 35      # High-protein dinners: at least this much protein per serving
WASH_MAX = 2        # Dishes to wash: at most this many vessels (derive.cleanup_factor 1)
ONCE_A_WEEK = 7     # days a recipe stays out of a series after a post
NOT_AN_INGREDIENT = ('Vegetarian', 'Other')  # protein labels Got [ingredient]? cannot ask for
HOOK_WORDS = 8      # a hook is at most this many words, filled in
STATUSES = ('active', 'paused', 'retired')
# The slide kinds a card may list, built in slides(): a kind may stand for several slides (days, shop, grid)
SLIDE_KINDS = ('cover', 'got_cover', 'week_cover', 'airfryer', 'numbers', 'timebar', 'delta', 'delta_or_timebar',
               'timers', 'wash', 'ingredients', 'shop_split', 'days', 'shop', 'grid', 'end')
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
    'cuisine': 'the cuisine (the week)',
}
# The facts every post has (never None), so a phrasing may use them without needing them; the rest must be needed
ALWAYS = ('n', 'series', 'dish', 'title', 'dishes', 'count', 'symbols', 'doer', 'doer_cap', 'vessels')


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
            'kcal': 425, 'ingredient': 'chicken thighs', 'ingredient_cap': 'Chicken thighs', 'cuisine': 'Middle Eastern'}


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
        for kind in card['slides']:
            if kind not in SLIDE_KINDS:
                problems.append(f'{where}: slide kind {kind!r} is not one of {", ".join(SLIDE_KINDS)}')
        if not card['slides'] or card['slides'][-1] != 'end':
            problems.append(f'{where}: the slides must end with end')
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


def cta(group, facts, size, address, seed, noun='dinner'):
    """The last slide's call to action: {'group', 'text'}, or None when the group is not one."""
    if group not in CTAS:
        return None
    if group == 'bio' and size != 'ig':
        group = 'site'
    choices = CTAS[group]
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


def facts(posts, n=None, count=None, ingredient=None, cuisine=None, series=None):
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
    nutrition = v['nutrition'] or {}
    f = {'n': n, 'series': series, 'dish': short_title(v['title']), 'title': v['title'], 'dishes': len(posts),
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
            'protein': recipe.protein_type, 'cuisine': recipe.cuisine}


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

    # What the post is about, by how many dinners it has
    shared = days = shop = None
    if card['filter'] == 'got':
        shared = shared_ingredient(posts, r['protein'])
        days = social_week.days_of(views, images, [f'Dinner {i + 1}' for i in range(len(posts))])
        shop, shop_staples = social_week.shopping(days, views)
        f = facts(posts, n, count=len(shop), ingredient=shared['name'], series=card['name'].format(ingredient=shared['name']))
    elif len(posts) > 1:
        cuisine = r['cuisine'] or 'the week'
        days = social_week.days_of(views, images)
        shop, shop_staples = social_week.shopping(days, views)
        f = facts(posts, n, count=len(shop), cuisine=cuisine, series=card['name'].format(cuisine=cuisine))
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
        call = cta(cta_group, f, size, address, sd, card['noun']) or cta(card['cta'], f, size, address, sd, card['noun'])

    out = []
    for kind in card['slides']:
        if kind == 'cover':
            out.append({'kind': 'cover', 'eyebrow': label, 'title': text, 'name': v['title'], 'image': r['image'],
                        'tiles': tiles, 'total': social.clock(f['total']) if f['total'] else None,
                        'count': len(tiles), 'parts': v['parts']})
        elif kind == 'got_cover':
            out.append({'kind': 'got_cover', 'eyebrow': label, 'title': text, 'symbol': shared['symbol'],
                        'ingredient': shared['name'], 'dishes': images, 'count': len(posts)})
        elif kind == 'week_cover':
            out.append(social_week.week_slides(views, images, size, eyebrow=label, title=text, cta=call)[0])
        elif kind == 'days':
            for d in days:
                keep = [t for t in d['tiles'] if not shared or t['key'] not in shared['keys']]
                out.append({'kind': 'day', **d, 'tiles': keep, 'many': len(keep) > social_week.DAY_MANY,
                            'note': f"Plus the {shared['name']}." if shared and len(keep) < len(d['tiles']) else None,
                            'cols': max(5, social.columns(len(keep), size, room=social_week.DAY_ROOM_MANY
                                                          if len(keep) > social_week.DAY_MANY else social_week.DAY_ROOM))})
        elif kind == 'shop':
            title = f'One list for all {len(posts)}' if shared else 'The shopping list'
            out += social.shop_slides(shop, shop_staples, size, title)
        elif kind == 'grid':
            grid = social.recipe_slides(v, 'grid', r['image'], size, hook=text, cta=call)[:-1]
            grid[0]['eyebrow'] = label
            out += grid
        elif kind == 'airfryer':
            out.append(social.airfryer_slide(v, r['eq']))
        elif kind == 'numbers':
            out.append(social.numbers_slide(v, 'Per serving'))
        elif kind == 'timebar':
            out.append(social.timebar_slide(v, r['heat_source']))
        elif kind == 'delta':
            out.append(social.delta_slide(v) or social.timebar_slide(v, r['heat_source']))
        elif kind == 'delta_or_timebar':
            out.append(social.delta_slide(v) or social.timebar_slide(v, r['heat_source']))
        elif kind == 'timers':
            out.append(social.timers_slide(v))
        elif kind == 'wash':
            out.append(social.wash_slide(v, r['eq']))
        elif kind == 'ingredients':
            out.append({'kind': 'ingredients', 'title': 'What you need', 'tiles': tiles, 'staples': staples,
                        'cols': social.columns(len(tiles), size)})
        elif kind == 'shop_split':
            out.append(social.shop_split_slide(v, size))
        elif kind == 'end':
            out.append(social.end_slide('', call))
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
    where = social.address(size, code)
    titles = ', '.join(p['view']['title'] for p in posts)
    v = posts[0]['view']
    in_time = f" in {f['total']} minutes" if f['total'] else ''
    work = f", {f['active']} minutes of work" if f['active'] else ''
    if card['filter'] == 'got':
        what = f"What to make with {f['ingredient']}: {titles}. One shopping list for all {len(posts)}: {f['count']} things."
    elif len(posts) > 1:
        what = f"{len(posts)} {f['cuisine']} weeknights: {titles}. Buy {f['count']} things for the whole week."
    elif card['filter'] == 'protein':
        table = f', on the table{in_time}' if in_time else ''
        what = f"{v['title']}: {f['protein']} g protein and {f['kcal']} kcal per serving{table}."
    elif card['filter'] == 'dishes':
        what = f"{v['title']}, with {plural(f['vessels'], 'dish')} to wash{work}."
    elif card['filter'] == 'all':
        what = f"{f['symbols']} ingredients, one dinner. Guess it before the third picture gives it away."
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
    """The recipes a series may draw from: approved, with a dish image, a dinner (the meal type, as the week takes
    them: social_week.WEEK_MEAL) and not baby food, one per dish, within the card's filter.
    {id: {'protein', 'cuisine', 'kcal', 'buy'}}."""
    kind = SERIES[slug]['filter']
    q = db.select(Recipe.id, FAMILY, Recipe.base_recipe_id).where(
        Recipe.status == 'approved', Recipe.schema_version == 2, Recipe.image_filename.isnot(None),
        Recipe.age_from_months.is_(None),
        Recipe.id.in_(db.select(RecipeMealType.recipe_id).where(RecipeMealType.meal_type == social_week.WEEK_MEAL)),
        Recipe.id.not_in(db.select(RecipeMealType.recipe_id).where(RecipeMealType.meal_type == social_week.NOT_FOR_WEEK)),
    ).order_by(Recipe.id)
    if kind == 'airfryer':
        q = q.where(Recipe.heat_source == 'airfryer')
    elif kind == 'protein':
        q = q.where(Recipe.total_protein >= PROTEIN_G * func.coalesce(Recipe.base_servings, 4))
    elif kind == 'dishes':
        q = q.where(Recipe.cleanup_factor == 1)
    elif kind == 'got':
        q = q.where(Recipe.protein_type.isnot(None), Recipe.protein_type.not_in(NOT_AN_INGREDIENT))
    elif kind == 'cuisine':
        q = q.where(Recipe.cuisine.isnot(None), Recipe.cuisine != '')
    ids = one_per_dish(db.session.execute(q).all())
    if not ids:
        return {}
    rows = db.session.execute(db.select(Recipe.id, Recipe.protein_type, Recipe.cuisine, Recipe.total_calories,
                                        Recipe.base_servings).where(Recipe.id.in_(ids))).all()
    buy = social_week.buy_sets(ids) if kind in ('got', 'cuisine') else {}
    return {i: {'protein': protein, 'cuisine': cuisine, 'kcal': (kcal or 0) / (servings or 4),
                'buy': frozenset(buy.get(i, ()))} for i, protein, cuisine, kcal, servings in rows}


def pick(slug, today=None):
    """The recipe ids for the next post of a series, or [] when the series has run out (then it pauses)."""
    today = today or datetime.date.today()
    c = candidates(slug)
    last = used_in(slug)
    since = today - datetime.timedelta(days=ONCE_A_WEEK)
    eligible = [i for i in c if i not in last or last[i] < since]
    card = SERIES[slug]

    def order(i):
        return (last.get(i, datetime.date.min), c[i]['kcal'] if card['filter'] == 'protein' else 0, i)
    eligible.sort(key=order)
    if card['count'] == 1:
        return eligible[:1]
    key = 'protein' if card['filter'] == 'got' else 'cuisine'
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
    ids = by[group]
    if card['filter'] == 'cuisine':
        varied = social_week.pick({i: {'protein': (c[i]['protein'] or 'none').lower(), 'buy': c[i]['buy']}
                                   for i in ids if c[i]['buy']}, card['count'])
        if varied:
            return varied
    return ids[:card['count']]
