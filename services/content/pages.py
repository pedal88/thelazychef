"""Pages made of blocks (docs/CONTENT.md): versions, publishing, what a person sees, and the content package Claude
writes. A page's text is kept per language in PageText rows; every save is a new version.

A content package (what Claude makes, pasted in Admin -> Pages -> Import):
    {"slug", "kind", "lang", "title", "summary", "hero_image", "note", "blocks": [{"kind", "settings", "audience"}]}
Importing saves it as a new, unpublished version of that page in that language; the page is made if it is new.
"""
import datetime
import logging
import re

from database.models import Page, PageText, db
from services.content.blocks import AUDIENCES, KINDS

log = logging.getLogger(__name__)
LANGS = {'en': 'English', 'no': 'Norsk'}
DEFAULT_LANG = 'en'
PAGE_KINDS = ('home', 'guide', 'landing')
SLUG = re.compile(r'^[a-z0-9]+(?:-[a-z0-9]+)*$')
HOME = 'home'


class ContentError(ValueError):
    """What is wrong with a package or a version, as a list of sentences."""

    def __init__(self, errors):
        super().__init__('; '.join(errors))
        self.errors = errors


def find_page(slug):
    return db.session.execute(db.select(Page).where(Page.slug == slug)).scalar_one_or_none()


def _texts(page, lang):
    return [t for t in page.texts if t.lang == lang]


def latest_text(page, lang):
    """The newest version in this language, published or not (what an admin previews)."""
    texts = _texts(page, lang)
    return max(texts, key=lambda t: t.version) if texts else None


def live_text(page, lang=DEFAULT_LANG):
    """What visitors see: the newest published version in this language, else in the default language."""
    for code in dict.fromkeys((lang, DEFAULT_LANG)):
        published = [t for t in _texts(page, code) if t.published_at]
        if published:
            return max(published, key=lambda t: t.version)
    return None


def check_blocks(blocks):
    """Everything wrong with a list of blocks, as sentences naming the block ("Block 2 (recipes): ...")."""
    if not isinstance(blocks, list):
        return ['blocks must be a list']
    errors = []
    for n, block in enumerate(blocks, 1):
        if not isinstance(block, dict) or block.get('kind') not in KINDS:
            errors.append(f'Block {n}: kind must be one of {", ".join(KINDS)}')
            continue
        where = f'Block {n} ({block["kind"]})'
        if set(block) - {'kind', 'settings', 'audience'}:
            errors.append(f'{where}: only kind, settings and audience')
        if block.get('audience', 'all') not in AUDIENCES:
            errors.append(f'{where}: audience must be one of {", ".join(AUDIENCES)}')
        settings = block.get('settings', {})
        if not isinstance(settings, dict):
            errors.append(f'{where}: settings must be an object')
            continue
        errors += [f'{where}: {e}' for e in KINDS[block['kind']].check(settings)]
    return errors


def check_package(data):
    if not isinstance(data, dict):
        return ['the package must be a JSON object']
    errors = []
    if not isinstance(data.get('slug'), str) or not SLUG.match(data['slug']):
        errors.append('slug must be lower case words joined by "-" ("cast-iron-pans")')
    if data.get('kind', 'guide') not in PAGE_KINDS:
        errors.append(f'kind must be one of {", ".join(PAGE_KINDS)}')
    if data.get('lang', DEFAULT_LANG) not in LANGS:
        errors.append(f'lang must be one of {", ".join(LANGS)}')
    if not isinstance(data.get('title'), str) or not data['title'].strip() or len(data['title']) > 200:
        errors.append('title is missing or longer than 200 characters')
    for key in ('summary', 'hero_image', 'note'):
        if data.get(key) is not None and not isinstance(data[key], str):
            errors.append(f'{key} must be text')
    unknown = set(data) - {'slug', 'kind', 'lang', 'title', 'summary', 'hero_image', 'note', 'blocks'}
    if unknown:
        errors.append(f'unknown keys: {", ".join(sorted(unknown))}')
    return errors + check_blocks(data.get('blocks', []))


def save_version(data):
    """A content package -> a new unpublished PageText (the page made when new). Raises ContentError. The caller commits."""
    errors = check_package(data)
    page = find_page(data.get('slug')) if not errors else None
    if page and page.kind != data.get('kind', 'guide'):
        errors.append(f'the page "{page.slug}" is a {page.kind}, not a {data.get("kind", "guide")}')
    if errors:
        raise ContentError(errors)
    if not page:
        page = Page(slug=data['slug'], kind=data.get('kind', 'guide'))
        db.session.add(page)
    lang = data.get('lang', DEFAULT_LANG)
    last = latest_text(page, lang)
    text = PageText(page=page, lang=lang, version=(last.version + 1) if last else 1, title=data['title'].strip(),
                    summary=data.get('summary'), hero_image=data.get('hero_image'), note=data.get('note'),
                    blocks=[{'kind': b['kind'], 'settings': b.get('settings', {}), 'audience': b.get('audience', 'all')}
                            for b in data.get('blocks', [])])
    db.session.add(text)
    db.session.flush()
    return text


def package_of(text):
    """A version as a content package, to edit and save again."""
    return {'slug': text.page.slug, 'kind': text.page.kind, 'lang': text.lang, 'title': text.title,
            'summary': text.summary, 'hero_image': text.hero_image, 'note': None, 'blocks': text.blocks}


def publish(text):
    """Publish this version: visitors see it from now on. An older version is published as a copy, so the newest
    version is always the one shown and the history stays as it was."""
    if text.version != latest_text(text.page, text.lang).version:
        data = package_of(text)
        data['note'] = f'Version {text.version} again'
        text = save_version(data)
    text.published_at = datetime.datetime.utcnow()
    return text


def unpublish(page, lang):
    for t in _texts(page, lang):
        t.published_at = None


def render_blocks(text, user, lang):
    """The blocks this person sees: [{'kind', 'data'}]. A block for another audience, with nothing to show or that
    fails to load is left out (and a failure logged), so one block never breaks the page."""
    signed_in = user is not None
    out = []
    for n, block in enumerate(text.blocks, 1):
        audience = block.get('audience', 'all')
        if (audience == 'signed_in' and not signed_in) or (audience == 'signed_out' and signed_in):
            continue
        try:
            data = KINDS[block['kind']].load(block.get('settings', {}), user, lang)
        except Exception:
            log.exception('Block %s (%s) on page %s failed to load', n, block.get('kind'), text.page.slug)
            continue
        if data is not None:
            out.append({'kind': block['kind'], 'data': data})
    return out


def default_home():
    """The first home page, as a package: what you are cooking, your queue, three rows of dishes and the ways in."""
    return {
        'slug': HOME, 'kind': 'home', 'lang': DEFAULT_LANG, 'title': 'Tonight', 'note': 'The first home page',
        'summary': 'What to cook tonight.',
        'blocks': [
            {'kind': 'text', 'settings': {'style': 'intro', 'markdown': '# What shall we cook tonight?\n\nPick a dish, '
                                          'get the bowls ready and cook it step by step.'}},
            {'kind': 'continue', 'settings': {'title': 'Carry on cooking'}},
            {'kind': 'cook_next', 'settings': {'title': 'Cook next', 'limit': 4}, 'audience': 'signed_in'},
            {'kind': 'recipes', 'settings': {'title': 'Quick tonight', 'text': 'On the table in 30 minutes or less.',
                                             'filter': {'time': '30'}, 'sort': 'quick', 'limit': 6, 'more': True}},
            {'kind': 'recipes', 'settings': {'title': 'New dishes', 'sort': 'new', 'limit': 6, 'more': True}},
            {'kind': 'links', 'settings': {'title': 'Find your way', 'items': [
                {'to': 'discover'}, {'to': 'recipes_list'}, {'to': 'explore_galaxy'}, {'to': 'explore_ingredient_galaxy'}]}},
        ],
    }
