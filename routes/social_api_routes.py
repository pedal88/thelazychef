"""The social API: what scripts/social_batch.py uses to log a day's TikTok and Instagram posts as drafts in the Funnel
page's post log, so each post has its code before its slides are rendered, and the next post of a series sees this
one as used, and what scripts/social_numbers.py uses to keep TikTok's numbers (docs/SOCIAL.md). It takes the content API's key (CONTENT_API_KEY, as a bearer token) and answers 401
without it.

Nothing here posts anything: a draft becomes a post when Pål has put it up and marks it posted on the Funnel page."""
import datetime

from flask import Blueprint, jsonify, request

from database.models import SocialPost, db
from routes._shared import get_storage
from routes.content_api_routes import key_required
from services import funnel, social_publish

social_api_bp = Blueprint('social_api', __name__, url_prefix='/api/social')


def _day(value):
    try:
        return datetime.date.fromisoformat(value or '')
    except ValueError:
        return None


@social_api_bp.route('/drafts', methods=['POST'])
@key_required
def drafts():
    """{"day": "2026-11-03", "posts": [{"format": "series", "series": "airfryer", "series_n": 7, "ids": [325], …},
    {"format": "map", "recipe_id": 345, "hook": "…"}]} -> the posts as drafts on both platforms, with their codes
    (funnel.plan_drafts). Sending the same post again keeps the code it was given."""
    body = request.get_json(silent=True) or {}
    day = _day(body.get('day'))
    posts = body.get('posts')
    if day is None or not isinstance(posts, list) or not posts or not all(isinstance(p, dict) for p in posts):
        return jsonify({'error': 'send {"day": "YYYY-MM-DD", "posts": [{"format": …}, …]}'}), 400
    planned, errors = funnel.plan_drafts(day, posts)
    if errors:
        return jsonify({'errors': errors}), 400
    return jsonify({'day': day.isoformat(), 'posts': planned})


@social_api_bp.route('/tiktok-numbers', methods=['POST'])
@key_required
def tiktok_numbers():
    """{"on": "2026-11-08", "dry_run": true, "posts": [{"code": "6", "views": 276, "likes": 11, "comments": 0}, …]} -> what
    the numbers read off TikTok Studio that day come to, saved unless dry_run (funnel.save_tiktok_reading)."""
    body = request.get_json(silent=True) or {}
    on = _day(body.get('on'))
    posts = body.get('posts')
    if on is None or not isinstance(posts, list) or not posts or not all(isinstance(p, dict) for p in posts):
        return jsonify({'error': 'send {"on": "YYYY-MM-DD", "posts": [{"code": …, "views": …}, …]}'}), 400
    done, errors = funnel.save_tiktok_reading(on, posts, dry_run=bool(body.get('dry_run')))
    if errors:
        return jsonify({'errors': errors}), 400
    return jsonify({'on': on.isoformat(), 'saved': not body.get('dry_run'), 'posts': done})


@social_api_bp.route('/slides/<code>', methods=['POST'])
@key_required
def slides(code):
    """A post's slides (JPEGs, the form's files named slides, in order) and its caption, for the form's platform
    (Instagram unless it says tiktok). An Instagram post then waits in the queue on the Funnel page, where nothing goes
    up until it is approved; a TikTok post waits on the TikTok page, to be posted by hand."""
    platform = request.form.get('platform') or 'instagram'
    post = db.session.execute(db.select(SocialPost).filter_by(platform=platform, code=code)).scalar()
    if post is None:
        return jsonify({'error': f'no {platform} post with code {code}'}), 404
    if post.status != 'draft':
        return jsonify({'error': f'{platform}-{code} is {post.status}, not a draft'}), 400
    error = social_publish.save_slides(post, [f.read() for f in request.files.getlist('slides')],
                                       (request.form.get('caption') or '').strip(), get_storage())
    if error:
        return jsonify({'error': error}), 400
    return jsonify({'code': code, 'slides': len(social_publish.slides_of(post))})
