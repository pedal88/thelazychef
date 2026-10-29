"""The funnel from TikTok and Instagram to the app (services/funnel.py): the short addresses people type from a post,
the ref code any page can carry (?ref=ig-3), and the admin Funnel page."""
from flask import Blueprint, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from services import funnel
from utils.decorators import admin_required

funnel_bp = Blueprint('funnel', __name__)


@funnel_bp.before_app_request
def keep_ref():
    """?ref= on any page a visitor opens is kept for the session (the first one only) and counted."""
    if request.method == 'GET' and 'ref' in request.args and not current_user.is_authenticated:
        funnel.remember(request.args.get('ref'))


# The short addresses on the posts and in the TikTok bio, which has no link: thelazychef.app/tiktok, /ig, and /tiktok/3
# for one post (the code tiktok-3). They keep the code and open the home page.
def _short_link(channel, code):
    if not current_user.is_authenticated:
        funnel.remember(f'{channel}-{code}' if code else channel)
    return redirect(url_for('content.home'))


# The last route listed is registered first and is the address; the shorter alias above it redirects there.
@funnel_bp.route('/tt', defaults={'code': None})
@funnel_bp.route('/tiktok/<code>')
@funnel_bp.route('/tiktok', defaults={'code': None})
def tiktok(code):
    return _short_link('tiktok', code)


@funnel_bp.route('/instagram', defaults={'code': None})
@funnel_bp.route('/ig/<code>')
@funnel_bp.route('/ig', defaults={'code': None})
def instagram(code):
    return _short_link('instagram', code)


@funnel_bp.route('/admin/funnel')
@login_required
@admin_required
def dashboard():
    return render_template('admin/funnel.html', r=funnel.report(), labels=funnel.CHANNEL_LABELS)
