"""The video inbox (services/recipe_v2/inbox.py): cooking videos saved from the phone. Admin only, except the task
Cloud Tasks calls.

The iPhone shortcut copies the link and opens /admin/inbox/add, where Paste and save sends it (docs/VIDEO_INBOX.md). With
?url=… the GET writes nothing: it gives a page that sends itself as a POST, which a form on another site cannot do
(utils/cross_site.py).

Many links go through /admin/inbox/check, which reads them out of pasted text or a file and saves nothing: it says how many
are new and what the look-ups cost, and its form saves them.
"""
import logging
import zipfile

from flask import Blueprint, abort, flash, jsonify, redirect, render_template, request, url_for
from flask_login import login_required

from database.models import VideoInbox, db
from services.recipe_v2 import inbox as inbox_service, tasks
from services.recipe_v2.sources import is_video
from utils.decorators import admin_required

video_inbox_bp = Blueprint('video_inbox', __name__)
log = logging.getLogger(__name__)


@video_inbox_bp.route('/admin/inbox')
@login_required
@admin_required
def inbox():
    status = 'discarded' if request.args.get('show') == 'discarded' else 'new'
    return render_template('video_inbox.html', rows=inbox_service.rows(status), status=status, titles=inbox_service.recipe_titles(),
                           waiting=len(inbox_service.waiting()),
                           other=db.session.scalar(db.select(db.func.count()).select_from(VideoInbox).where(VideoInbox.status != status)))


@video_inbox_bp.route('/admin/inbox/add', methods=['GET'])
@login_required
@admin_required
def add_page():
    shared = request.args.get('url') or ''
    link = inbox_service.first_link(shared)
    usable = bool(link and is_video(link))
    return render_template('video_inbox_add.html', shared=shared, link=link, usable=usable), 200 if usable or not shared else 400


@video_inbox_bp.route('/admin/inbox/add', methods=['POST'])
@login_required
@admin_required
def add():
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


def _allow_long_forms():
    """Before the form is read: Flask stops at 500 kB of text, and a pasted file can be more."""
    request.max_form_memory_size = inbox_service.MAX_TEXT


@video_inbox_bp.route('/admin/inbox/check', methods=['POST'])
@login_required
@admin_required
def check():
    """What the pasted text or the file holds. Saves nothing."""
    _allow_long_forms()
    text = request.form.get('text') or ''
    upload = request.files.get('file')
    if upload and upload.filename:
        try:
            text += '\n' + inbox_service.text_of_upload(upload.read(), upload.filename)
        except zipfile.BadZipFile:
            flash('That zip file could not be read.', 'error')
            return redirect(url_for('video_inbox.add_page'))
    found = inbox_service.sort(text)
    new = found['new']
    return render_template('video_inbox_check.html', **found, links=new[:inbox_service.MAX_LINKS], limit=inbox_service.MAX_LINKS,
                           cost=min(len(new), inbox_service.MAX_LINKS) * inbox_service.COST_A_VIDEO,
                           minutes=round(min(len(new), inbox_service.MAX_LINKS) * tasks.INBOX_SPACING / 60))


@video_inbox_bp.route('/admin/inbox/add-many', methods=['POST'])
@login_required
@admin_required
def add_many():
    _allow_long_forms()
    rows = inbox_service.save_many(request.form.get('links'))
    db.session.commit()
    _look_up_many([row.id for row in rows])
    flash(f'Saved {len(rows)} {"video" if len(rows) == 1 else "videos"}.', 'success')
    return redirect(url_for('video_inbox.inbox'))


def _look_up_many(ids):
    try:
        if ids:
            tasks.enqueue_inbox_many(ids)
    except Exception:  # the videos are saved; the inbox says they wait, and can queue them again
        log.exception('Video inbox: could not queue %s look-ups', len(ids))


@video_inbox_bp.route('/admin/inbox/look-up-waiting', methods=['POST'])
@login_required
@admin_required
def look_up_waiting():
    _look_up_many(inbox_service.waiting())
    return redirect(url_for('video_inbox.inbox'))


@video_inbox_bp.route(tasks.INBOX_MANY_PATH, methods=['POST'])
def run_many_task():
    """Called by Cloud Tasks, not by users: queues the look-ups of many videos (tasks.run_inbox_many)."""
    if not tasks.verified(request.headers.get('Authorization')):
        return jsonify({'error': 'unauthorized'}), 401
    ids = (request.get_json(silent=True) or {}).get('ids') or []
    return jsonify({'queued': tasks.run_inbox_many(ids)})


@video_inbox_bp.route('/admin/inbox/<int:row_id>/look-up', methods=['POST'])
@login_required
@admin_required
def look_up(row_id):
    """Look up a video again, from the list: in the queue, or straight away without one."""
    row = db.session.get(VideoInbox, row_id) or abort(404)
    row.meta_error = None  # asked for again, so what stopped it last time does not count
    db.session.commit()
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
