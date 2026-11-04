"""The site's language (services/language.py): what chooses it, the flag, the pages that stay English whatever the
visitor asked for, above all the slides, and that everything marked for translation has Norwegian."""
import json
import os
import re
import sys
from pathlib import Path

import pytest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

os.environ['DB_BACKEND'] = 'local'
os.environ['DATABASE_URL'] = 'sqlite://'
os.environ['STORAGE_BACKEND'] = 'local'
os.environ.setdefault('SECRET_KEY', 'test-secret')
os.environ.setdefault('GOOGLE_API_KEY', 'test-key')
os.environ.pop('K_SERVICE', None)

from babel.messages.frontend import CommandLineInterface  # noqa: E402
from babel.messages.pofile import read_po  # noqa: E402
from flask_babel import get_locale  # noqa: E402

import ai_engine  # noqa: E402
from app import app  # noqa: E402
from database.models import Page, PageText, Recipe, db  # noqa: E402
from scripts import social_render  # noqa: E402
from services import language  # noqa: E402
from services.recipe_v2 import appearance, generate, images, inbox, view  # noqa: E402
from services.recipe_v2.generate import refresh  # noqa: E402
from services.recipe_v2.store import save_v2  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
NORWEGIAN = 'nb-NO,nb;q=0.9,no;q=0.8,en;q=0.7'


@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.app_context():
        db.drop_all()
        db.create_all()
    # Outside the app context: Flask would share one, and with it g, between the client's requests
    yield app.test_client()
    with app.app_context():
        db.session.remove()
        db.drop_all()


def _tikka():
    with open(ROOT / 'data' / 'pilot_v2' / 'fasit' / 'tikka.json', encoding='utf-8') as f:
        data = json.load(f)
    recipe = Recipe(title=data['title'], cuisine='', difficulty='', status='approved', schema_version=2)
    db.session.add(recipe)
    save_v2(recipe, data, {})
    db.session.flush()
    refresh(recipe)
    db.session.commit()
    return recipe


@pytest.fixture
def launched(monkeypatch):
    monkeypatch.setenv('NORWEGIAN_ON', '1')


@pytest.fixture(autouse=True)
def not_launched(monkeypatch):
    monkeypatch.delenv('NORWEGIAN_ON', raising=False)


def chosen(path='/recipes', accept=None, cookie=None):
    headers = {'Accept-Language': accept} if accept else {}
    if cookie:
        headers['Cookie'] = f'lang={cookie}'
    with app.test_request_context(path, headers=headers):
        return language.current()


def html_lang(response):
    return re.search(r'<html lang="([a-z]+)"', response.get_data(as_text=True)).group(1)


# What chooses the language

def test_before_launch_a_norwegian_browser_gets_english():
    assert chosen(accept=NORWEGIAN) == 'en'


@pytest.mark.parametrize('accept, expected', [
    (NORWEGIAN, 'nb'),
    ('no', 'nb'),
    ('nn-NO,nn;q=0.9', 'nb'),
    ('nb', 'nb'),
    ('en-US,en;q=0.9,nb;q=0.8', 'en'),  # English first: the browser's order decides
    ('sv-SE,sv;q=0.9', 'en'),
    ('de-DE,nb;q=0.5', 'nb'),
    ('*', 'en'),
    (None, 'en'),  # bots, the render scripts
])
def test_after_launch_the_browser_chooses(launched, accept, expected):
    assert chosen(accept=accept) == expected


@pytest.mark.parametrize('path, cookie, accept, expected', [
    ('/recipes?lang=no', None, None, 'nb'),
    ('/recipes?lang=nb', None, None, 'nb'),
    ('/recipes?lang=en', 'nb', NORWEGIAN, 'en'),  # the link beats the cookie
    ('/recipes', 'nb', None, 'nb'),
    ('/recipes', 'en', NORWEGIAN, 'en'),  # the choice beats the browser
    ('/recipes?lang=fr', None, None, 'en'),
    ('/recipes', 'fr', None, 'en'),
])
def test_a_choice_works_with_and_without_the_flag(monkeypatch, path, cookie, accept, expected):
    assert chosen(path, accept, cookie) == expected
    monkeypatch.setenv('NORWEGIAN_ON', '1')
    assert chosen(path, accept, cookie) == expected


def test_the_codes_of_the_content_tables():
    assert language.content_code('nb') == 'no'
    assert language.content_code('en') == 'en'


def test_outside_a_request_it_is_english():
    assert language.current() == 'en'
    with app.app_context():
        assert language.current() == 'en'
        assert str(get_locale()) == 'en'


# The pages

def test_lang_link_is_kept_until_changed(client):
    first = client.get('/privacy?lang=no')
    assert html_lang(first) == 'nb'
    assert 'lang=nb' in first.headers['Set-Cookie']
    assert 'HttpOnly' in first.headers['Set-Cookie'] and 'SameSite=Lax' in first.headers['Set-Cookie']
    assert 'Accept-Language' in first.headers['Vary']
    again = client.get('/privacy')
    assert html_lang(again) == 'nb'
    assert 'Set-Cookie' not in again.headers
    assert html_lang(client.get('/privacy?lang=en')) == 'en'
    assert html_lang(client.get('/privacy')) == 'en'


def test_nothing_changes_for_a_visitor_before_launch(client):
    page = client.get('/privacy', headers={'Accept-Language': NORWEGIAN})
    assert html_lang(page) == 'en'
    assert 'data-lang-switch' not in page.get_data(as_text=True)
    assert 'Set-Cookie' not in page.headers


def test_the_switch_after_launch(client, launched):
    html = client.get('/privacy?ref=x').get_data(as_text=True)
    assert 'data-lang-switch' in html
    assert 'href="/privacy?ref=x&amp;lang=nb"' in html
    assert 'Language' in html


def test_the_switch_gets_someone_in_norwegian_back_before_launch(client):
    html = client.get('/privacy?lang=no').get_data(as_text=True)
    assert 'href="/privacy?lang=en"' in html


def test_a_translated_word_shows_and_the_rest_falls_back_to_english(client):
    html = client.get('/privacy?lang=no').get_data(as_text=True)
    assert 'Språk' in html
    assert 'Units' in html  # not translated yet: English, not empty


def test_not_found_and_error_pages_follow_the_language(client):
    assert html_lang(client.get('/no-such-page?lang=no')) == 'nb'


def _text(page, lang, title):
    return PageText(page=page, lang=lang, version=1, title=title, blocks=[], published_at=db.func.now())


def test_guides_and_home_follow_the_language_with_english_as_fallback(client):
    with app.app_context():
        guide = Page(slug='pans', kind='guide')
        only_en = Page(slug='knives', kind='guide')
        db.session.add_all([guide, _text(guide, 'en', 'Pans'), _text(guide, 'no', 'Panner'),
                            only_en, _text(only_en, 'en', 'Knives')])
        db.session.commit()
    assert '>Pans<' in client.get('/guides/pans').get_data(as_text=True)
    assert '>Panner<' in client.get('/guides/pans?lang=no').get_data(as_text=True)
    assert '>Panner<' in client.get('/guides/pans').get_data(as_text=True)  # the choice is kept
    assert '>Knives<' in client.get('/guides/knives').get_data(as_text=True)


def test_admins_lang_is_the_text_they_edit_not_their_choice(client):
    response = client.get('/admin/pages/1?lang=no')  # refused, but must not store a choice on the way
    assert 'Set-Cookie' not in response.headers or 'lang=' not in response.headers['Set-Cookie']
    assert chosen('/admin/pages/1?lang=no') == 'en'


# What stays English

@pytest.mark.parametrize('path', [
    '/social/pantry', '/social/post', '/social/week', '/social/recipe/1/map', '/admin/funnel', '/admin/inbox',
    '/new-recipe', '/new-recipe/v2/batch', '/new-ingredient', '/explore/galaxy', '/explore/ingredient-galaxy',
    '/mirror', '/api/social/drafts', '/api/content/pages', '/api/review/pantry', '/internal/tasks/social-stats',
])
def test_english_only_pages_ignore_every_way_of_asking(launched, path):
    assert chosen(f'{path}?lang=no', NORWEGIAN, 'nb') == 'en'


@pytest.mark.parametrize('path', ['/', '/discover', '/recipes', '/recipe/1', '/recipe/1/print', '/login', '/register',
                                  '/privacy', '/guides/x', '/ingredients', '/saved-recipes', '/next-recipes',
                                  '/post/instagram/1', '/api/feed/recipes', '/api/recipes/count'])
def test_the_flow_is_not_english_only(path):
    assert not language.english_only(path)


def test_every_slide_route_and_admin_route_is_english_only():
    rules = [r.rule for r in app.url_map.iter_rules()]
    slides = [r for r in rules if r.startswith('/social/')]
    assert slides
    for rule in slides + [r for r in rules if r.startswith('/admin')]:
        assert language.english_only(rule), rule


@pytest.mark.parametrize('fmt, recipe', [('series', None), ('pantry', None), ('week', None), ('map', 1), ('grid', 1)])
def test_the_render_script_only_reads_english_pages(fmt, recipe):
    url = social_render.page_url('https://x', fmt, recipe, size='tt', slide=1)
    assert language.english_only(url.removeprefix('https://x').split('?')[0])


def test_slides_ask_babel_for_english(launched):
    with app.test_request_context('/social/pantry?lang=no', headers={'Accept-Language': NORWEGIAN, 'Cookie': 'lang=nb'}):
        assert str(get_locale()) == 'en'


def test_slides_are_the_same_whoever_looks(client, launched):
    with app.app_context():
        recipe_id = _tikka().id
    for path in (f'/social/recipe/{recipe_id}/map', '/social/pantry'):
        plain = client.get(f'{path}?size=tt&slide=1')
        assert plain.status_code == 200, path
        client.set_cookie('lang', 'nb')
        asked = client.get(f'{path}?size=tt&slide=1&lang=no', headers={'Accept-Language': NORWEGIAN})
        client.delete_cookie('lang')
        assert asked.get_data() == plain.get_data(), path
        assert html_lang(plain) == 'en'
        assert 'Set-Cookie' not in asked.headers


def test_as_text_goes_to_claude_in_the_base_language(client, monkeypatch):
    real, seen = view.fmt_amount, []

    def spy(*args, **kwargs):
        seen.append(str(get_locale()))
        return real(*args, **kwargs)

    monkeypatch.setattr(view, 'fmt_amount', spy)
    with app.app_context():
        base = view.as_text(_tikka())
    seen.clear()
    with app.test_request_context('/recipes?lang=no'):
        assert str(get_locale()) == 'nb'
        assert view.as_text(db.session.scalars(db.select(Recipe)).first()) == base
        assert str(get_locale()) == 'nb'  # back afterwards
    assert seen and set(seen) == {'en'}


@pytest.mark.parametrize('module', [ai_engine, generate, images, appearance, inbox], ids=lambda m: m.__name__)
def test_prompts_are_drawn_without_translation(module):
    assert '_' not in module.env.globals


# The translations

def test_everything_marked_has_norwegian(tmp_path):
    pot = tmp_path / 'messages.pot'
    CommandLineInterface().run(['pybabel', '--quiet', 'extract', '-F', str(ROOT / 'babel.cfg'), '-k', 'lazy_gettext',
                                '--no-location', '-o', str(pot)]
                               + [str(ROOT / d) for d in ('routes', 'services', 'utils', 'templates')])
    with open(pot, encoding='utf-8') as f:
        marked = {m.id for m in read_po(f) if m.id}
    assert marked
    with open(ROOT / 'translations' / 'nb' / 'LC_MESSAGES' / 'messages.po', encoding='utf-8') as f:
        catalog = read_po(f)
    missing = sorted(m for m in marked
                     if not (catalog.get(m) and catalog.get(m).string and not catalog.get(m).fuzzy))
    assert not missing, f'no Norwegian in translations/nb/LC_MESSAGES/messages.po for: {missing}'


def test_the_build_compiles_the_translations():
    dockerfile = (ROOT / 'Dockerfile').read_text(encoding='utf-8')
    assert 'pybabel compile -d translations' in dockerfile
    assert dockerfile.index('COPY --chown') < dockerfile.index('pybabel compile')
