"""The funnel from TikTok and Instagram to the app (services/funnel.py): the short addresses people type from a post,
the ref code any page can carry (?ref=ig-3), the admin Funnel page, and its post log."""
import datetime

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from database.models import SocialPost, db
from services import funnel
from utils.decorators import admin_required

funnel_bp = Blueprint('funnel', __name__)


@funnel_bp.before_app_request
def keep_ref():
    """?ref= on any page a visitor opens is kept for the session (the first one only) and counted."""
    if request.method == 'GET' and 'ref' in request.args and not current_user.is_authenticated:
        funnel.remember(request.args.get('ref'), request.user_agent.string)


@funnel_bp.app_context_processor
def ref_unseen():
    """base.html asks /ref/seen to count the visit when this session brought a code that is not counted yet."""
    return {'ref_unseen': not current_user.is_authenticated and funnel.unseen()}


@funnel_bp.route('/ref/seen', methods=['POST'])
def ref_seen():
    """The page has been open in a browser for a few seconds: count the session's visit for its code (once). Open to
    anyone, like the short addresses; it counts nothing without a code kept in the session."""
    if not current_user.is_authenticated:
        funnel.seen(request.user_agent.string)
    return '', 204


# The short addresses on the posts and in the TikTok bio, which has no link: thelazychef.app/tiktok, /ig, and /tiktok/3
# for one post (the code tiktok-3). They keep the code and open the home page.
def _short_link(channel, code):
    if not current_user.is_authenticated:
        funnel.remember(f'{channel}-{code}' if code else channel, request.user_agent.string)
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


def _post_page(post, error=None, form=None):
    return render_template('admin/funnel_post.html', post=post, error=error, form=form or {},
                           platforms=funnel.PLATFORMS, formats=funnel.POST_FORMATS, stat_fields=funnel.STAT_FIELDS,
                           statuses=funnel.POST_STATUSES,
                           ref=funnel.post_ref(post) if post.id else None), 400 if error else 200


@funnel_bp.route('/admin/funnel/posts/new', methods=['GET', 'POST'])
@login_required
@admin_required
def new_post():
    """A post for the log. scripts/social_render.py prints this address with the platform, code, format and recipe
    filled in; an empty code is the next free one."""
    if request.method == 'POST':
        post = SocialPost()
        error = funnel.save_post(post, request.form)
        if error:
            db.session.rollback()
            return _post_page(SocialPost(), error, request.form)
        flash(f'Logged {funnel.post_ref(post)}.', 'success')
        return redirect(url_for('funnel.edit_post', post_id=post.id))
    args = request.args
    form = {'platform': args.get('platform', 'tiktok'), 'code': args.get('code') or funnel.next_code(),
            'format': args.get('format', 'map'), 'recipe_id': args.get('recipe', ''),
            'posted_on': datetime.date.today().isoformat()}
    return _post_page(SocialPost(), form=form)


@funnel_bp.route('/admin/funnel/posts/<int:post_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_post(post_id):
    """A logged post: what it is, and its numbers from the platform, a row per day after it went up."""
    post = db.session.get(SocialPost, post_id) or abort(404)
    if request.method == 'POST':
        save = funnel.save_stat if request.form.get('part') == 'stats' else funnel.save_post
        error = save(post, request.form)
        if error:
            db.session.rollback()
            return _post_page(post, error, request.form)
        flash('Saved.', 'success')
        return redirect(url_for('funnel.edit_post', post_id=post.id))
    return _post_page(post)


@funnel_bp.route('/admin/funnel/numbers', methods=['GET', 'POST'])
@login_required
@admin_required
def numbers():
    """The numbers sheet: every post that went up on one date, ?day=2 or 7 days later (?on=, default that many days
    ago), on ?platform= or both, in one table to copy the platform's numbers into at once."""
    values = request.values
    day = values.get('day', 7, type=int)
    if day not in funnel.SHEET_DAYS:
        day = 7
    try:
        on = datetime.date.fromisoformat(values.get('on') or '')
    except ValueError:
        on = datetime.date.today() - datetime.timedelta(days=day)
    platform = values.get('platform') if values.get('platform') in dict(funnel.PLATFORMS) else ''
    rows = funnel.sheet(day, on, platform or None)
    error = None
    if request.method == 'POST':
        saved, error = funnel.save_sheet(rows, day, request.form)
        if error:
            db.session.rollback()
        else:
            flash(f'Saved the numbers of {saved} post{"s" if saved != 1 else ""}.', 'success')
            return redirect(url_for('funnel.numbers', day=day, on=on.isoformat(), platform=platform or None))
    return render_template('admin/funnel_numbers.html', rows=rows, day=day, on=on, platform=platform,
                           days=funnel.SHEET_DAYS, platforms=funnel.PLATFORMS, stat_fields=funnel.STAT_FIELDS,
                           ref=funnel.post_ref, error=error, form=request.form if error else {},
                           day_span=datetime.timedelta(days=day)), 400 if error else 200


@funnel_bp.route('/admin/funnel/posts/<int:post_id>/posted', methods=['POST'])
@login_required
@admin_required
def mark_posted(post_id):
    """A draft from scripts/social_batch.py is up: it went up today."""
    post = db.session.get(SocialPost, post_id) or abort(404)
    post.status, post.posted_on = 'posted', datetime.date.today()
    db.session.commit()
    flash(f'{funnel.post_ref(post)} is up.', 'success')
    return redirect(url_for('funnel.dashboard') + '#posts')


@funnel_bp.route('/admin/funnel/posts/<int:post_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_post(post_id):
    post = db.session.get(SocialPost, post_id) or abort(404)
    db.session.delete(post)
    db.session.commit()
    flash(f'Removed {funnel.post_ref(post)} from the log.', 'success')
    return redirect(url_for('funnel.dashboard') + '#posts')
