"""CSRF: a request that changes something must come from this site's own pages. A browser says where a request comes
from and a page cannot forge it: Sec-Fetch-Site in every browser since 2023, Origin before that. Scripts send neither
(Cloud Tasks with its OIDC token, the API with its key, curl): they hold no visitor's cookie, so they pass and answer
to their own checks. So no tokens: nothing to add to a form or a fetch, and nothing goes stale in a tab left open while
cooking. The session and remember cookies are also SameSite=Lax (app.py), for a browser that sends neither header."""
from urllib.parse import urlsplit

from flask import current_app, request
from flask_babel import gettext

SAFE_METHODS = {'GET', 'HEAD', 'OPTIONS'}
OWN_SITE = {'same-origin', 'none'}  # none: the visitor's own doing, not a page's


def _from_elsewhere():
    site = request.headers.get('Sec-Fetch-Site')
    if site:
        return site not in OWN_SITE
    origin = request.headers.get('Origin')
    return bool(origin) and urlsplit(origin).netloc != request.host  # "null", a sandboxed frame, has no netloc


def refuse_cross_site():
    """Runs before every request (app.py)."""
    if request.method not in SAFE_METHODS and _from_elsewhere():
        current_app.logger.warning('Refused cross-site %s %s (Sec-Fetch-Site %s, Origin %s)', request.method, request.path,
                                   request.headers.get('Sec-Fetch-Site'), request.headers.get('Origin'))
        return gettext('This request came from another site, so it was not carried out. Go back to the page and try again.'), 403, {'Content-Type': 'text/plain; charset=utf-8'}
    return None
