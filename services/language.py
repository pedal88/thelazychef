"""Which language a person sees the site in, and the codes for it. The site speaks 'en' (the base, every source string)
and 'nb'; the words are in translations/ (Flask-Babel, docs/README_TOP_COMMANDS.md), and whatever is not translated
stays English.

The choice, first that holds: pages that stay English always do (ENGLISH_ONLY); ?lang=no|nb|en, kept in a cookie; the
cookie; the browser's language; English. The browser's language and the switch in the menu wait for NORWEGIAN_ON, so
until launch only someone who asks with ?lang=no sees Norwegian.
"""
import os
import urllib.parse

from flask import current_app, has_request_context, request

DEFAULT = 'en'
NAMES = {'en': 'English', 'nb': 'Norsk'}  # the switch: each language in its own name
ASKED = {'en': 'en', 'nb': 'nb', 'no': 'nb'}  # ?lang= and the cookie
BROWSER = {'nb': 'nb', 'no': 'nb', 'nn': 'nb'}  # a Norwegian browser, any of the codes they use
COOKIE = 'lang'
YEAR = 365 * 24 * 3600
# Never translated, whatever the visitor asked for. The slides above all: scripts/social_render.py photographs /social/…,
# drawn from the same parts as the recipe pages, and the posts are in English (tests/test_language.py). Admin pages use
# ?lang= for the language of a page's text they are editing, so here it is not the visitor's choice either.
ENGLISH_ONLY = ('/social', '/admin', '/new-recipe', '/new-ingredient', '/explore', '/mirror', '/internal', '/static',
                '/content/interactive', '/api/content', '/api/social', '/api/review', '/api/admin', '/api/graph',
                '/api/mirror')


def norwegian_on():
    """The launch switch: Norwegian browsers get Norwegian, and everyone gets the switch in the menu."""
    return os.environ.get('NORWEGIAN_ON') == '1'


def english_only(path=None):
    path = request.path if path is None else path
    return any(path == prefix or path.startswith(f'{prefix}/') for prefix in ENGLISH_ONLY)


def _chosen():
    if english_only():
        return DEFAULT
    asked = ASKED.get(request.args.get('lang')) or ASKED.get(request.cookies.get(COOKIE))
    if asked:
        return asked
    if norwegian_on():
        return BROWSER.get(request.accept_languages.best_match(['en', *BROWSER], default=DEFAULT), DEFAULT)
    return DEFAULT


def current():
    """The language of this request; English outside one (scripts, the app's own jobs)."""
    return _chosen() if has_request_context() else DEFAULT


def content_code(code=None):
    """The code of a language in the content tables (PageText.lang), which say 'no' where the site and the recipes say
    'nb'. The one place that maps them; the data stays as it is."""
    code = code or current()
    return 'no' if code == 'nb' else code


def switch():
    """The switch in the menu, [{'code', 'name', 'url', 'on'}], or nothing: shown after launch, and to anyone already
    in Norwegian so they can get back. Plain links, ?lang= keeps the choice."""
    if english_only() or not (norwegian_on() or current() != DEFAULT):
        return []
    return [{'code': code, 'name': name, 'on': code == current(), 'url': _with_lang(code)} for code, name in NAMES.items()]


def _with_lang(code):
    args = request.args.to_dict(flat=False)
    args['lang'] = [code]
    return f'{request.path}?{urllib.parse.urlencode(args, doseq=True)}'


def remember(response):
    """An after_request: ?lang= is kept for the next pages, and the answer depends on what chose the language."""
    if english_only():
        return response
    response.vary.add('Accept-Language')
    response.vary.add('Cookie')
    asked = ASKED.get(request.args.get('lang'))
    if asked and request.method == 'GET' and request.cookies.get(COOKIE) != asked:
        response.set_cookie(COOKIE, asked, max_age=YEAR, samesite='Lax', httponly=True,
                            secure=current_app.config['SESSION_COOKIE_SECURE'])
    return response
