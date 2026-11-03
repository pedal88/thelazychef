"""Errors Blueprint: an address that does not exist and an error on our side, in the site's look; and the short
addresses from the posts when they are typed a little differently by hand (/TikTok/4, /tiktok/4/, /instagram/4)."""
import re

from flask import Blueprint, redirect, render_template, request

errors_bp = Blueprint('errors', __name__)

SHORT = re.compile(r'/(tiktok|tt|ig|instagram)(/[\w-]+)?/?', re.IGNORECASE)
SAME = {'tt': 'tiktok', 'instagram': 'ig'}


def _not_for_people():
    """Scripts and files keep the plain answer: nobody reads it, and a missing image should not draw a whole page."""
    return request.path.startswith(('/api/', '/internal/', '/static/'))


def _short_address():
    """The address it should have been (routes/funnel_routes.py has the real ones), or None when it is not one of them."""
    match = SHORT.fullmatch(request.path)
    if not match or request.method not in ('GET', 'HEAD'):
        return None
    channel = match[1].lower()
    address = f'/{SAME.get(channel, channel)}{(match[2] or "").lower()}'
    if address == request.path:
        return None
    return address + (f'?{request.query_string.decode()}' if request.query_string else '')


@errors_bp.app_errorhandler(404)
def not_found(error):
    if _not_for_people():
        return error
    address = _short_address()
    if address:
        return redirect(address)
    return render_template('errors/404.html'), 404


@errors_bp.app_errorhandler(500)
def server_error(error):
    """On its own page, not on base.html: the menu reads the signed-in user, and the database may be what failed."""
    if _not_for_people():
        return error
    return render_template('errors/500.html'), 500
