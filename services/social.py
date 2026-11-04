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

Two sizes: ig (1080 × 1350, Instagram's tallest carousel) and tt (1080 × 1440, the 3:4 TikTok's photo mode shows on a
phone: a taller picture loses its top and bottom there). The last slide
gives the short address for the platform (thelazychef.app/ig or /tiktok, with the post's code), so a visit that came
from the post is counted (services/funnel.py).
"""
import html
import re
import textwrap

from database.models import Ingredient, db
from services.measures import temp
from services.recipe_v2 import groups
from services.recipe_v2.derive import HEAT_LABELS, HEAT_SOURCES, VESSELS

SIZES = {'ig': (1080, 1350), 'tt': (1080, 1440)}
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
STEPS_PER_SLIDE = {'ig': 10, 'tt': 11}
# The metro map: every station is named when the names, at least MAP_NAME_GAP apart, stay within MAP_NAME_DRIFT of
# their stations; else only where a part starts, where parts meet and the end, so the names stay large enough to read
# on a phone. MAP_ROOM is the height the title, the key and the margins take; the map is scaled to the rest (at most
# MAP_MAX_SCALE).
MAP_NAME_DRIFT = 24
MAP_PAD = 24
MAP_ROOM = {'ig': 470, 'tt': 502}
MAP_MAX_SCALE = 2.6
MAP_NAME_GAP = 46
# The pantry format's groups fill a slide up to its height less GRID_ROOM: a row of PANTRY_COLS symbols is
# PANTRY_ROW high, a group's heading PANTRY_HEAD
PANTRY_COLS = 7
PANTRY_ROW = 190
PANTRY_HEAD = 70
# A grid of symbols takes the fewest columns (from 3) whose rows fit the room left on the slide: the slide's height less
# GRID_ROOM (margins, title, note); a labelled tile is CAPTION taller than it is wide. Columns are WIDTH wide in all.
GRID_ROOM = {'ig': 470, 'tt': 502}
CAPTION = 74
WIDTH = 912
# The points game's pictures: the height left for them after the margins, the eyebrow, the score block, the bar and
# the line at the bottom, per size; a tile's caption; and the least of its cell a symbol takes (game_symbol, which
# static/css/social.css applies), so that 12 is 4 by 3 and 15 is 5 by 3 on both sizes
GAME_HEIGHT = {'ig': 790, 'tt': 848}
GAME_CAPTION = 82
GAME_SYMBOL = {'ig': 0.72, 'tt': 0.72}
# The symbols strip on a cover: at most this many in a row
STRIP_COLS = 6
# The river delta goes on a slide only when it is small enough to read on a phone: at most DELTA_DEPTH levels above
# the dish (delta.build's max_depth, the dish at 0) and DELTA_LEAVES branches. 11 of the 59 public recipes on
# 31.10.2026 (serier.md); else the slide shows the time bar.
DELTA_DEPTH = 2
DELTA_LEAVES = 2
# The steps as on the Cook view (a series): at most this many per slide, over as many slides as it takes, each step's
# symbols with it
COOK_STEPS = {'ig': 3, 'tt': 3}
# Fewer when they would run into the foot. COOK_ROOM is the height from under the eyebrow to just above the foot; a step
# takes its name's lines (COOK_NAME_CHARS to a line) and rows of symbols (static/css/social.css .cook), at least the
# numeral. Measured on the 59 recipes in F Washi, 03.11.2026.
COOK_ROOM = {'ig': 1082, 'tt': 1140}
COOK_GAP = 24
COOK_NUMERAL = 110
COOK_NAME_CHARS = 21
COOK_NAME_LINE = 72
COOK_SYMBOLS_ROW = 4
COOK_SYMBOLS_HEIGHT = 218
COOK_SYMBOLS_TOP = 14
# A step on its own slide (The whole recipe), in its own words, which are never cut: FULL_ROOM is the height from the top
# margin to just above the foot, and the rest what static/css/social.css .kind-step draws, as lines of about so many
# characters. full_step_height adds them up.
FULL_ROOM = {'ig': 1104, 'tt': 1162}
FULL_EYEBROW = 54
FULL_FACTS_ONE = 58
FULL_NAME_CHARS, FULL_NAME_LINE = 26, 76
FULL_FACTS_TOP, FULL_FACTS_CHARS, FULL_FACTS_LINE = 24, 52, 72
FULL_TEXT_TOP, FULL_TEXT_CHARS, FULL_TEXT_LINE = 28, 40, 59
FULL_SYMBOLS_TOP, FULL_SYMBOLS_ROW, FULL_SYMBOLS_HEIGHT, FULL_SYMBOL_NAME_CHARS, FULL_SYMBOL_NAME_LINE = 28, 6, 164, 9, 27
FULL_DONE_TOP, FULL_DONE_CHARS, FULL_DONE_LINE = 28, 44, 47
FULL_TILE_MIN, FULL_TILE_MAX, FULL_TILE_GAP, FULL_TILE_CAPTION = 132, 300, 20, 76  # a symbol's width; the room for its name
SYMBOL_IN_TEXT = re.compile(r'<span class="sym[^>]*>.*?</span>', re.DOTALL)  # view.symbol, as a step's text has it
SERVES_ROOM = 60  # what "Serves 4" takes from the shopping list's symbols
# The symbols on a series cover: this many of the things to buy, under the hook, in two rows of six
COVER_SYMBOLS = 12
# One Pot Meals count the vessels food is cooked in: not bowls, sieves, machines (derive.VESSELS has them for the
# washing up) and not the air fryer, which is a series of its own
COOK_VESSELS = {'grill_pan', 'saucepan', 'large_pot', 'wide_pot', 'dutch_oven', 'frying_pan', 'wok', 'steamer',
                'deep_fryer', 'slow_cooker', 'baking_tray', 'roasting_pan', 'ovenproof_dish', 'form_20x20', 'form_20x30',
                'springform_24', 'loaf_tin', 'muffin_tin', 'silicone_cups', 'pie_dish'}
# A shopping list for several dinners goes over as many slides as it takes to keep SHOP_PER_SLIDE things or fewer on
# each, split evenly, so a week of 50 things is readable on a phone
SHOP_PER_SLIDE = 24
# What does the hands-off minutes while the cook does nothing, by the recipe's heat source (derive.HEAT_SOURCES)
IDLE_BY = {'airfryer': 'the air fryer', 'oven': 'the oven', 'pot': 'the pot', 'pan': 'the pan', 'grill': 'the grill',
           'slow_cooker': 'the slow cooker', 'microwave': 'the microwave', 'sous_vide': 'the water bath'}
IDLE = 'hands off'
# Time is a selling point only when it is short (serier-v2.md): the active time is said only under SAY_ACTIVE_UNDER
# minutes, the time from start to table only at SAY_TOTAL_UPTO or less, and under STRESS_* it may be stressed
# ("under 10 minutes of work"). Above the limits no minutes appear: not in the hook, on the cover, on a day's label,
# on the numbers slide or in the caption. said_active() and said_total() give the minutes or None.
SAY_ACTIVE_UNDER = 20
SAY_TOTAL_UPTO = 30
STRESS_ACTIVE_UNDER = 10
STRESS_TOTAL_UNDER = 20


def said_active(minutes):
    """The minutes of work when they may be said, else None."""
    return minutes if minutes is not None and minutes < SAY_ACTIVE_UNDER else None


def said_total(minutes):
    """The minutes from start to table when they may be said, else None."""
    return minutes if minutes is not None and minutes <= SAY_TOTAL_UPTO else None


def clock(minutes):
    """A time on a slide: "45 min", and from two hours "2 h 37 min" (the recipe page's view.duration says "2.6 h",
    which reads badly beside "105 min")."""
    if minutes < 120:
        return f'{minutes} min'
    hours, rest = divmod(minutes, 60)
    return f'{hours} h {rest} min' if rest else f'{hours} h'


def shop_slides(tiles, staples, size, title='The shopping list'):
    """The shopping list for several dinners (×3 = in three of them), over more slides than one when it is long;
    the staples on the last."""
    pages = max(1, -(-len(tiles) // SHOP_PER_SLIDE))
    base, extra = divmod(len(tiles), pages)
    out, at = [], 0
    for i in range(pages):
        page = tiles[at:at + base + (1 if i < extra else 0)]
        at += len(page)
        out.append({'kind': 'shop', 'title': title if pages == 1 else f'{title}, {i + 1} of {pages}', 'tiles': page,
                    'staples': staples if i == pages - 1 else [], 'cols': columns(len(page), size)})
    return out


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


def end_slide(line, cta=None, images=()):
    """The last slide: the address, after the line; or a CTA ({'group', 'text'}, services/social_series.py), with the
    address kept small under it when the CTA is not the site itself. With the dish images (a series) the slide is
    the dish over the whole slide, several in a grid, the CTA as the site's button and the address in white."""
    if cta:
        return {'kind': 'end', 'line': cta['text'], 'cta': cta['group'], 'small': cta['group'] != 'site',
                'images': [i for i in images if i], 'count': len([i for i in images if i])}
    return {'kind': 'end', 'line': line}


def cooking_vessels(view):
    """The vessels food is cooked in (COOK_VESSELS), in the order they are first used: [{'id', 'name', 'image'}]."""
    return [e for e in view['equipment'] if e['id'] in COOK_VESSELS]


def cook_step_height(step):
    """About how tall a step is on a slide, in the slide's pixels."""
    height = -(-len(step['short']) // COOK_NAME_CHARS) * COOK_NAME_LINE
    if step['symbols']:
        height += COOK_SYMBOLS_TOP + -(-len(step['symbols']) // COOK_SYMBOLS_ROW) * COOK_SYMBOLS_HEIGHT
    return max(COOK_NUMERAL, height)


def cook_pages(steps, size):
    """The steps over the fewest slides they fit, as evenly as that allows."""
    def fits(page):
        return (len(page) <= COOK_STEPS[size] and
                sum(cook_step_height(st) for st in page) + COOK_GAP * (len(page) - 1) <= COOK_ROOM[size])

    filled = []
    for st in steps:
        if filled and fits(filled[-1] + [st]):
            filled[-1].append(st)
        else:
            filled.append([st])
    base, extra = divmod(len(steps), max(1, len(filled)))
    even, at = [], 0
    for i in range(len(filled)):
        even.append(steps[at:at + base + (1 if i < extra else 0)])
        at += len(even[-1])
    return even if all(fits(page) for page in even) else filled


def steps_slides(view, size):
    """The steps as on the Cook view (slide kind 'cook'; 'steps' is the map format's one list), COOK_STEPS at a
    time, or over more slides when that many would not fit COOK_ROOM: each step's number, its short name, large, and
    the symbols of the lines that go in with their amounts; no minutes."""
    pictured = view.get('pictured') or {}
    steps = []
    for s in view['steps']:
        symbols = [{'name': pictured[lid]['name'], 'img': pictured[lid]['img'], 'amount': pictured[lid]['amount']}
                   for lid in s.get('uses') or [] if lid in pictured]
        steps.append({'no': s['n'], 'short': s['short'], 'phase': s['phase'], 'symbols': symbols})
    pages = cook_pages(steps, size)
    out = []
    for i, page in enumerate(pages):
        first, last = page[0]['no'], page[-1]['no']
        out.append({'kind': 'cook', 'eyebrow': f'Step {first}' + (f' to {last}' if last != first else '') + f' of {len(steps)}',
                    'steps': page, 'page': i + 1, 'pages': len(pages)})
    return out


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
    total = said_total(view['total_min'])
    return {'kind': 'delta', 'title': 'The whole dish', 'total': clock(total) if total else None, 'cols': d['leaves'],
            'rows': d['max_depth'] + 1,
            'cells': [{**n, 'row': d['max_depth'] - n['depth'] + 1, 'col': (n['span'][0] + 1, n['span'][1] + 1),
                       'flows': n['id'] in flows} for n in d['nodes']]}


def machine_minutes(view, heat_source):
    """The minutes the heat source cooks on its own: the standing time of the steps in it (derive.HEAT_SOURCES).
    0 when the recipe has no such step or none stands."""
    ids = set(HEAT_SOURCES.get(heat_source, ()))
    return sum(s.get('passive_min') or 0 for s in view['steps'] if ids & set(s['equipment_ids']))


def hands_off(view, heat_source=None):
    """The time the cook is not working, and who does it: (minutes, 'the air fryer'). One definition for the hook,
    the time bar and the air fryer slide: the heat source's own minutes (machine_minutes) when it has any, else the
    whole of the time from start to table that is not active, 'hands off'."""
    total, active = view['total_min'], min(view['active_min'], view['total_min'])
    minutes = machine_minutes(view, heat_source)
    if minutes:
        return minutes, IDLE_BY.get(heat_source, IDLE)
    return total - active, IDLE


def machine_temp(view, heat_source):
    """The heat source's temperature as written for the reader ("200 °C"), the highest of its steps, or None."""
    ids = set(HEAT_SOURCES.get(heat_source, ()))
    temps = [s['temp_c'] for s in view['steps'] if s.get('temp_c') and ids & set(s['equipment_ids'])]
    return temp(max(temps), view['units']) if temps else None


def numbers_slide(view, title=None):
    """The big numbers: protein and kcal per serving (when the recipe has nutrition), no minutes (time is not what a
    high-protein dinner sells); without nutrition, the things to buy and the dishes to wash."""
    n = view['nutrition']
    items = []
    if n:
        items += [{'value': n['protein'], 'unit': 'g', 'label': 'protein per serving'},
                  {'value': n['kcal'], 'unit': '', 'label': 'kcal per serving'}]
    if not items:
        items += [{'value': len(_ingredients(view)[0]), 'unit': '', 'label': 'things to buy'},
                  {'value': len([e for e in view['equipment'] if e['id'] in VESSELS]), 'unit': '', 'label': 'dishes to wash'}]
    return {'kind': 'numbers', 'title': title or view['title'], 'items': items}


def wash_slide(view, images):
    """The equipment to wash: the vessels (derive.VESSELS) with their images ({equipment id: url}), nothing else."""
    items = [{'name': e['name'], 'img': images.get(e['id'])} for e in view['equipment'] if e['id'] in VESSELS]
    return {'kind': 'wash', 'title': f'Dishes to wash: {len(items)}', 'items': items, 'count': len(items),
            'cols': min(max(len(items), 1), 3)}


def airfryer_slide(view, images):
    """The air fryer's temperature and its minutes (hands_off: the same number the hook and the time bar give), with
    its image. A recipe with no step standing in the air fryer shows the minutes of its heated steps instead."""
    steps = [s for s in view['steps'] if 'airfryer' in s['equipment_ids']] or [s for s in view['steps'] if s['heat']]
    temps = [s['temp_c'] for s in steps if s.get('temp_c')]
    minutes = machine_minutes(view, 'airfryer') or sum(s['minutes'] for s in steps)
    return {'kind': 'airfryer', 'title': 'In the air fryer', 'name': HEAT_LABELS['airfryer'],
            'temp': temp(max(temps), view['units']) if temps else None, 'minutes': minutes,
            'img': images.get('airfryer')}


def shop_split_slide(view, size, serves=False):
    """The shopping list in two: what to buy, with amounts, and what you probably have; serves also says how much the
    amounts make, for a post you can cook from."""
    tiles, _ = _ingredients(view)
    have = _staples(view)
    said = (view.get('yield_text') or f"Serves {view['servings']}") if serves else None
    return {'kind': 'shop_split', 'title': f'Buy {len(tiles)} things', 'tiles': tiles, 'have': have, 'serves': said,
            'cols': columns(len(tiles), size, room=(220 if have else 0) + (SERVES_ROOM if serves else 0))}


def full_step_slides(view, size):
    """The whole recipe: a slide per step, in the step list's order and its own words ('html', with the amounts), with
    what the step list says about it, and the symbols of the lines that go in (kind 'step'), as large as the room under
    the words lets them (full_step_tile)."""
    pictured = view.get('pictured') or {}
    out = []
    for s in view['steps']:
        symbols = [{'name': pictured[lid]['name'], 'img': pictured[lid]['img']}
                   for lid in s.get('uses') or [] if lid in pictured]
        slide = {'kind': 'step', 'eyebrow': f"Step {s['n']} of {len(view['steps'])}", 'short': s['short'],
                 'part': s['component'] if len(view['parts']) > 1 else None, 'html': s['html'],
                 'facts': [fact for fact in (s['duration'], s['equipment']) if fact], 'during': s['while'],
                 'done_when': s['done_when'], 'symbols': symbols}
        out.append({**slide, 'tile': full_step_tile(slide, size)})
    return out


def lines_of(text, chars):
    """The lines a text takes at about chars characters to a line."""
    return len(textwrap.wrap(text, chars)) or 1


def full_step_words(slide):
    """About how tall a step's slide is without its symbols, in the slide's pixels (static/css/social.css .kind-step). In
    the step's words: the symbols inside the text's amounts are hidden on the slide, so they do not count."""
    text = re.sub(r'<[^>]+>', '', SYMBOL_IN_TEXT.sub('', str(slide['html'])))
    height = FULL_EYEBROW + lines_of(slide['short'], FULL_NAME_CHARS) * FULL_NAME_LINE
    height += FULL_TEXT_TOP + lines_of(html.unescape(text), FULL_TEXT_CHARS) * FULL_TEXT_LINE
    if slide['facts'] or slide['during']:
        chips = ' '.join([*slide['facts'], slide['during']])
        height += FULL_FACTS_TOP + (lines_of(chips, FULL_FACTS_CHARS) - 1) * FULL_FACTS_LINE + FULL_FACTS_ONE
    if slide['done_when']:
        height += FULL_DONE_TOP + lines_of(f"Done when {slide['done_when']}", FULL_DONE_CHARS) * FULL_DONE_LINE
    return height


def full_step_height(slide):
    """About how tall a step's slide is at the least, with its symbols at their smallest (FULL_SYMBOLS_*): what decides
    whether it fits, never much less than it comes to in a browser."""
    height = full_step_words(slide)
    if slide['symbols']:
        names = [lines_of(t['name'], FULL_SYMBOL_NAME_CHARS) for t in slide['symbols']]
        rows = [names[i:i + FULL_SYMBOLS_ROW] for i in range(0, len(names), FULL_SYMBOLS_ROW)]
        height += FULL_SYMBOLS_TOP + sum(FULL_SYMBOLS_HEIGHT + (max(row) - 1) * FULL_SYMBOL_NAME_LINE for row in rows)
    return height


def full_step_tile(slide, size):
    """How wide a symbol is on a step's slide, in pixels: the largest, up to FULL_TILE_MAX, whose rows fit the room the
    words leave; at least FULL_TILE_MIN, which is what full_step_height counts."""
    n = len(slide['symbols'])
    room = FULL_ROOM[size] - full_step_words(slide) - FULL_SYMBOLS_TOP
    best = FULL_TILE_MIN
    for cols in range(1, min(n, FULL_SYMBOLS_ROW) + 1):
        width = min((WIDTH - FULL_TILE_GAP * (cols - 1)) // cols, FULL_TILE_MAX)
        if -(-n // cols) * (width + FULL_TILE_CAPTION) <= room:
            best = max(best, width)
    return best


def full_steps_fit(view):
    """Whether every step's slide fits above the foot on both sizes (Instagram's is the shorter)."""
    return all(full_step_height(slide) <= min(FULL_ROOM.values()) for slide in full_step_slides(view, 'ig'))


def columns(n, size, labels=True, room=0):
    """How many columns a grid of n symbols needs to fit on the slide."""
    height = SIZES[size][1] - GRID_ROOM[size] - room
    for cols in range(3, 9):
        rows = -(-n // cols)
        if rows * (WIDTH / cols + (CAPTION if labels else 0) + 20) <= height:
            return cols
    return 9


def game_columns(n, size):
    """The columns of the points game's pictures: full rows where a count from 4 to STRIP_COLS divides them (12 is
    4 by 3, 15 is 5 by 3), with the symbols as large as fit; else the fewest columns from 4 that fit the slide."""
    def fits(cols):
        rows = -(-n // cols)
        return rows * (WIDTH / cols * GAME_SYMBOL[size] + GAME_CAPTION + 12) <= GAME_HEIGHT[size]
    full = [c for c in range(4, STRIP_COLS + 1) if n % c == 0 and fits(c)]
    if full:
        return full[0]
    return next((c for c in range(4, 9) if fits(c)), 9)


def game_symbol(n, size):
    """How much of its cell a symbol takes in the points game, in percent: as much as game_columns' rows leave room
    for on the slide with the amounts, from GAME_SYMBOL up to all of it, so ten things are not small for no reason."""
    cols = game_columns(n, size)
    room = (GAME_HEIGHT[size] / -(-n // cols) - GAME_CAPTION - 12) / (WIDTH / cols)
    return round(100 * min(1, max(GAME_SYMBOL[size], room)))


def strip_columns(n):
    """The columns of a cover's symbols strip: one row up to STRIP_COLS, else rows as even as they come (7 is 4 and
    3, 12 is 6 and 6), never an orphan."""
    rows = max(1, -(-n // STRIP_COLS))
    return -(-n // rows)


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
    facts = {'total': clock(view['total_min']), 'count': len(tiles), 'parts': view['parts']}
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
        slides.append({**map_slide(view['metro_map'], size), 'title': 'The map', 'total': clock(view['total_min'])})
    slides.append({'kind': 'ingredients', 'title': 'What you need', 'tiles': tiles, 'staples': staples,
                   'cols': columns(len(tiles), size)})
    steps = [{'no': i + 1, 'short': s['short'], 'duration': s['duration'], 'phase': s['phase']}
             for i, s in enumerate(view['steps'])]
    if steps:
        # One step more than fits is shown rather than "and 1 more"
        shown = steps if len(steps) <= STEPS_PER_SLIDE[size] + 1 else steps[:STEPS_PER_SLIDE[size]]
        slides.append({'kind': 'steps', 'title': f'{len(steps)} steps, {clock(view["total_min"])}', 'steps': shown,
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
