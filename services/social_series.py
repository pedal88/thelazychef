"""The post series for TikTok and Instagram (docs/SOCIAL.md "The series"): a fixed promise repeated with a new dish
each time, so there is a reason to follow and the agent can make every post from the database.

A series is a slug in SERIES with its slide sequence, built from the recipe page's view and the slide kinds in
services/social.py. A post of a series has a number (#7), a hook (the words on the first slide, from a group of
phrasings that state the post's own numbers) and a CTA (the last slide: follow, save, send, ask, the site or the
bio). The phrasing is drawn with a seed from the series, number and recipes, so a post renders the same every time.

Picking: only approved recipes with a dish image, within the series' filter, a recipe at most once in ONCE_A_WEEK
days per series (the post log, SocialPost.series and recipe_ids), never used first, then the longest ago; High-protein
puts the lighter dishes first.
"""
import datetime
import random

from sqlalchemy import func

from database.models import Ingredient, Recipe, SocialPost, db
from services import social, social_week
from services.recipe_library import FAMILY, one_per_dish
from services.recipe_v2.derive import ACCENT, ANIMAL, FISH_NAMES, MEAT_LABELS, OTHER_PROTEINS, VESSELS

PROTEIN_G = 35      # High-protein dinners: at least this much protein per serving
WASH_MAX = 2        # Dishes to wash: at most this many vessels (derive.cleanup_factor 1)
GOT_RECIPES = 3     # Got [ingredient]?: dinners per post
ONCE_A_WEEK = 7     # days a recipe stays out of a series after a post
NOT_AN_INGREDIENT = ('Vegetarian', 'Other')  # protein labels Got [ingredient]? cannot ask for

SERIES = {
    'airfryer': {'name': 'Air fryer dinners', 'noun': 'air fryer dinner', 'count': 1, 'hook': 'lazy', 'cta': 'follow',
                 'hashtags': '#airfryer #airfryerrecipes #easydinner #dinnerideas #weeknightdinner',
                 'hooks': {'lazy': [('Air fryer #{n}: {active} min of work', ('n', 'active')),
                                    ('{active} min of work. Then the air fryer.', ('active',)),
                                    ('You: {active} min. Air fryer: {idle} min.', ('active', 'idle'))]}},
    'got': {'name': 'Got {ingredient}?', 'noun': 'dinner idea', 'count': GOT_RECIPES, 'hook': 'search', 'cta': 'save',
            'hashtags': '#dinnerideas #whatsfordinner #easyrecipes #mealprep #{tag}'},
    'protein': {'name': 'High-protein dinners', 'noun': 'high-protein dinner', 'count': 1, 'hook': 'number',
                'cta': 'follow', 'hashtags': '#highprotein #proteindinner #healthydinner #dinnerideas #easyrecipes',
                'hooks': {'number': [('{protein} g protein. {kcal} kcal.', ('protein', 'kcal')),
                                     ('{protein} g of protein in {total} minutes.', ('protein', 'total')),
                                     ('{protein} g protein, {count} things to buy.', ('protein', 'count'))]}},
    'dishes': {'name': 'Dishes to wash', 'noun': 'one-pot dinner', 'count': 1, 'hook': 'number', 'cta': 'send',
               'hashtags': '#onepot #onepan #easydinner #lessdishes #dinnerideas',
               'hooks': {'number': [('Dishes to wash: {vessels}', ('vessels',)),
                                    ('{vessels} dishes to wash. {active} min of work.', ('vessels', 'active')),
                                    ('One dinner, {vessels} dishes to wash.', ('vessels',))]}},
    'guess': {'name': 'Guess the dinner', 'noun': 'dinner to guess', 'count': 1, 'hook': 'guess', 'cta': 'ask',
              'hashtags': social.HASHTAGS['grid']},
    'cuisine': {'name': '5 weeknights of {cuisine}', 'noun': 'weeknight dinner', 'count': len(social_week.WEEK_DAYS),
                'hook': 'number', 'cta': 'save', 'hashtags': '#mealplan #weeknightdinner #{tag} #dinnerideas #easyrecipes',
                'hooks': {'number': [('5 {cuisine} dinners. {count} things to buy.', ('cuisine', 'count')),
                                     ('A week of {cuisine}. {count} things.', ('cuisine', 'count')),
                                     ('{cuisine} all week. {count} things, one shop.', ('cuisine', 'count'))]}},
}

# The hook groups (playbook.md): (phrasing, the facts it needs). Every phrasing is at most eight words and every
# number in it is the post's own; a phrasing whose facts are missing is not drawn. A series may have its own list for
# a group (SERIES[slug]['hooks']).
HOOKS = {
    'number': [('{count} things to buy. {total} minutes.', ('count', 'total')),
               ('{vessels} dishes to wash. {active} min of work.', ('vessels', 'active')),
               ('{protein} g protein. {kcal} kcal.', ('protein', 'kcal')),
               ('{dishes} dinners. {count} things to buy.', ('many', 'count')),
               ('{total} minutes, {count} things, dinner.', ('total', 'count'))],
    'lazy': [("{active} minutes of work. That's it.", ('active',)),
             ('You: {active} min. {doer_cap}: {idle} min.', ('active', 'idle')),
             ('You do {active} minutes. Dinner does the rest.', ('active',))],
    'search': [('Got {ingredient}? {dishes} dinners.', ('ingredient', 'many')),
               ('{ingredient_cap} for dinner? {dishes} ideas.', ('ingredient', 'many')),
               ('What to make with {ingredient}: {dishes} dinners', ('ingredient', 'many')),
               ('Got {ingredient}? Dinner in {total} minutes.', ('ingredient', 'total'))],
    'guess': [('Guess the dinner from {symbols} symbols', ('symbols',)),
              ('Can you guess the dinner?', ()),
              ('{symbols} symbols. One dinner. Guess it.', ('symbols',))],
    # Used sparingly; each is true only under its condition (few, quick, one_two in facts())
    'contrast': [('Not 30 ingredients. Just {count}.', ('few',)),
                 ('Not an hour. {total} minutes.', ('quick',)),
                 ('Not a sink full. {vessels} dishes to wash.', ('one_two',)),
                 ('No takeaway. {total} minutes, {count} things.', ('quick', 'count'))],
}

# The CTA groups and what they ask; "ask" has a question for one dish and one for several, "site" carries the
# address and "bio" is Instagram only (TikTok gets "site" instead)
CTAS = {
    'follow': ["Follow for tomorrow's {noun}", 'Follow for the next {noun}', 'A new {noun} every day. Follow.'],
    'save': ["Save this for Sunday's shop", 'Save it for your next shop', 'Save this for a lazy weeknight'],
    'send': ['Send to the person you cook with', 'Send this to whoever cooks tonight', 'Send it to your flatmate'],
    'ask': {'one': ['Would you cook this tonight?', 'What would you add?'],
            'many': ['Which one would you cook first?', 'Which one is yours?']},
    'site': {'one': ['Every step with timers: {address}', 'The whole recipe, with timers: {address}'],
             'many': ['All {dishes} on one shopping list: {address}', 'Every recipe, with timers: {address}']},
    'bio': ['Shopping list: link in bio', 'The full recipe: link in bio'],
}
HOOK_WORDS = 8


def seed(slug, n, ids):
    """The seed a post's phrasings are drawn with: the same post draws the same words every time."""
    return f'{slug}:{n}:{",".join(str(i) for i in ids)}'


def hook(group, facts, seed, slug=None):
    """The words on the first slide for a hook group, or None when the group is not one (the caller falls back).
    A series' own phrasings for the group come first (SERIES[slug]['hooks'])."""
    if group not in HOOKS:
        return None
    phrasings = (SERIES.get(slug) or {}).get('hooks', {}).get(group) or HOOKS[group]
    fits = [text for text, needs in phrasings if all(facts.get(k) not in (None, False, '') for k in needs)]
    if not fits:
        return None
    return random.Random(seed + ':hook').choice(fits).format(**facts)


def hook_for(group, facts, seed, slug=None):
    """The hook for a series post: the group asked for when it has words for this post, else the series' own group,
    else a number."""
    for g in (group, SERIES[slug]['hook'] if slug else None, 'number'):
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


def facts(posts, n=None, count=None, ingredient=None, cuisine=None):
    """What the hooks can say about a post: posts are post_of() dicts; count overrides the things to buy (one list
    for several dinners). Every value is the post's own number."""
    v = posts[0]['view']
    tiles, _ = social._ingredients(v)
    total = max(p['view']['total_min'] for p in posts)
    active = min(max(p['view']['active_min'] for p in posts), total)
    vessels = len([e for e in v['equipment'] if e['id'] in VESSELS])
    nutrition = v['nutrition'] or {}
    f = {'n': n, 'dishes': len(posts), 'many': len(posts) > 1, 'count': len(tiles) if count is None else count,
         'symbols': len(tiles), 'total': total, 'active': active, 'idle': total - active,
         'doer': social.IDLE_BY.get(posts[0]['heat_source'], social.IDLE), 'vessels': vessels,
         'doer_cap': social.IDLE_BY.get(posts[0]['heat_source'], social.IDLE).capitalize(),
         'protein': nutrition.get('protein'), 'kcal': nutrition.get('kcal'), 'ingredient': ingredient,
         'ingredient_cap': ingredient[:1].upper() + ingredient[1:] if ingredient else None, 'cuisine': cuisine,
         'title': v['title']}
    f.update(few=f['count'] <= 15, quick=f['total'] <= 45, one_two=vessels <= WASH_MAX)
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
    """Got [ingredient]?: the ingredient the dinners share. The tiles that are this protein (the pantry item's
    category, as derive.main_protein reads it), the name to ask with (the item's shortest name when the dinners buy
    the same one, else the protein: "chicken thighs" or "chicken") and its symbol."""
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


def slides(slug, posts, size, n, hook_group=None, cta_group=None, code=None):
    """The slides of a series post, with the hook and CTA chosen: (slides, facts, hook group, hook text, cta).
    posts are post_of() dicts, as many as the series takes."""
    series = SERIES[slug]
    ids = [p['id'] for p in posts]
    sd = seed(slug, n, ids)
    r = posts[0]
    v = r['view']
    address = social.address(size, code)
    label = f"{series['name']} #{n}"
    tiles, staples = social._ingredients(v)
    ingredients = {'kind': 'ingredients', 'title': 'What you need', 'tiles': tiles, 'staples': staples,
                   'cols': social.columns(len(tiles), size)}
    delta_or_bar = social.delta_slide(v) or social.timebar_slide(v, r['heat_source'])

    if slug == 'got':
        shared = shared_ingredient(posts, r['protein'])
        days = social_week.days_of([p['view'] for p in posts], [p['image'] for p in posts],
                                   [f'Dinner {i + 1}' for i in range(len(posts))])
        shop, staples = social_week.shopping(days, [p['view'] for p in posts])
        f = facts(posts, n, count=len(shop), ingredient=shared['name'])
        label = f"{series['name'].format(ingredient=shared['name'])} #{n}"
        group, text = hook_for(hook_group, f, sd, slug)
        call = cta(cta_group, f, size, address, sd, series['noun']) or cta(series['cta'], f, size, address, sd, series['noun'])
        out = [{'kind': 'got_cover', 'eyebrow': label, 'title': text, 'symbol': shared['symbol'],
                'ingredient': shared['name'], 'dishes': [p['image'] for p in posts], 'count': len(posts)}]
        for d in days:
            rest = [t for t in d['tiles'] if t['key'] not in shared['keys']]
            out.append({'kind': 'day', **d, 'tiles': rest, 'many': len(rest) > social_week.DAY_MANY,
                        'note': f"Plus the {shared['name']}." if len(rest) < len(d['tiles']) else None,
                        'cols': max(5, social.columns(len(rest), size, room=social_week.DAY_ROOM_MANY
                                                      if len(rest) > social_week.DAY_MANY else social_week.DAY_ROOM))})
        out.append({'kind': 'shop', 'title': f'One list for all {len(posts)}', 'tiles': shop, 'staples': staples,
                    'cols': social.columns(len(shop), size)})
        out.append(social.end_slide('', call))
        return out, f, group, text, call

    if slug == 'cuisine':
        cuisine = r['cuisine'] or 'the week'
        views, images = [p['view'] for p in posts], [p['image'] for p in posts]
        count = len(social_week.shopping(social_week.days_of(views, images), views)[0])
        f = facts(posts, n, count=count, cuisine=cuisine)
        label = f"{series['name'].format(cuisine=cuisine)} #{n}"
        group, text = hook_for(hook_group, f, sd, slug)
        call = cta(cta_group, f, size, address, sd, series['noun']) or cta(series['cta'], f, size, address, sd, series['noun'])
        week = social_week.week_slides(views, images, size, eyebrow=label, title=text, cta=call)
        by_kind = {s['kind']: s for s in week}
        days = [s for s in week if s['kind'] == 'day']
        return [by_kind['week_cover'], *days, by_kind['shop'], by_kind['end']], f, group, text, call

    f = facts(posts, n)
    group, text = hook_for(hook_group, f, sd, slug)
    call = cta(cta_group, f, size, address, sd, series['noun']) or cta(series['cta'], f, size, address, sd, series['noun'])
    if slug == 'guess':
        out = social.recipe_slides(v, 'grid', r['image'], size, hook=text, cta=call)
        out[0]['eyebrow'] = label
        return out, f, group, text, call
    cover = {'kind': 'cover', 'eyebrow': label, 'title': text, 'name': v['title'], 'image': r['image'],
             'tiles': tiles, 'total': v['total'], 'count': len(tiles), 'parts': v['parts']}
    if slug == 'airfryer':
        out = [cover, social.airfryer_slide(v, r['eq']), ingredients, delta_or_bar,
               social.shop_split_slide(v, size), social.end_slide('', call)]
    elif slug == 'protein':
        out = [cover, social.numbers_slide(v, 'Per serving'), ingredients, social.timebar_slide(v, r['heat_source']),
               social.shop_split_slide(v, size), social.end_slide('', call)]
    else:  # dishes
        out = [cover, social.wash_slide(v, r['eq']), ingredients, delta_or_bar, social.timers_slide(v),
               social.end_slide('', call)]
    return out, f, group, text, call


def caption(slug, posts, f, text, call, size, code=None):
    """A first draft of a series post's text: what it shows in a sentence, the CTA, the address and the hashtags."""
    series = SERIES[slug]
    where = social.address(size, code)
    titles = ', '.join(p['view']['title'] for p in posts)
    v = posts[0]['view']
    if slug == 'got':
        what = f"Got {f['ingredient']}? {titles}. One shopping list for all {len(posts)}: {f['count']} things."
    elif slug == 'cuisine':
        what = f"Five {f['cuisine']} weeknights: {titles}. Buy {f['count']} things for the whole week."
    elif slug == 'protein':
        what = f"{v['title']}: {f['protein']} g protein and {f['kcal']} kcal per serving, on the table in {f['total']} minutes."
    elif slug == 'dishes':
        what = f"{v['title']}, with {f['vessels']} dishes to wash and {f['active']} minutes of work."
    elif slug == 'guess':
        what = f"{f['symbols']} ingredients, one dinner. Guess it before the third picture gives it away."
    else:
        what = f"{v['title']}: the whole dinner in the air fryer, {f['active']} minutes of work, {f['total']} start to table."
    lines = [what, '', call['text']]
    if call['group'] != 'site':
        lines += [f'Every step with timers: {where}']
    tag = ''.join(c for c in (f.get('ingredient') or f.get('cuisine') or '').lower() if c.isalnum())
    return '\n'.join(lines + ['', series['hashtags'].format(tag=tag or 'dinner')])


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
    """The recipes a series may draw from: approved, with a dish image, not baby food, one per dish, within the
    series' filter. {id: {'protein', 'cuisine', 'kcal', 'buy'}}."""
    q = db.select(Recipe.id, FAMILY, Recipe.base_recipe_id).where(
        Recipe.status == 'approved', Recipe.schema_version == 2, Recipe.image_filename.isnot(None),
        Recipe.age_from_months.is_(None)).order_by(Recipe.id)
    if slug == 'airfryer':
        q = q.where(Recipe.heat_source == 'airfryer')
    elif slug == 'protein':
        q = q.where(Recipe.total_protein >= PROTEIN_G * func.coalesce(Recipe.base_servings, 4))
    elif slug == 'dishes':
        q = q.where(Recipe.cleanup_factor == 1)
    elif slug == 'got':
        q = q.where(Recipe.protein_type.isnot(None), Recipe.protein_type.not_in(NOT_AN_INGREDIENT))
    elif slug == 'cuisine':
        q = q.where(Recipe.cuisine.isnot(None), Recipe.cuisine != '')
    ids = one_per_dish(db.session.execute(q).all())
    if not ids:
        return {}
    rows = db.session.execute(db.select(Recipe.id, Recipe.protein_type, Recipe.cuisine, Recipe.total_calories,
                                        Recipe.base_servings).where(Recipe.id.in_(ids))).all()
    buy = social_week.buy_sets(ids) if slug in ('got', 'cuisine') else {}
    return {i: {'protein': protein, 'cuisine': cuisine, 'kcal': (kcal or 0) / (servings or 4),
                'buy': frozenset(buy.get(i, ()))} for i, protein, cuisine, kcal, servings in rows}


def pick(slug, today=None):
    """The recipe ids for the next post of a series, or [] when the series has run out (then it pauses)."""
    today = today or datetime.date.today()
    c = candidates(slug)
    last = used_in(slug)
    since = today - datetime.timedelta(days=ONCE_A_WEEK)
    eligible = [i for i in c if i not in last or last[i] < since]

    def order(i):
        return (last.get(i, datetime.date.min), c[i]['kcal'] if slug == 'protein' else 0, i)
    eligible.sort(key=order)
    series = SERIES[slug]
    if series['count'] == 1:
        return eligible[:1]
    key = 'protein' if slug == 'got' else 'cuisine'
    by, group_last = {}, {}
    for i in eligible:
        by.setdefault(c[i][key], []).append(i)
    for i in c:
        group_last[c[i][key]] = max(group_last.get(c[i][key], datetime.date.min), last.get(i, datetime.date.min))
    groups = [g for g, ids in by.items() if len(ids) >= series['count']]
    if not groups:
        return []
    # The group least recently seen in the series; among the never seen, the biggest
    group = min(groups, key=lambda g: (group_last[g], -len(by[g]), g))
    ids = by[group]
    if slug == 'cuisine':
        varied = social_week.pick({i: {'protein': (c[i]['protein'] or 'none').lower(), 'buy': c[i]['buy']}
                                   for i in ids if c[i]['buy']})
        if varied:
            return varied
    return ids[:series['count']]
