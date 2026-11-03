"""The video inbox (services/recipe_v2/inbox.py): cooking videos saved from the phone. Admin only.

The iPhone shortcut opens /admin/inbox/add?url=… in Safari (docs/VIDEO_INBOX.md). The GET writes nothing: it gives a
page that sends itself as a POST, with a token kept in the session, so that a form on another site cannot save anything.
"""
import hmac
import secrets

from flask import Blueprint, abort, flash, redirect, render_template, request, session, url_for
from flask_login import login_required

from database.models import VideoInbox, db
from services.recipe_v2 import inbox as inbox_service
from services.recipe_v2.sources import is_video
from utils.decorators import admin_required

video_inbox_bp = Blueprint('video_inbox', __name__)


def _token():
    if 'inbox_token' not in session:
        session['inbox_token'] = secrets.token_urlsafe(32)
    return session['inbox_token']


@video_inbox_bp.route('/admin/inbox')
@login_required
@admin_required
def inbox():
    status = 'discarded' if request.args.get('show') == 'discarded' else 'new'
    return render_template('video_inbox.html', rows=inbox_service.rows(status), status=status,
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
    flash('Saved.' if how == 'saved' else 'Already in the inbox.', 'success')
    return redirect(url_for('video_inbox.inbox'))


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
