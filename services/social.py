"""Posts for TikTok and Instagram, drawn from the recipes themselves (docs/SOCIAL.md).

A post is a carousel of slides: one page per slide at /social/…?slide=n, which scripts/social_render.py photographs.
The formats, tests for the first weeks:

- map: "Dinner as a subway map": the dish, its metro map, what you need, the steps in one list, the address.
- grid: "Everything in a dish": every ingredient as a symbol (guess the dinner), then with amounts, then the dish.
- pantry: "The foundation pantry": the foundation by kitchen group, and how much of what goes into dinner it covers.
- week: "One shop, five dinners": five dinners that share their shopping, the list, the week, each day
  (services/social_week.py).
- The series (services/social_series.py, /social/post?series=): Air fryer dinners, Got [ingredient]?, High-protein
  dinners, Dishes to wash: N, Guess the dinner and 5 weeknights of [cuisine], built from the slide kinds here: the
  dishes to wash, the shopping list split in "to buy" and "you probably have", the river delta, the steps with
  timers, the big numbers, the active-against-hands-off bar and the air fryer's temperature and time.

Two sizes: ig (1080 × 1350, Instagram's tallest carousel) and tt (1080 × 1920, TikTok's photo mode). The last slide
gives the short address for the platform (thelazychef.app/ig or /tiktok, with the post's code), so a visit that came
from the post is counted (services/funnel.py).
"""
from database.models import Ingredient, db
from services.measures import temp
from services.recipe_v2 import groups
from services.recipe_v2.derive import HEAT_LABELS, VESSELS

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
# The river delta goes on a slide only when it is small enough to read on a phone: at most DELTA_DEPTH levels above
# the dish (delta.build's max_depth, the dish at 0) and DELTA_LEAVES branches. 11 of the 59 public recipes on
# 31.10.2026 (serier.md); else the slide shows the time bar.
DELTA_DEPTH = 2
DELTA_LEAVES = 2
# The steps with timers: at most this many on the slide, the rest "and N more"
TIMER_STEPS = 6
# What does the hands-off minutes while the cook does nothing, by the recipe's heat source (derive.HEAT_SOURCES)
IDLE_BY = {'airfryer': 'the air fryer', 'oven': 'the oven', 'pot': 'the pot', 'pan': 'the pan', 'grill': 'the grill',
           'slow_cooker': 'the slow cooker', 'microwave': 'the microwave', 'sous_vide': 'the water bath'}
IDLE = 'hands off'


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


def _staples(v):
    """What you probably have, as tiles (the staples group of the shopping list)."""
    return [{'name': s['name'], 'amount': None, 'img': s['img'], 'key': buy_key(s)}
            for g in v['shop_groups'] if g['key'] == 'staples' for s in g['items']]


def end_slide(line, cta=None):
    """The last slide: the address, after the line; or a CTA ({'group', 'text'}, services/social_series.py), with the
    address kept small under it when the CTA is not the site itself."""
    if cta:
        return {'kind': 'end', 'line': cta['text'], 'cta': cta['group'], 'small': cta['group'] != 'site'}
    return {'kind': 'end', 'line': line}


# The slide kinds the series are built from (docs/SOCIAL.md "The series"), each from the recipe page's view

def delta_fits(d):
    """Whether the river delta is small enough for a slide."""
    return bool(d) and d['max_depth'] <= DELTA_DEPTH and d['leaves'] <= DELTA_LEAVES


def delta_slide(view):
    """The river delta drawn on the slide, or None when it is too big (then the time bar takes its place). The cells
    are placed on a grid as static/js/delta.js does portrait: a column per branch, the dish on the last row; every
    arrow runs straight down into the step below, since a step spans its branches."""
    d = view['delta']
    if not delta_fits(d):
        return None
    flows = {a for a, b in d['edges']}
    return {'kind': 'delta', 'title': 'The whole dish', 'total': view['total'], 'cols': d['leaves'],
            'rows': d['max_depth'] + 1,
            'cells': [{**n, 'row': d['max_depth'] - n['depth'] + 1, 'col': (n['span'][0] + 1, n['span'][1] + 1),
                       'flows': n['id'] in flows} for n in d['nodes']]}


def timebar_slide(view, heat_source=None):
    """Active against hands-off time: "9 min you, 41 min the oven"."""
    total, active = view['total_min'], min(view['active_min'], view['total_min'])
    idle = total - active
    doer = IDLE_BY.get(heat_source, IDLE)
    return {'kind': 'timebar', 'title': f'{total} minutes. {active} of them yours.', 'active': active, 'idle': idle,
            'total': total, 'doer': doer, 'you': f'{active} min you', 'other': f'{idle} min {doer}'}


def timers_slide(view):
    """The steps with their timers, at most TIMER_STEPS; a standing time is the timer."""
    steps = [{'no': s['n'], 'short': s['short'], 'duration': s['duration'], 'phase': s['phase'],
              'timer': f"{s['passive_min']} min" if s.get('passive_min') else None} for s in view['steps']]
    shown = steps if len(steps) <= TIMER_STEPS + 1 else steps[:TIMER_STEPS]
    return {'kind': 'timers', 'title': f'{len(steps)} steps, {view["total"]}', 'steps': shown,
            'more': len(steps) - len(shown)}


def numbers_slide(view, title=None):
    """The big numbers: protein and kcal per serving (when the recipe has nutrition), and the minutes."""
    n = view['nutrition']
    items = []
    if n:
        items += [{'value': n['protein'], 'unit': 'g', 'label': 'protein per serving'},
                  {'value': n['kcal'], 'unit': '', 'label': 'kcal per serving'}]
    items.append({'value': view['total_min'], 'unit': 'min', 'label': 'start to table'})
    if not n:
        items.append({'value': view['active_min'], 'unit': 'min', 'label': 'of them yours'})
    return {'kind': 'numbers', 'title': title or view['title'], 'items': items}


def wash_slide(view, images):
    """The equipment to wash: the vessels (derive.VESSELS) with their images ({equipment id: url}), nothing else."""
    items = [{'name': e['name'], 'img': images.get(e['id'])} for e in view['equipment'] if e['id'] in VESSELS]
    return {'kind': 'wash', 'title': f'Dishes to wash: {len(items)}', 'items': items, 'count': len(items),
            'cols': min(max(len(items), 1), 3)}


def airfryer_slide(view, images):
    """The air fryer's temperature and time, from the steps in it (else the heated steps), with its image."""
    steps = [s for s in view['steps'] if 'airfryer' in s['equipment_ids']] or [s for s in view['steps'] if s['heat']]
    temps = [s['temp_c'] for s in steps if s.get('temp_c')]
    minutes = sum(s['minutes'] for s in steps)
    return {'kind': 'airfryer', 'title': 'In the air fryer', 'name': HEAT_LABELS['airfryer'],
            'temp': temp(max(temps), view['units']) if temps else None, 'minutes': minutes,
            'img': images.get('airfryer')}


def shop_split_slide(view, size):
    """The shopping list in two: what to buy, with amounts, and what you probably have."""
    tiles, _ = _ingredients(view)
    have = _staples(view)
    return {'kind': 'shop_split', 'title': f'Buy {len(tiles)} things', 'tiles': tiles, 'have': have,
            'cols': columns(len(tiles), size, room=160 if have else 0)}


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


def recipe_slides(view, fmt, dish_image, size='ig', hook=None, cta=None):
    """The slides of a recipe post: [{'kind', ...}], from the recipe page's view (services/recipe_v2/view.page).
    hook is the words on the first slide instead of the dish's name (the grid's question), cta the last slide's
    {'group', 'text'} (services/social_series.py); without them the post is as it always was."""
    tiles, staples = _ingredients(view)
    facts = {'total': view['total'], 'count': len(tiles), 'parts': view['parts']}
    cover = {'kind': 'cover', 'eyebrow': FORMATS[fmt], 'title': view['title'], 'image': dish_image, 'tiles': tiles,
             **facts}
    if hook:
        cover.update(title=hook, name=view['title'])
    if fmt == 'grid':
        return [
            # The dish is not named before the third slide: the first asks the viewer to guess it
            {'kind': 'collage', 'title': hook or 'Can you guess the dinner?', 'tiles': tiles, 'count': len(tiles),
             'cols': columns(len(tiles), size, labels=False, room=200)},
            {'kind': 'ingredients', 'title': 'What you need', 'tiles': tiles, 'staples': staples,
             'cols': columns(len(tiles), size)},
            {**cover, 'kind': 'dish', 'eyebrow': f'{len(tiles)} ingredients make', 'title': view['title'], 'name': None},
            end_slide('The whole recipe, step by step, with timers', cta),
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
    slides.append(end_slide('Every step in full, with timers, bowls and the map', cta))
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
