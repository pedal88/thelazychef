"""The social API: what scripts/social_batch.py uses to plan a day's TikTok and Instagram posts and log them as drafts
in the Funnel page's post log, so each post has its code before its slides are rendered (docs/SOCIAL.md). It takes
the content API's key (CONTENT_API_KEY, as a bearer token) and answers 401 without it.

Nothing here posts anything: a draft becomes a post when Pål has put it up and marks it posted on the Funnel page."""
import datetime

from flask import Blueprint, jsonify, request

from routes.content_api_routes import key_required
from services import funnel

social_api_bp = Blueprint('social_api', __name__, url_prefix='/api/social')


def _day(value):
    try:
        return datetime.date.fromisoformat(value or '')
    except ValueError:
        return None


@social_api_bp.route('/suggest')
@key_required
def suggest():
    """?day=2026-11-03&n=5: posts for the day from recipes no post has drawn on lately (funnel.suggest)."""
    day = _day(request.args.get('day'))
    if day is None:
        return jsonify({'error': 'day must be a date, e.g. 2026-11-03'}), 400
    n = min(max(request.args.get('n', 5, type=int), 1), 20)
    return jsonify({'day': day.isoformat(), 'posts': funnel.suggest(day, n)})


@social_api_bp.route('/drafts', methods=['POST'])
@key_required
def drafts():
    """{"day": "2026-11-03", "posts": [{"format": "map", "recipe_id": 345, "hook": "…"}, …]} -> the posts as drafts on
    both platforms, with their codes. Sending the same day again keeps the codes it was given."""
    body = request.get_json(silent=True) or {}
    day = _day(body.get('day'))
    posts = body.get('posts')
    if day is None or not isinstance(posts, list) or not posts or not all(isinstance(p, dict) for p in posts):
        return jsonify({'error': 'send {"day": "YYYY-MM-DD", "posts": [{"format": …}, …]}'}), 400
    planned, errors = funnel.plan_drafts(day, posts)
    if errors:
        return jsonify({'errors': errors}), 400
    return jsonify({'day': day.isoformat(), 'posts': planned})
