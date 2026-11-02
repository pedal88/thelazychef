"""The funnel from TikTok and Instagram to the app (services/funnel.py): the short addresses people type from a post,
the ref code any page can carry (?ref=ig-3), the admin Funnel page, and its post log."""
import datetime

from flask import Blueprint, abort, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from database.models import SocialPost, db
from services import funnel, social_publish, social_stats
from services.recipe_v2 import tasks
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
# for one post (the code tiktok-3). They keep the code and open what the post showed: its recipe, the post's page when
# it showed several, else the home page (funnel.post_recipes). The visit is counted on the page they open, as anywhere.
def _short_link(channel, code):
    if not current_user.is_authenticated:
        funnel.remember(f'{channel}-{code}' if code else channel, request.user_agent.string)
    post = code and funnel.post_for(channel, code)
    ids = funnel.post_recipes(post) if post else []
    if len(ids) > 1:
        return redirect(url_for('funnel.post_page', platform=channel, code=post.code))
    return redirect(url_for('recipe_detail', recipe_id=ids[0]) if ids else url_for('content.home'))


@funnel_bp.route('/post/<platform>/<code>')
def post_page(platform, code):
    """A post that showed several dinners (a week, Got chicken?): the dishes, each to its recipe, and one shopping
    list for all of them, as the post had it. Public; a post of one recipe or none has no page."""
    post = funnel.post_for(platform, code) if platform in dict(funnel.PLATFORMS) else None
    ids = funnel.post_recipes(post) if post else []
    if len(ids) < 2:
        abort(404)
    return render_template('post.html', **funnel.post_view(post, ids, current_user if current_user.is_authenticated else None))


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
                           choices=funnel.VARIANT_CHOICES, statuses=funnel.POST_STATUSES,
                           ref=funnel.post_ref(post) if post.id else None), 400 if error else 200


@funnel_bp.route('/admin/funnel/posts/new', methods=['GET', 'POST'])
@login_required
@admin_required
def new_post():
    """A post for the log. scripts/social_render.py prints this address with the platform, code, format, recipe and
    the variant (series, n, hook, cta, recipes, views, look, slides) filled in; an empty code is the next free one."""
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
            'posted_on': datetime.date.today().isoformat(), 'hook': args.get('hook', ''),
            'series': args.get('series', ''), 'series_n': args.get('n', ''), 'hook_group': args.get('hook_group', ''),
            'cta_group': args.get('cta', ''), 'recipe_ids': args.get('recipes', ''), 'views': args.get('views', ''),
            'look': args.get('look', ''), 'slides': args.get('slides', ''), 'round': args.get('round', '')}
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


@funnel_bp.route('/admin/funnel/fetch', methods=['POST'])
@login_required
@admin_required
def fetch_now():
    """Fetch from Instagram on the Funnel page: what the daily job does, now."""
    if not social_stats.configured():
        flash('Instagram is not set up: INSTAGRAM_ACCESS_TOKEN and INSTAGRAM_USER_ID are missing.', 'error')
    else:
        try:
            flash(social_stats.report(social_stats.fetch_instagram()), 'success')
        except social_stats.StatsError as e:
            db.session.rollback()
            flash(f'Instagram could not be read: {e}', 'error')
    return redirect(url_for('funnel.dashboard') + '#posts')


@funnel_bp.route('/internal/tasks/social-stats', methods=['POST'])
def social_stats_task():
    """The daily job (Cloud Scheduler, social-stats): the platforms' numbers into the post log. It carries the
    queue's service account's OIDC token, like the Cloud Tasks jobs (tasks.verified)."""
    if not tasks.verified(request.headers.get('Authorization')):
        return jsonify({'error': 'unauthorized'}), 401
    if not social_stats.configured():
        return jsonify({'skipped': 'Instagram is not set up'}), 200
    try:
        summary = social_stats.fetch_instagram()
    except social_stats.StatsError as e:
        db.session.rollback()
        print(f'social-stats: {e}')
        return jsonify({'error': str(e)}), 502  # Cloud Scheduler tries again
    print(f'social-stats: {social_stats.report(summary)}')
    return jsonify(summary), 200


@funnel_bp.route('/admin/funnel/queue')
@login_required
@admin_required
def queue():
    """The Instagram queue: the posts scripts/social_batch.py has rendered, by day, to approve with a time."""
    return render_template('admin/funnel_queue.html', days=social_publish.queue(),
                           ready=social_stats.configured() and tasks.configured())


@funnel_bp.route('/admin/funnel/queue/approve', methods=['POST'])
@login_required
@admin_required
def approve_queue():
    """Schedules the posts ticked in the form with their times and text; the others stay as they are."""
    errors, done = [], 0
    for day in social_publish.queue():
        for row in day['posts']:
            post = row['post']
            if request.form.get(f'approve-{post.id}'):
                error = social_publish.schedule(post, social_publish.parse_when(request.form.get(f'when-{post.id}')),
                                                request.form.get(f'caption-{post.id}'))
                if error:
                    errors.append(error)
                else:
                    done += 1
    if done:
        flash(f'{done} post{"s" if done != 1 else ""} scheduled.', 'success')
    for error in errors:
        flash(error, 'error')
    return redirect(url_for('funnel.queue'))


@funnel_bp.route('/admin/funnel/queue/<int:post_id>/cancel', methods=['POST'])
@login_required
@admin_required
def cancel_queue(post_id):
    post = db.session.get(SocialPost, post_id) or abort(404)
    social_publish.cancel(post)
    flash(f'{funnel.post_ref(post)} is back to draft.', 'success')
    return redirect(url_for('funnel.queue'))


@funnel_bp.route('/internal/tasks/social-publish/<int:post_id>', methods=['POST'])
def social_publish_task(post_id):
    """A scheduled post's Cloud Task, at its time. Always 200 when it has run: a failure is shown in the queue, not
    tried again (services/social_publish.py)."""
    if not tasks.verified(request.headers.get('Authorization')):
        return jsonify({'error': 'unauthorized'}), 401
    post = db.session.get(SocialPost, post_id)
    if post is None:
        return jsonify({'result': 'no such post'}), 200
    if not social_stats.configured():
        return jsonify({'result': 'Instagram is not set up'}), 200
    result = social_publish.publish(post)
    print(f'social-publish: {funnel.post_ref(post)}: {result}')
    return jsonify({'result': result}), 200


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
