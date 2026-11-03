"""The video inbox (services/recipe_v2/inbox.py): cooking videos saved from the phone. Admin only, except the task
Cloud Tasks calls.

The iPhone shortcut opens /admin/inbox/add?url=… in Safari (docs/VIDEO_INBOX.md). The GET writes nothing: it gives a
page that sends itself as a POST, with a token kept in the session, so that a form on another site cannot save anything.
"""
import hmac
import logging
import secrets

from flask import Blueprint, abort, flash, jsonify, redirect, render_template, request, session, url_for
from flask_login import login_required

from database.models import VideoInbox, db
from services.recipe_v2 import inbox as inbox_service, tasks
from services.recipe_v2.sources import is_video
from utils.decorators import admin_required

video_inbox_bp = Blueprint('video_inbox', __name__)
log = logging.getLogger(__name__)


def _token():
    if 'inbox_token' not in session:
        session['inbox_token'] = secrets.token_urlsafe(32)
    return session['inbox_token']


@video_inbox_bp.route('/admin/inbox')
@login_required
@admin_required
def inbox():
    status = 'discarded' if request.args.get('show') == 'discarded' else 'new'
    return render_template('video_inbox.html', rows=inbox_service.rows(status), status=status, titles=inbox_service.recipe_titles(),
                           other=db.session.scalar(db.select(db.func.count()).select_from(VideoInbox).where(VideoInbox.status != status)))


@video_inbox_bp.route('/admin/inbox/add', methods=['GET'])
@login_required
@admin_required
def add_page():
    shared = request.args.get('url') or ''
    link = inbox_service.first_link(shared)
    usable = bool(link and is_video(link))
    return render_template('video_inbox_add.html', shared=shared, link=link, usable=usable, token=_token()), 200 if usable or not shared else 400


@video_inbox_bp.route('/admin/inbox/add', methods=['POST'])
@login_required
@admin_required
def add():
    if not hmac.compare_digest(request.form.get('token') or '', session.get('inbox_token') or secrets.token_urlsafe(32)):
        abort(400)
    row, how = inbox_service.add(request.form.get('url'))
    if row is None:
        flash('That is not a link to a TikTok, Instagram or YouTube video.', 'error')
        return redirect(url_for('video_inbox.inbox'))
    db.session.commit()
    if not row.dish_name:
        try:
            tasks.enqueue_inbox(row.id)
        except Exception:  # the video is saved; it can be looked up from the list
            log.exception('Video inbox %s: could not queue the look-up', row.id)
    flash('Saved.' if how == 'saved' else 'Already in the inbox.', 'success')
    return redirect(url_for('video_inbox.inbox'))


@video_inbox_bp.route('/admin/inbox/<int:row_id>/look-up', methods=['POST'])
@login_required
@admin_required
def look_up(row_id):
    """Look up a video again, from the list: in the queue, or straight away without one."""
    db.session.get(VideoInbox, row_id) or abort(404)
    if not tasks.enqueue_inbox(row_id):
        tasks.run_inbox(row_id, attempt=tasks.MAX_ATTEMPTS - 1)
    return redirect(url_for('video_inbox.inbox'))


@video_inbox_bp.route(tasks.INBOX_PATH.replace('{id}', '<int:row_id>'), methods=['POST'])
def run_task(row_id):
    """Called by Cloud Tasks, not by users: what a saved video is (tasks.run_inbox)."""
    if not tasks.verified(request.headers.get('Authorization')):
        return jsonify({'error': 'unauthorized'}), 401
    tasks.run_inbox(row_id, attempt=request.headers.get('X-CloudTasks-TaskRetryCount', type=int) or 0)
    return jsonify({'done': True})


@video_inbox_bp.route('/admin/inbox/<int:row_id>/status', methods=['POST'])
@login_required
@admin_required
def set_status(row_id):
    """Discard a row, or take it back."""
    row = db.session.get(VideoInbox, row_id) or abort(404)
    status = request.form.get('status')
    if status not in ('new', 'discarded'):
        abort(400)
    row.status = status
    db.session.commit()
    return redirect(url_for('video_inbox.inbox', show='discarded' if status == 'new' else None))
