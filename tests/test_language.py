"""The site's language (services/language.py): what chooses it, the flag, the pages that stay English whatever the
visitor asked for, above all the slides, and that everything marked for translation has Norwegian."""
import json
import os
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from unittest.mock import patch

import pytest
from sqlalchemy import event

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

os.environ['DB_BACKEND'] = 'local'
os.environ['DATABASE_URL'] = 'sqlite://'
os.environ['STORAGE_BACKEND'] = 'local'
os.environ.setdefault('SECRET_KEY', 'test-secret')
os.environ.setdefault('GOOGLE_API_KEY', 'test-key')
os.environ.pop('K_SERVICE', None)

from babel.messages.frontend import CommandLineInterface  # noqa: E402
from babel.messages.pofile import read_po  # noqa: E402
from flask_babel import force_locale, get_locale  # noqa: E402
from werkzeug.exceptions import InternalServerError  # noqa: E402

import ai_engine  # noqa: E402
from app import app  # noqa: E402
from database.models import Ingredient, Page, PageText, Recipe, RecipeDiet, RecipeTranslation, db  # noqa: E402
from routes._shared import DIFFICULTY_LABELS, MENU, site_menu  # noqa: E402
from routes.error_routes import server_error  # noqa: E402
from routes.recipes_routes import VIEWS  # noqa: E402
from scripts import social_render  # noqa: E402
from services import google_signin, labels, language  # noqa: E402
from services.ingredient_library import GROUPS  # noqa: E402
from services.measures import SYSTEMS, fmt_amount  # noqa: E402
from services.recipe_library import QUICK, SORT_LABELS, SPICE_LABELS, TIME_LABELS  # noqa: E402
from services.recipe_v2 import translation  # noqa: E402
from services.recipe_v2.derive import HEAT_LABELS  # noqa: E402
from services.recipe_v2.persona import SETTINGS  # noqa: E402
from services.recipe_v2.states import key as state_key  # noqa: E402
from services.recipe_v2.store import to_v2  # noqa: E402
from services.recipe_v2.store import to_v2  # noqa: E402
from services.social_week import WEEK_DAYS  # noqa: E402
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
    with app.test_request_context('/privacy?lang=no'):
        assert labels.label('A new cuisine') == 'A new cuisine'  # no translation yet: English, not empty
        assert labels.label(None) == ''


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


# No English left on a page, in what a visitor reads, the menu and footer too

class Words(HTMLParser):
    """The visible words of a page, and the words in the attributes a person can meet."""
    SKIP = {'script', 'style', 'svg', 'head'}
    SEEN = ('placeholder', 'aria-label', 'title', 'alt', 'data-show', 'data-hide')

    def __init__(self):
        super().__init__()
        self.words, self.skip = [], 0

    def handle_starttag(self, tag, attrs):
        self.skip += tag in self.SKIP
        self.words += [value for name, value in attrs if name in self.SEEN and value]

    def handle_endtag(self, tag):
        self.skip -= tag in self.SKIP

    def handle_data(self, data):
        if not self.skip and data.strip():
            self.words.append(' '.join(data.split()))


# The same in both languages on purpose: names, addresses and the like
SAME_IN_BOTH = {'The Lazy Chef', 'TikTok', 'Instagram', 'Google', '.', '·', '⋯', 'Datatilsynet',
                'thelazychefai@gmail.com', 'Cookies', 'English', 'Norsk', 'US', 'Protein', 'Keto', 'Paleo', 'Grill',
                'Sous vide', 'Snacks', 'Mild', 'Baby', 'Guide', 'Recipe Mirror', '→', ',', 'min', 'Over 45 min',
                'Under 30 min', 'Plan', 'cook@example.no', 'kcal', 'kJ', 'g', 'mg', 'Per 100 g', '\U0001F468\u200d\U0001F373'}  # the last: the loading overlay's chef
NUMBERS = re.compile(r'^(Start )?[\d\s.,:/·+′×−]*(min)?( \+ \d+)?[\s,]*$')  # counts and times


def visible(html):
    """The words of the body: the menu, the page and the footer."""
    words = Words()
    words.feed(html[html.index('<body'):])
    return words.words


def english_left(path, client=None, data=(), **kwargs):
    """What reads the same in both languages and should not. data: what is English until the recipes and ingredients
    are translated (their names). client: signed in; the choice of language is its cookie."""
    client = client or app.test_client()
    client.delete_cookie('lang')
    english = visible(client.get(path, **kwargs).get_data(as_text=True))
    client.set_cookie('lang', 'nb')
    norwegian = visible(client.get(path, **kwargs).get_data(as_text=True))
    client.delete_cookie('lang')
    assert english and len(english) == len(norwegian), path
    same = SAME_IN_BOTH | set(data)
    return [e for e, n in zip(english, norwegian) if e == n and e not in same and not NUMBERS.match(e)]


IPHONE_IN_INSTAGRAM = {'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) Instagram 350.0'}


@pytest.mark.parametrize('path, headers', [
    ('/login', {}), ('/register', {}), ('/privacy', {}), ('/no-such-page', {}),
    ('/login', IPHONE_IN_INSTAGRAM), ('/register', IPHONE_IN_INSTAGRAM),
])
def test_sign_up_log_in_privacy_and_errors_have_no_english_left(client, launched, monkeypatch, path, headers):
    monkeypatch.setattr(google_signin, 'enabled', lambda: True)
    assert english_left(path, headers=headers) == []


@pytest.mark.parametrize('action', ['save', 'queue', 'made'])
@pytest.mark.parametrize('page', ['login', 'register'])
def test_what_was_pressed_is_said_in_norwegian(client, launched, page, action):
    with app.app_context():
        recipe_id = _tikka().id
    assert english_left(f'/{page}?do={action}&recipe={recipe_id}&next=/recipe/{recipe_id}') == []


def _a_recipe():
    """An approved recipe with everything a card shows, and its names, which are English until they are translated."""
    with app.app_context():
        recipe = _tikka()
        recipe.cuisine, recipe.difficulty, recipe.prep_time_mins = 'Indian', 'Moderate', 40
        recipe.settings = ['kid_friendly', 'low_carb']
        recipe.diets.append(RecipeDiet(diet='gluten-free'))
        recipe.image_filename = 'x.png'
        db.session.commit()
        return recipe.id, {recipe.title} | {line.name for line in recipe.lines}


def _signed_in():
    client = app.test_client()
    client.post('/register', data={'email': 'cook@example.no', 'password': 'x'}, follow_redirects=True)  # and the welcome is read
    return client


@pytest.mark.parametrize('path', ['/recipes', '/recipes?sort=quick&diet=vegan&time=30', '/recipes?q=nothing-like-this',
                                  '/discover', '/ingredients', '/ingredients?q=nothing-like-this', '/ingredients?staples=1'])
def test_a_visitor_browsing_meets_no_english(client, launched, path):
    _, names = _a_recipe()
    assert english_left(path, data=names) == []


@pytest.mark.parametrize('path', ['/recipes', '/recipes?view=saved', '/recipes?view=made', '/recipes?view=next', '/discover'])
def test_someone_signed_in_meets_no_english(client, launched, path):
    _, names = _a_recipe()
    assert english_left(path, client=_signed_in(), data=names) == []


def test_the_card_of_something_saved_and_made_has_no_english(client, launched):
    recipe_id, names = _a_recipe()
    cook = _signed_in()
    cook.post(f'/api/recipes/{recipe_id}/favorite')
    cook.post(f'/api/queue/add/{recipe_id}')
    cook.patch(f'/api/interactions/recipe/{recipe_id}/made')
    for path in ('/recipes?view=saved', '/recipes?view=made', '/recipes?view=next'):
        assert english_left(path, client=cook, data=names) == [], path


def _an_ingredient():
    """An active staple in a dish, with its nutrition: (id, its name and the dish's, English until translated)."""
    with app.app_context():
        recipe = _tikka()
        ingredient = Ingredient(food_id='x1', name='Butter', main_category='meat', is_staple=True, status='active',
                                calories_per_100g=700, protein_per_100g=1, carbs_per_100g=1, fat_per_100g=80,
                                sugar_per_100g=1, fiber_per_100g=1, sodium_mg_per_100g=10)
        recipe.lines[0].ingredient = ingredient
        db.session.commit()
        return ingredient.id, {'Butter', 'butter', recipe.title}  # the sheet's fallback title is lower case


def test_the_ingredients_page_with_something_on_it_has_no_english(client, launched):
    _, names = _an_ingredient()
    assert english_left('/ingredients', data=names) == []


def test_the_sheet_of_an_ingredient_has_no_english(client):
    ingredient_id, names = _an_ingredient()
    plain, norsk = app.test_client(), app.test_client()
    norsk.set_cookie('lang', 'nb')
    words = [visible('<body>' + c.get(f'/ingredients/{ingredient_id}/card').get_data(as_text=True)) for c in (plain, norsk)]
    assert len(words[0]) == len(words[1])
    assert [e for e, n in zip(*words) if e == n and e not in SAME_IN_BOTH | names and not NUMBERS.match(e)] == []


def test_every_word_of_the_catalogs_is_a_label():
    def read(path, key):
        return json.loads((ROOT / 'data' / path).read_text(encoding='utf-8'))[key]

    words = (list(read('post_processing/cuisines.json', 'cuisines'))
             + [p['category'] for p in read('constraints/main_protein.json', 'protein_types')]
             + [d.capitalize() for d in read('constraints/diets.json', 'diets')]
             + list(read('constraints/meal_types.json', 'meal_types'))
             + [c.capitalize() for c in read('constraints/categories.json', 'main_categories')]
             + list(DIFFICULTY_LABELS.values()) + list(HEAT_LABELS.values()) + list(TIME_LABELS.values())
             + list(SORT_LABELS.values()) + list(SPICE_LABELS.values()) + list(SYSTEMS.values()) + list(WEEK_DAYS)
             + [q[2] for q in QUICK] + [g[0] for g in GROUPS.values()] + [v[1] for v in VIEWS]
             + [t.replace('_', ' ').capitalize() for t in SETTINGS]
             + [item[0] for g in MENU if g[0] != 'Admin' for item in g[2] if item] + [g[0] for g in MENU if g[0] != 'Admin'])
    assert sorted(set(words) - set(labels.WORDS)) == []


def test_every_word_a_script_says_is_in_the_dictionary():
    said = set()
    for path in [*(ROOT / 'static' / 'js').glob('*.js'), *(ROOT / 'templates').rglob('*.html')]:
        for found in re.findall(r"\btr\(\s*(?:[\w.]+\s*(?:===\s*\w+\s*)?\?\s*)?'([^']+)'(?:\s*:\s*'([^']+)')?", path.read_text(encoding='utf-8')):
            said |= {w for w in found if w}
    assert said
    assert sorted(said - set(labels.JS_WORDS)) == []


def test_the_scripts_get_their_words_in_the_language_of_the_page(client):
    assert 'window.WORDS = {};' in client.get('/privacy').get_data(as_text=True)
    html = client.get('/privacy?lang=no').get_data(as_text=True)
    assert '"Saved. Thank you.": "Lagret. Takk."' in html


def test_the_filters_still_filter_on_the_english_values(client):
    _a_recipe()
    client.set_cookie('lang', 'nb')
    html = client.get('/recipes?cuisine=Indian').get_data(as_text=True)
    assert 'value="Indian"' in html and '>Indisk<' in html and 'rcard-cuisine">Indisk<' in html
    assert client.get('/api/recipes/count?cuisine=Indian').get_json()['total'] == 1
    assert client.get('/api/recipes/count?cuisine=Thai').get_json()['total'] == 0


def test_discover_gets_its_cards_in_the_language(client):
    _a_recipe()
    assert client.get('/api/feed/recipes').get_json()['recipes'][0]['cuisine'] == 'Indian'
    client.set_cookie('lang', 'nb')
    card = client.get('/api/feed/recipes').get_json()['recipes'][0]
    assert (card['cuisine'], card['difficulty_label'], card['diets']) == ('Indisk', 'Middels', ['Glutenfri'])


def test_the_admin_group_of_the_menu_stays_english():
    with app.test_request_context('/recipes?lang=no'):
        assert [item for item in MENU if item[0] == 'Admin'][0][2][0][0] == 'New recipe'
        with patch('routes._shared.current_user', type('Admin', (), {'is_authenticated': True, 'is_admin': True})()):
            menu = {g['label']: g for g in site_menu()}
    assert 'Oppskrifter' in menu and 'Admin' in menu
    assert 'Recipes' in [i['label'] for i in menu['Admin']['items'] if i]


def test_the_page_for_an_error_on_our_side_has_no_english_left():
    def rendered(path):
        with app.test_request_context(path):
            return visible(server_error(InternalServerError())[0])

    english, norwegian = rendered('/recipes'), rendered('/recipes?lang=no')
    assert [e for e, n in zip(english, norwegian) if e == n and e not in SAME_IN_BOTH] == []


def _post(client, path, **form):
    client.set_cookie('lang', 'nb')
    return client.post(path, data=form, follow_redirects=True).get_data(as_text=True)


def test_the_messages_of_signing_up_and_in_are_norwegian(client):
    assert 'E-posten og passordet stemmer ikke.' in _post(client, '/login', email='a@b.no', password='x')
    assert 'Skriv inn e-post og passord.' in _post(client, '/register', email='', password='')
    welcome = _post(client, '/register', email='a@b.no', password='x')
    assert 'Velkommen til The Lazy Chef.' in welcome and 'Disse står på bordet på 30 minutter.' in welcome
    assert 'Du er logget ut.' in _post(client, '/logout')
    assert 'Det finnes allerede en konto' in _post(client, '/register', email='a@b.no', password='y')
    assert 'Logg inn for å se denne siden.' in client.get('/saved-recipes', follow_redirects=True).get_data(as_text=True)


def test_what_was_pressed_is_done_and_said_in_norwegian(client):
    with app.app_context():
        recipe_id = _tikka().id
        title = db.session.get(Recipe, recipe_id).title
    client.set_cookie('lang', 'nb')
    html = client.post(f'/register?do=save&recipe={recipe_id}&next=/privacy', data={'email': 'c@d.no', 'password': 'x'},
                       follow_redirects=True).get_data(as_text=True)
    assert f'{title} er lagret.' in html


def test_a_title_cannot_bring_html_into_the_norwegian(client):
    with app.app_context():
        recipe = _tikka()
        recipe.title = '<b>Bold</b> dish'
        db.session.commit()
        recipe_id = recipe.id
    client.set_cookie('lang', 'nb')
    html = client.get(f'/register?do=save&recipe={recipe_id}').get_data(as_text=True)
    assert '<b>Bold</b> dish' not in html and '&lt;b&gt;Bold&lt;/b&gt; dish' in html


@pytest.mark.parametrize('path, title', [('/login', 'Logg inn'), ('/register', 'Registrer deg'),
                                         ('/privacy', 'Personvern'), ('/no-such-page', 'Fant ikke siden')])
def test_the_tab_title_is_norwegian(client, path, title):
    client.set_cookie('lang', 'nb')
    assert f'<title>{title} - The Lazy Chef</title>' in client.get(path).get_data(as_text=True)


def test_the_show_button_of_the_password_speaks_norwegian(client):
    client.set_cookie('lang', 'nb')
    html = client.get('/login').get_data(as_text=True)
    assert 'data-show="Vis"' in html and 'data-hide="Skjul"' in html


def test_the_privacy_page_names_every_cookie_the_site_sets(client):
    html = client.get('/privacy').get_data(as_text=True)
    assert 'Four, all for the site itself' in html and 'remembers your language' in html


def test_a_cross_site_refusal_speaks_norwegian(client):
    client.set_cookie('lang', 'nb')
    response = client.post('/login', headers={'Sec-Fetch-Site': 'cross-site'})
    assert response.status_code == 403 and 'Forespørselen kom fra et annet nettsted' in response.get_data(as_text=True)


# The recipe page, the cook views and print: only the recipe's own words are English until they are translated

def _recipe_words(recipe):
    """Everything stored in the recipe's own words, lower case: what may still read the same in Norwegian."""
    data = to_v2(recipe)
    return json.dumps([data, recipe.title, recipe.chef_note, recipe.yield_text], ensure_ascii=False).lower()


def _no_amount(word):
    """A pill or tile's words without the amount in front."""
    return re.sub(r'^[\d¼½¾⅓⅔,. ]+(g|kg|ml|cl|dl|l|cm)?\b\s*', '', word).strip(' .,:()').lower()


def english_on_recipe_page(path, recipe_id, client=None):
    client = client or app.test_client()
    with app.app_context():
        own = _recipe_words(db.session.get(Recipe, recipe_id))
    client.delete_cookie('lang')
    english = visible(client.get(path).get_data(as_text=True))
    client.set_cookie('lang', 'nb')
    norwegian = visible(client.get(path).get_data(as_text=True))
    client.delete_cookie('lang')
    assert english and len(english) == len(norwegian), path
    return [e for e, n in zip(english, norwegian)
            if e == n and e not in SAME_IN_BOTH and not NUMBERS.match(e)
            and not all(_no_amount(part) in own for part in re.sub(r'\d+°', '', e).split(','))]


def test_a_visitor_on_the_recipe_page_meets_only_the_recipes_own_words(client, launched):
    recipe_id, _ = _a_recipe()
    assert english_on_recipe_page(f'/recipe/{recipe_id}', recipe_id) == []


def test_a_cook_on_the_recipe_page_meets_only_the_recipes_own_words(client, launched):
    recipe_id, _ = _a_recipe()
    cook = _signed_in()
    cook.post(f'/api/interactions/recipe/{recipe_id}/cooked')
    cook.post(f'/api/interactions/recipe/{recipe_id}/feedback', data={'rating': '4', 'comment': 'x'})
    assert english_on_recipe_page(f'/recipe/{recipe_id}', recipe_id, client=cook) == []


def test_print_meets_only_the_recipes_own_words(client, launched):
    recipe_id, _ = _a_recipe()
    assert english_on_recipe_page(f'/recipe/{recipe_id}/print?auto=0', recipe_id) == []


def test_the_recipes_facts_are_in_the_language(client):
    recipe_id, _ = _a_recipe()
    with app.app_context():
        recipe = db.session.get(Recipe, recipe_id)
        recipe.keeps_days, recipe.freezes, recipe.spice_level, recipe.protein_type = 2, True, 1, 'Chicken'
        recipe.settings = ['kid_friendly']
        db.session.commit()
    client.set_cookie('lang', 'nb')
    html = client.get(f'/recipe/{recipe_id}').get_data(as_text=True)
    for word in ('2 dager i kjøleskapet, kan fryses', 'Litt sterk', 'Kylling', 'Barnevennlig', 'Indisk', 'Middels'):
        assert word in html, word


def test_the_page_built_for_one_language_is_not_served_to_the_other(client):
    recipe_id, _ = _a_recipe()
    view.clear_cache()
    first = client.get(f'/recipe/{recipe_id}').get_data(as_text=True)
    client.set_cookie('lang', 'nb')
    norwegian = client.get(f'/recipe/{recipe_id}').get_data(as_text=True)
    client.delete_cookie('lang')
    again = client.get(f'/recipe/{recipe_id}').get_data(as_text=True)
    assert 'Forberede' in norwegian and 'Forberede' not in first
    assert first == again


@pytest.mark.parametrize('amount, unit, english, norwegian', [
    (2, 'tbsp', '2 tbsp', '2 ss'), (1.5, 'tsp', '1½ tsp', '1½ ts'), (2, 'clove', '2 cloves', '2 fedd'), (1, 'clove', '1 clove', '1 fedd'),
    (3, 'slice', '3 slices', '3 skiver'), (2.5, 'dl', '2½ dl', '2½ dl'), (7.5, 'g', '7.5 g', '7,5 g'), (0.5, 'ml', '0.5 ml', '0,5 ml'),
    (400, 'g', '400 g', '400 g'), (3, 'piece', '3', '3'),
])
def test_units_and_the_decimal_comma(amount, unit, english, norwegian):
    assert fmt_amount(amount, unit) == english
    with app.test_request_context('/recipes?lang=no'):
        assert fmt_amount(amount, unit) == norwegian
        with force_locale('en'):
            assert fmt_amount(amount, unit) == english


def test_hours_have_a_comma_in_norwegian():
    assert (view.duration(150), view.duration(120), view.duration(45)) == ('2.5 h', '2 h', '45 min')
    with app.test_request_context('/recipes?lang=no'):
        assert (view.duration(150), view.duration(120), view.duration(45)) == ('2,5 t', '2 t', '45 min')


def test_equipment_modes_and_states_use_the_catalogs_norwegian(client):
    recipe_id, _ = _a_recipe()
    with app.test_request_context(f'/recipe/{recipe_id}?lang=no'):
        built = view.page(db.session.get(Recipe, recipe_id))
        catalog = {e['name_en']: e['name'] for e in json.loads((ROOT / 'data/constraints/equipment.json').read_text(encoding='utf-8'))['equipment'] if e.get('name_en')}
        assert built['equipment'] and all(e['name'] in catalog.values() for e in built['equipment'])
        states_shown = {p['cut_word'] for p in built['pictured'].values() if p['cut_word']}
        words = {s['nb'] for s in appearance_states()['states']} | {g['nb'] for g in appearance_states()['grades']}
        assert states_shown and all(set(w.split(' (')[0].split(' ')) <= set(' '.join(words).split(' ')) for w in states_shown)
        assert 'kuttet' in str(state_key())
    assert 'cut' in str(state_key()) and 'kuttet' not in str(state_key())


def appearance_states():
    return json.loads((ROOT / 'data/constraints/states.json').read_text(encoding='utf-8'))


def test_the_shared_parts_on_a_slide_stay_english(client, launched):
    recipe_id, _ = _a_recipe()
    client.set_cookie('lang', 'nb')
    html = client.get(f'/social/recipe/{recipe_id}/map?size=tt&slide=1&lang=no', headers={'Accept-Language': NORWEGIAN}).get_data(as_text=True)
    assert 'Forberede' not in html and 'Kokkelere' not in html and ' ss ' not in html


def test_v2_text_for_claude_is_english_whoever_looks(client):
    with open(ROOT / 'data' / 'pilot_v2' / 'fasit' / 'tikka.json', encoding='utf-8') as f:
        data = json.load(f)
    base = view.v2_text(data)
    with app.test_request_context('/recipes?lang=no'):
        assert view.v2_text(data) == base


def test_the_macros_that_set_a_variable_do_not_hide_the_translation_function():
    for name in ('step_list', 'whole_dish'):
        assert '{% set _ =' not in (ROOT / 'templates' / 'components' / f'{name}.html').read_text(encoding='utf-8')


# The translations

def test_everything_marked_has_norwegian(tmp_path):
    pot = tmp_path / 'messages.pot'
    CommandLineInterface().run(['pybabel', '--quiet', 'extract', '-F', str(ROOT / 'babel.cfg'), '-k', 'lazy_gettext',
                                '--no-location', '-o', str(pot)]
                               + [str(ROOT / d) for d in ('app.py', 'routes', 'services', 'utils', 'templates')])
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


# A recipe's words in Norwegian (services/recipe_v2/translation.py). Requests run outside the app context the data is
# set up in, or they would share its session and its choice of language.
def _norwegian(words):
    return {k: _norwegian(v) for k, v in words.items()} if isinstance(words, dict) else f'{words} NB'


def _english_recipe(title='Pasta'):
    recipe_id, _ = _a_recipe()
    recipe = db.session.get(Recipe, recipe_id)
    recipe.language, recipe.title = 'en', title
    db.session.commit()
    view.clear_cache()
    return recipe


def _translated_recipe(title='Pasta'):
    """The id, a line's name and a step's short of an English recipe with a Norwegian translation."""
    with app.app_context():
        recipe = _english_recipe(title)
        translation.save(recipe, 'nb', _norwegian(translation.source(recipe)))
        db.session.commit()
        return recipe.id, recipe.lines[0].name, recipe.steps[0].short


def test_a_translated_recipe_shows_in_norwegian_and_stays_as_written_in_english(client):
    recipe_id, line, short = _translated_recipe()
    norwegian = client.get(f'/recipe/{recipe_id}?lang=no').get_data(as_text=True)
    english = client.get(f'/recipe/{recipe_id}?lang=en').get_data(as_text=True)
    assert 'Pasta NB' in norwegian and f'{line} NB' in norwegian and f'{short} NB' in norwegian and 'lang="nb"' in norwegian
    assert ' NB' not in english


def test_the_pills_in_a_translated_step_still_work(client):
    recipe_id, line, _ = _translated_recipe()
    html = client.get(f'/recipe/{recipe_id}?lang=no').get_data(as_text=True)
    assert 'class="pill" data-l="' in html and not re.search(r'\{i\d+\}', html)


def test_a_translation_with_something_wrong_is_not_saved(client):
    with app.app_context():
        recipe = _english_recipe()
        step = next(s for s in recipe.steps if '{' in s.text).local_id

        def refused(change):
            words = _norwegian(translation.source(recipe))
            change(words)
            with pytest.raises(ValueError):
                translation.save(recipe, 'nb', words)
        refused(lambda w: w['steps'].pop(step))
        refused(lambda w: w['steps'][step].update(text='Ingen plassholdere'))
        refused(lambda w: w['steps'][step].update(text=w['steps'][step]['text'] + ' {i999}'))
        refused(lambda w: w['steps'][step].update(short='  '))
        refused(lambda w: w['lines'].update(gone={'name': 'x'}))
        refused(lambda w: w.pop('title'))
        assert db.session.get(RecipeTranslation, (recipe.id, 'nb')) is None


def test_the_translation_lasts_as_long_as_the_words(client):
    recipe_id, _, short = _translated_recipe()
    with app.app_context():
        recipe = db.session.get(Recipe, recipe_id)
        words = translation.source(recipe)
        assert translation.source_hash(dict(reversed(list(words.items())))) == translation.source_hash(words)
        recipe.revision = (recipe.revision or 1) + 1  # saved again, the same words
        db.session.commit()
        assert translation.of(recipe, 'nb')['title'] == 'Pasta NB'
        recipe.steps[0].short = 'Something else entirely'
        recipe.revision += 1
        db.session.commit()
        assert translation.of(recipe, 'nb') is None
    html = client.get(f'/recipe/{recipe_id}?lang=no').get_data(as_text=True)
    assert 'Something else entirely' in html and f'{short} NB' not in html and 'Pasta NB' not in html


def test_a_local_id_that_is_gone_breaks_nothing(client):
    with app.app_context():
        v2 = to_v2(_english_recipe())
        shorts = [s['short'] for s in v2['steps']]
        translation.apply(v2, {'title': 'T', 'steps': {'gone': {'short': 'x'}}, 'components': {'gone': {'name': 'y'}}})
        assert v2['title'] == 'T' and [s['short'] for s in v2['steps']] == shorts


def test_a_recipe_written_in_norwegian_needs_no_translation(client):
    with app.app_context():
        recipe = _english_recipe('Norsk rett')
        recipe.language = 'nb'
        db.session.commit()
        recipe_id = recipe.id
        assert translation.of(recipe, 'nb') is None and translation.of(recipe, 'no') is None
        assert translation.titles([recipe], 'nb') == {}
        with pytest.raises(ValueError):
            translation.save(recipe, 'no', _norwegian(translation.source(recipe)))
    for lang in ('no', 'en'):
        assert 'Norsk rett' in client.get(f'/recipe/{recipe_id}?lang={lang}').get_data(as_text=True)


def test_no_is_nb_in_the_recipe_tables(client):
    with app.app_context():
        recipe = _english_recipe()
        row = translation.save(recipe, 'no', _norwegian(translation.source(recipe)))
        db.session.commit()
        assert row.language == 'nb' == language.recipe_code('no') == language.recipe_code('nb')
        assert translation.of(recipe, 'no')['title'] == 'Pasta NB'


def test_titles_for_a_page_take_one_query_and_english_takes_none(client):
    with app.app_context():
        recipe = _english_recipe()
        translation.save(recipe, 'nb', _norwegian(translation.source(recipe)))
        db.session.commit()
        others = [Recipe(title=f'Other {n}', cuisine='', difficulty='', language='en') for n in range(5)]
        db.session.add_all(others)
        db.session.commit()
        asked = []

        def seen(conn, cursor, statement, *rest):
            if 'recipe_translation' in statement:
                asked.append(statement)
        event.listen(db.engine, 'before_cursor_execute', seen)
        try:
            assert translation.titles([recipe, *others], 'nb') == {recipe.id: 'Pasta NB'}
            assert len(asked) == 1
            assert translation.titles([recipe, *others], 'en') == {}
            assert len(asked) == 1
        finally:
            event.remove(db.engine, 'before_cursor_execute', seen)


def test_a_card_shows_the_translated_title_until_the_title_changes(client):
    recipe_id, _, _ = _translated_recipe()
    assert 'Pasta NB' in client.get('/recipes?lang=no').get_data(as_text=True)
    assert 'Pasta NB' not in client.get('/recipes?lang=en').get_data(as_text=True)
    with app.app_context():
        db.session.get(Recipe, recipe_id).title = 'Pasta again'
        db.session.commit()
    html = client.get('/recipes?lang=no').get_data(as_text=True)
    assert 'Pasta NB' not in html and 'Pasta again' in html


def test_deleting_a_recipe_takes_its_translation(client):
    recipe_id, _, _ = _translated_recipe()
    with app.app_context():
        db.session.delete(db.session.get(Recipe, recipe_id))
        db.session.commit()
        assert db.session.get(RecipeTranslation, (recipe_id, 'nb')) is None


def test_an_ingredient_has_its_norwegian_name_when_there_is_one(client):
    with app.app_context():
        ingredient = Ingredient(food_id='999901', name='testitem', status='active')
        db.session.add(ingredient)
        db.session.commit()
    assert 'testitem' in client.get('/ingredients?lang=no&q=testitem').get_data(as_text=True)
    with app.app_context():
        db.session.execute(db.select(Ingredient).filter_by(food_id='999901')).scalar_one().name_nb = 'Norsk  Navn'
        db.session.commit()
    assert 'norsk navn' in client.get('/ingredients?lang=no&q=norsk').get_data(as_text=True)
    english = client.get('/ingredients?lang=en&q=testitem').get_data(as_text=True)
    assert 'testitem' in english and 'norsk navn' not in english
