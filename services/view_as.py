"""An admin seeing the site as a signed-in user or a visitor, from the admin chip (routes/view_as_routes.py).

The choice is kept in the signed session and read where everyone is signed in, app.load_user: as a visitor no user
comes back, so the whole app sees an anonymous visitor; as a user the account comes back wrapped so it is no admin.
It can only go down: the account behind the session must really be an admin, or the choice counts for nothing.
Nothing is saved meanwhile (guard), visits are not counted (routes/funnel_routes.py), and every page says so (mark_page)."""
import re
from urllib.parse import urlsplit

from flask import flash, g, has_request_context, jsonify, redirect, render_template, request, session, url_for
from flask_login import UserMixin, user_logged_in, user_logged_out
from sqlalchemy import event

from database.models import User, db

KEY = 'view_as'
ROLES = {'user': 'signed-in user', 'visitor': 'visitor'}
HEADER = 'X-View-As'  # on a refused fetch, so the bar can say why nothing happened
SAFE_METHODS = {'GET', 'HEAD', 'OPTIONS'}
# POSTs that save nothing: the switch itself, leaving, and a search that happens to use POST
ALLOWED_WRITES = {'view_as.switch', 'logout', 'search_ingredients_api'}
# GETs that save something: signing in with Google, and the partner code /mirror makes on the first visit
WRITES_ON_GET = {'google_start', 'google_done', 'mirror_hub'}
BODY, TITLE = re.compile(r'<body\b[^>]*>', re.I), re.compile(r'</title>', re.I)  # a plain error page has no body tag


class SignedInView(UserMixin):
    """The account as a signed-in user sees it: everything comes from the account except is_admin. A wrapper, so that
    is_admin is never set on the database object, where a commit could save it and lock the admin out."""
    is_admin = False

    def __init__(self, user):
        self._user = user

    def __getattr__(self, name):
        return getattr(self._user, name)


class ViewOnly(Exception):
    """Something tried to save while an admin is viewing the site as someone else (guard's safety net)."""


def account():
    """The account really signed in, from the session, whatever it is viewing the site as."""
    user_id = session.get('_user_id')
    return db.session.get(User, int(user_id)) if user_id else None


def role():
    """What this admin is viewing the site as, or None. A value left in the session counts only for a real admin."""
    chosen = session.get(KEY)
    if chosen not in ROLES:
        return None
    user = account()
    return chosen if user is not None and user.is_admin else None


def seen_as(user):
    """What app.load_user hands the app for the account."""
    chosen = role()
    if chosen == 'visitor':
        return None
    return SignedInView(user) if chosen == 'user' else user


def _message():
    """Says it is the preview that stopped it, not what the people it shows are allowed to do."""
    real = ' For a real signed-in user this works as normal.' if g.view_as == 'user' else ''
    return f'Not saved, because this is only a preview.{real}'


def refusal():
    """A form goes back where it came from with the message; a fetch gets it as JSON, and the bar shows it."""
    if 'text/html' not in request.headers.get('Accept', ''):
        return jsonify({'error': _message(), 'success': False}), 403, {HEADER: g.view_as}
    flash(_message(), 'info')
    came_from = urlsplit(request.referrer or '')
    back = came_from.path if came_from.netloc == request.host and came_from.path != request.path else None
    return redirect((back + (f'?{came_from.query}' if came_from.query else '')) if back else url_for('content.home'))


def _saves():
    if request.method not in SAFE_METHODS:
        return request.endpoint not in ALLOWED_WRITES
    # /login?do=save does what was pressed when someone is signed in already
    pressed = request.endpoint in ('login', 'register') and request.args.get('do') and g.view_as == 'user'
    return request.endpoint in WRITES_ON_GET or bool(pressed)


def guard():
    """Runs before every request (app.py): no saving while viewing the site as someone else."""
    g.view_as = role()
    if g.view_as and _saves():
        return refusal()
    return None


@event.listens_for(db.session, 'before_flush')
def _no_saving(session_, flush_context, instances):
    """The safety net under guard: a GET nobody knew saved something stops here rather than save it."""
    if has_request_context() and g.get('view_as') and (session_.new or session_.dirty or session_.deleted):
        raise ViewOnly()


def mark_page(response):
    """Runs after every request (app.py): the bar on every page while viewing, whatever layout the page has. Not on a
    sandboxed interactive, which has a page of its own around it, and nothing the browser could keep and show later."""
    chosen = g.get('view_as')
    if not chosen or response.mimetype != 'text/html' or response.direct_passthrough:  # (an abort counts as streamed)
        return response
    response.headers['Cache-Control'] = 'no-store'
    if response.status_code // 100 == 3 or 'Content-Security-Policy' in response.headers:
        return response
    html = response.get_data(as_text=True)
    body = BODY.search(html)
    place = body or TITLE.search(html)
    if place:
        bar = render_template('components/view_as_bar.html', seen_as=ROLES[chosen], header=HEADER, note=_message())
        fit = '' if body else '<meta name="viewport" content="width=device-width, initial-scale=1">'  # so a phone sees the bar
        response.set_data(html[:place.end()] + fit + bar + html[place.end():])
    return response


def _forget(sender, user, **extra):
    session.pop(KEY, None)


user_logged_in.connect(_forget)
user_logged_out.connect(_forget)
