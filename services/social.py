"""Posts for TikTok and Instagram, drawn from the recipes themselves (docs/SOCIAL.md).

A post is a carousel of slides: one page per slide at /social/…?slide=n, which scripts/social_render.py photographs.
The formats, tests for the first weeks:

- map: "Dinner as a subway map": the dish, its metro map, what you need, the steps in one list, the address.
- grid: "Everything in a dish": every ingredient as a symbol (guess the dinner), then with amounts, then the dish.
- pantry: "The foundation pantry": the foundation by kitchen group, and how much of what goes into dinner it covers.
- week: "One shop, five dinners": five dinners that share their shopping, the list, the week, each day
  (services/social_week.py).

Two sizes: ig (1080 × 1350, Instagram's tallest carousel) and tt (1080 × 1920, TikTok's photo mode). The last slide
gives the short address for the platform (thelazychef.app/ig or /tiktok, with the post's code), so a visit that came
from the post is counted (services/funnel.py).
"""
from database.models import Ingredient, db
from services.recipe_v2 import groups

SIZES = {'ig': (1080, 1350), 'tt': (1080, 1920)}
FORMATS = {'map': 'Dinner as a subway map', 'grid': 'Everything in a dish'}
ADDRESS = {'ig': 'thelazychef.app/ig', 'tt': 'thelazychef.app/tiktok'}
HASHTAGS = {'map': '#recipe #dinnerideas #easyrecipes #mealprep #cooking',
            'grid': '#recipe #ingredients #dinnerideas #easyrecipes #cooking',
            'pantry': '#pantry #pantrystaples #cookingtips #mealplanning #cooking',
            'week': '#mealplan #mealprep #groceryhaul #dinnerideas #easyrecipes'}

# How much of cooking the foundation pantry covers: the share of ingredient lines in 272 dishes Norwegian home cooks
# make, in 13 cuisines weighted by how often they are made (scripts/foundation_sample.py, RECIPE_MODEL_V2.md
# "Basisvarer og grunnlager", 22.10.2026)
COVERAGE = [('The staples alone', 21), ('The 60 most used', 74), ('The 100 most used', 84)]
COVERAGE_SAMPLE = '272 dishes home cooks make, in 13 cuisines'

# Steps on one slide of the map format, per size; a longer recipe ends the list with "and N more"
STEPS_PER_SLIDE = {'ig': 10, 'tt': 14}
# The metro map: every station is named when the names, at least MAP_NAME_GAP apart, stay within MAP_NAME_DRIFT of
# their stations; else only where a part starts, where parts meet and the end, so the names stay large enough to read
# on a phone. MAP_ROOM is the height the title, the key and the margins take; the map is scaled to the rest (at most
# MAP_MAX_SCALE).
MAP_NAME_DRIFT = 24
MAP_PAD = 24
MAP_ROOM = {'ig': 470, 'tt': 760}
MAP_MAX_SCALE = 2.6
MAP_NAME_GAP = 46
# The pantry format's groups fill a slide up to its height less GRID_ROOM: a row of PANTRY_COLS symbols is
# PANTRY_ROW high, a group's heading PANTRY_HEAD
PANTRY_COLS = 7
PANTRY_ROW = 190
PANTRY_HEAD = 70
# A grid of symbols takes the fewest columns (from 3) whose rows fit the room left on the slide: the slide's height less
# GRID_ROOM (margins, title, note); a labelled tile is CAPTION taller than it is wide. Columns are WIDTH wide in all.
GRID_ROOM = {'ig': 470, 'tt': 760}
CAPTION = 74
WIDTH = 912


def address(size, code=None):
    base = ADDRESS.get(size, ADDRESS['ig'])
    return f'{base}/{code}' if code else base


def buy_key(item):
    """What makes two shopping lines one thing to buy: the pantry item, else the name as written."""
    return item.get('pantry_id') or item['name'].lower()


def _ingredients(v):
    """The shopping list as tiles, the staples apart: (tiles, staple names)."""
    tiles = [{'name': s['name'], 'amount': s['amount'], 'img': s['img'], 'key': buy_key(s)}
             for g in v['shop_groups'] if g['key'] != 'staples' for s in g['items']]
    staples = [s['name'] for g in v['shop_groups'] if g['key'] == 'staples' for s in g['items']]
    return tiles, staples


def columns(n, size, labels=True, room=0):
    """How many columns a grid of n symbols needs to fit on the slide."""
    height = SIZES[size][1] - GRID_ROOM[size] - room
    for cols in range(3, 9):
        rows = -(-n // cols)
        if rows * (WIDTH / cols + (CAPTION if labels else 0) + 20) <= height:
            return cols
    return 9


def map_slide(m, size):
    """The metro map (services/recipe_v2/whole.metro_map) scaled to the slide, with the names to show and where."""
    height = SIZES[size][1]
    k = min((height - MAP_ROOM[size]) / (m['height'] + 2 * MAP_PAD), MAP_MAX_SCALE)

    def place(every):
        firsts = {}
        for st in m['stations']:
            firsts.setdefault(st['lane'], st['id'])
        labels = []
        for st in sorted(m['stations'], key=lambda st: st['y']):
            starts = firsts[st['lane']] == st['id'] and len(m['lanes']) > 1
            if not (every or st['final'] or st['merge'] or starts):
                continue
            part = starts and not every and not st['merge'] and not st['final']
            labels.append({'y': (st['y'] + MAP_PAD) * k, 'at': (st['y'] + MAP_PAD) * k,
                           'text': m['lanes'][st['lane']]['name'] if part else st['short'],
                           'lane': m['lanes'][st['lane']]['n'], 'part': part, 'final': st['final'],
                           'phase': st['phase'], 'time': st['time'] if every else None})
        for before, label in zip(labels, labels[1:]):
            label['y'] = max(label['y'], before['y'] + MAP_NAME_GAP)
        return labels

    # Every station named when the names can stay beside their stations; else the parts, meetings and the end
    labels = place(True)
    every = all(label['y'] - label['at'] <= MAP_NAME_DRIFT for label in labels)
    if not every:
        labels = place(False)
    return {'kind': 'map', 'map': m, 'k': k, 'pad': MAP_PAD, 'labels': labels, 'every': every}


def recipe_slides(view, fmt, dish_image, size='ig'):
    """The slides of a recipe post: [{'kind', ...}], from the recipe page's view (services/recipe_v2/view.page)."""
    tiles, staples = _ingredients(view)
    facts = {'total': view['total'], 'count': len(tiles), 'parts': view['parts']}
    cover = {'kind': 'cover', 'eyebrow': FORMATS[fmt], 'title': view['title'], 'image': dish_image, 'tiles': tiles,
             **facts}
    if fmt == 'grid':
        return [
            # The dish is not named before the third slide: the first asks the viewer to guess it
            {'kind': 'collage', 'title': 'Can you guess the dinner?', 'tiles': tiles, 'count': len(tiles),
             'cols': columns(len(tiles), size, labels=False, room=200)},
            {'kind': 'ingredients', 'title': 'What you need', 'tiles': tiles, 'staples': staples,
             'cols': columns(len(tiles), size)},
            {**cover, 'kind': 'dish', 'eyebrow': f'{len(tiles)} ingredients make'},
            {'kind': 'end', 'line': 'The whole recipe, step by step, with timers'},
        ]
    slides = [cover]
    if view['metro_map']:
        slides.append({**map_slide(view['metro_map'], size), 'title': 'The map', 'total': view['total']})
    slides.append({'kind': 'ingredients', 'title': 'What you need', 'tiles': tiles, 'staples': staples,
                   'cols': columns(len(tiles), size)})
    steps = [{'no': i + 1, 'short': s['short'], 'duration': s['duration'], 'phase': s['phase']}
             for i, s in enumerate(view['steps'])]
    if steps:
        # One step more than fits is shown rather than "and 1 more"
        shown = steps if len(steps) <= STEPS_PER_SLIDE[size] + 1 else steps[:STEPS_PER_SLIDE[size]]
        slides.append({'kind': 'steps', 'title': f'{len(steps)} steps, {view["total"]}', 'steps': shown,
                       'more': len(steps) - len(shown)})
    slides.append({'kind': 'end', 'line': 'Every step in full, with timers, bowls and the map'})
    return slides


def foundation():
    """The foundation pantry (tiers staple and foundation, RECIPE_MODEL_V2.md "Basisvarer og grunnlager"), as tiles in
    kitchen groups: [{'key', 'label', 'items'}]."""
    rows = db.session.execute(db.select(Ingredient).where(Ingredient.tier.in_(('staple', 'foundation')),
                                                          Ingredient.status == 'active')
                              .order_by(Ingredient.name)).scalars().all()
    items = [{'name': i.name, 'img': i.image_url, 'group': groups.group_of(i, i.tier == 'staple')} for i in rows]
    return groups.grouped(items)


def pantry_slides(size='ig'):
    grouped = foundation()
    count = sum(len(g['items']) for g in grouped)
    collage = [i for g in grouped for i in g['items'] if i['img']][::3][:30]
    slides = [{'kind': 'pantry_cover', 'count': count, 'tiles': collage, 'share': COVERAGE[-1][1],
               'cols': columns(len(collage), size, labels=False, room=260)}]
    # The groups in order, a new slide when the next group would not fit
    room = SIZES[size][1] - GRID_ROOM[size] + 160  # no title on these slides

    def height(group):
        return PANTRY_HEAD + -(-len(group['items']) // PANTRY_COLS) * PANTRY_ROW

    page = []
    for g in grouped:
        if page and sum(height(x) for x in page) + height(g) > room:
            slides.append({'kind': 'pantry', 'groups': page})
            page = []
        page.append(g)
    if page:
        slides.append({'kind': 'pantry', 'groups': page})
    slides.append({'kind': 'coverage', 'rows': COVERAGE, 'sample': COVERAGE_SAMPLE, 'count': count})
    slides.append({'kind': 'end', 'line': 'Every recipe shows what you need beyond these'})
    return slides


def caption(fmt, size, code=None, title=None, count=None, titles=()):
    """A first draft of the post's text, to edit before posting."""
    where = address(size, code)
    if fmt == 'week':
        lines = [f'Buy {count} things, make five dinners: ' + ', '.join(titles) + '. Save it for your next shop.',
                 '', f'All five recipes, with timers: {where}']
    elif fmt == 'pantry':
        lines = [f'The {count} ingredients behind most dinners: the 100 most used cover 84% of what goes into them. '
                 'Save this for your next big shop.',
                 '', f'Full recipes that show what you need beyond these: {where}']
    elif fmt == 'grid':
        lines = [f'{count} ingredients, one dinner. Guess it before the third picture gives it away.',
                 '', f'The whole recipe, with timers: {where}']
    else:
        lines = [f'{title}, drawn as a subway map. Every line is a part of the dish; where they meet, dinner is ready.',
                 '', f'Every step with timers: {where}']
    return '\n'.join(lines + ['', HASHTAGS[fmt]])
