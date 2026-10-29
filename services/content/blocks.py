"""The block kinds a page is made of (docs/CONTENT.md). One entry in KINDS per kind, each with:

- check(settings): what is wrong with the settings, as sentences (empty when all is well). Run when a version is
  saved, so a page never points at a recipe, page or embed that does not exist.
- load(settings, user, lang): the data its template needs (templates/blocks/<kind>.html), or None to leave the block
  out for this person (nothing to show).

A block in a page is {"kind", "settings", "audience"}; audience is "all", "signed_in" or "signed_out".
A new kind: a class here, its template, a line in docs/CONTENT.md and a test.
"""
import markdown
import nh3
from flask import url_for

from database.models import PageEmbed, Recipe, db
from services.recipe_library import Filters, cards, from_args, recipe_page
from werkzeug.datastructures import MultiDict

AUDIENCES = ('all', 'signed_in', 'signed_out')

# The parts of the app a "links" block may point at: endpoint -> (title, text, icon)
LINKABLE = {
    'discover': ('Discover', 'One dish at a time: save it or pass on it.', 'search'),
    'recipes_list': ('All recipes', 'Search and filter every dish.', 'book'),
    'explore_galaxy': ('Recipe galaxy', 'The dishes as a map, by cuisine and protein.', 'galaxy'),
    'explore_ingredient_galaxy': ('Ingredient galaxy', 'Everything in the pantry, as a map.', 'galaxy'),
    'pantry_management': ('Ingredients', 'What is in the pantry, with nutrition.', 'carrot'),
}
SORTS = ('new', 'quick', 'active')
# The filters a "recipes" block takes, as the recipe list's address parameters (services/recipe_library.from_args)
FILTER_KEYS = ('time', 'heat_source', 'protein', 'diet', 'cuisine', 'meal_type', 'difficulty', 'spice')


def _text(settings, key, errors, required=False, limit=500):
    value = settings.get(key)
    if value is None or value == '':
        if required:
            errors.append(f'{key} is missing')
        return
    if not isinstance(value, str):
        errors.append(f'{key} must be text')
    elif len(value) > limit:
        errors.append(f'{key} is longer than {limit} characters')


def _int(settings, key, errors, low, high):
    value = settings.get(key)
    if value is not None and (not isinstance(value, int) or isinstance(value, bool) or not low <= value <= high):
        errors.append(f'{key} must be a whole number from {low} to {high}')


def _filter_args(flt):
    args = MultiDict()
    for key in FILTER_KEYS:
        value = flt.get(key)
        for v in (value if isinstance(value, list) else [value] if value not in (None, '') else []):
            args.add(key, str(v))
    return args


class Block:
    label = ''

    def check(self, s):
        return []

    def load(self, s, user, lang):
        return s


class Text(Block):
    """Markdown, cleaned. style "intro" is the big opening of a page (a heading and a line), "prose" running text."""
    label = 'Text'

    def check(self, s):
        errors = []
        _text(s, 'markdown', errors, required=True, limit=20000)
        if s.get('style', 'prose') not in ('prose', 'intro'):
            errors.append('style must be "prose" or "intro"')
        return errors

    def load(self, s, user, lang):
        html = markdown.markdown(s['markdown'], extensions=['tables', 'sane_lists'])
        return {'html': nh3.clean(html), 'style': s.get('style', 'prose')}


class Recipes(Block):
    """A row of recipe cards: chosen ones (ids), or the newest, quickest or least hands-on matching a filter.
    Only approved recipes with a dish image. "more" links to the recipe list with the same filter."""
    label = 'Recipes'

    def check(self, s):
        errors = []
        _text(s, 'title', errors, limit=120)
        _text(s, 'text', errors)
        _int(s, 'limit', errors, 1, 12)
        ids, flt = s.get('ids'), s.get('filter')
        if ids is not None:
            if not isinstance(ids, list) or not all(isinstance(i, int) for i in ids):
                errors.append('ids must be a list of recipe ids')
            else:
                found = set(db.session.execute(db.select(Recipe.id).where(
                    Recipe.id.in_(ids), Recipe.status == 'approved')).scalars())
                missing = [i for i in ids if i not in found]
                if missing:
                    errors.append(f'no approved recipe with id {", ".join(map(str, missing))}')
        if flt is not None:
            if not isinstance(flt, dict) or set(flt) - set(FILTER_KEYS):
                errors.append(f'filter takes {", ".join(FILTER_KEYS)}')
            else:
                _, groups = from_args(_filter_args(flt))
                known = {g['key']: {v for v, _, _ in g['options']} for g in groups}
                for key, value in flt.items():
                    for v in (value if isinstance(value, list) else [value]):
                        if str(v) not in known[key]:
                            errors.append(f'filter {key}: "{v}" is not one of the choices')
        if s.get('sort', 'new') not in SORTS:
            errors.append(f'sort must be one of {", ".join(SORTS)}')
        return errors

    def load(self, s, user, lang):
        limit = s.get('limit', 6)
        if s.get('ids'):
            pictured = set(db.session.execute(db.select(Recipe.id).where(
                Recipe.id.in_(s['ids']), Recipe.status == 'approved', Recipe.image_filename.isnot(None))).scalars())
            recipes = cards([i for i in s['ids'] if i in pictured][:limit], user)
            more = None
        else:
            args = _filter_args(s.get('filter') or {})
            f = from_args(args)[0] if args else Filters()
            recipes = recipe_page('discover', f, sort=s.get('sort', 'new'), shown=limit, user=user, pictured=True).recipes
            more = url_for('recipes_list', **args.to_dict(flat=False), **({'sort': s['sort']} if s.get('sort', 'new') != 'new' else {}))
        if not recipes:
            return None
        return {'title': s.get('title'), 'text': s.get('text'), 'recipes': recipes, 'more': more if s.get('more') else None}


class Continue(Block):
    """The dish you are in the middle of on this device, from the ticks static/js/steps.js keeps; filled in by
    static/js/content.js and hidden when there is none."""
    label = 'Continue cooking'

    def check(self, s):
        errors = []
        _text(s, 'title', errors, limit=120)
        return errors


class CookNext(Block):
    """The person's Cook next queue, in order. Nothing for a visitor or an empty queue."""
    label = 'Cook next'

    def check(self, s):
        errors = []
        _text(s, 'title', errors, limit=120)
        _int(s, 'limit', errors, 1, 12)
        return errors

    def load(self, s, user, lang):
        if user is None:
            return None
        recipes = recipe_page('next', Filters(), shown=s.get('limit', 4), user=user).recipes
        if not recipes:
            return None
        return {'title': s.get('title') or 'Cook next', 'recipes': recipes, 'more': url_for('recipes_list', view='next')}


class Links(Block):
    """Ways into the app or to other pages, as tiles. An item's "to" is an endpoint in LINKABLE or "page:<slug>"
    (a published page: its title, summary and image unless the item says otherwise)."""
    label = 'Links'

    def check(self, s):
        from services.content.pages import find_page
        errors = []
        _text(s, 'title', errors, limit=120)
        items = s.get('items')
        if not isinstance(items, list) or not items:
            return errors + ['items must be a list of links']
        for n, item in enumerate(items, 1):
            if not isinstance(item, dict):
                errors.append(f'item {n} must be an object')
                continue
            to = item.get('to', '')
            if isinstance(to, str) and to.startswith('page:'):
                if not find_page(to[5:]):
                    errors.append(f'item {n}: no page "{to[5:]}"')
            elif to not in LINKABLE:
                errors.append(f'item {n}: "to" must be "page:<slug>" or one of {", ".join(LINKABLE)}')
            for key in ('title', 'text', 'icon'):
                _text(item, key, errors, limit=200)
        return errors

    def load(self, s, user, lang):
        from services.content.pages import find_page, live_text
        tiles = []
        for item in s['items']:
            to = item['to']
            if to.startswith('page:'):
                page = find_page(to[5:])
                text = page and live_text(page, lang)
                if not text:
                    continue  # not published (yet): no tile
                tile = {'url': page_url(page), 'title': text.title, 'text': text.summary, 'icon': 'book',
                        'image': text.hero_image}
            else:
                title, blurb, icon = LINKABLE[to]
                tile = {'url': url_for(to), 'title': title, 'text': blurb, 'icon': icon, 'image': None}
            tile.update({k: item[k] for k in ('title', 'text', 'icon') if item.get(k)})
            tiles.append(tile)
        return {'title': s.get('title'), 'tiles': tiles} if tiles else None


class Interactive(Block):
    """The escape hatch: a one-off interactive made with Claude, a self-contained HTML page stored as a PageEmbed and
    shown in a sandboxed frame (/content/interactive/<id>) that takes the height its page asks for. When a kind of
    interactive is wanted twice, it becomes a block kind of its own."""
    label = 'Interactive'

    def check(self, s):
        errors = []
        _text(s, 'title', errors, required=True, limit=200)
        _text(s, 'caption', errors)
        _int(s, 'height', errors, 120, 4000)
        if not isinstance(s.get('embed'), str) or not db.session.get(PageEmbed, s['embed']):
            errors.append('embed must be the id of an uploaded interactive (Admin -> Pages)')
        return errors

    def load(self, s, user, lang):
        return {'src': url_for('content.embed', embed_id=s['embed']), 'title': s['title'],
                'caption': s.get('caption'), 'height': s.get('height', 600), 'id': s['embed']}


KINDS = {'text': Text(), 'recipes': Recipes(), 'continue': Continue(), 'cook_next': CookNext(), 'links': Links(),
         'interactive': Interactive()}


def page_url(page):
    return url_for('content.home') if page.kind == 'home' else url_for('content.page', slug=page.slug)
