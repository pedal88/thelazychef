"""Slides for TikTok and Instagram posts (services/social.py, docs/SOCIAL.md): one page per slide, photographed by
scripts/social_render.py. Public like the recipe pages they are drawn from, but kept out of search engines."""
from flask import Blueprint, abort, render_template, request

from database.models import Recipe, db
from routes._shared import LOOK_FONTS, dish_images, viewer_is_admin
from services import social, social_week

social_bp = Blueprint('social', __name__)


def _size():
    size = request.args.get('size', 'ig')
    if size not in social.SIZES:
        abort(404)
    return size


def _slide(slides, fmt, title=None, count=None, titles=()):
    """The page for ?slide=n (from 1), at ?size=ig or tt, with the post's ?code for the address on the last slide, in
    today's look or one of the style trial's (?look=c|d|e|f). ?caption=1 gives a first draft of the post's text."""
    size = _size()
    code = request.args.get('code')
    if request.args.get('caption'):
        text = social.caption(fmt, size, code, title=title, count=count, titles=titles)
        return text, 200, {'Content-Type': 'text/plain; charset=utf-8', 'X-Robots-Tag': 'noindex'}
    n = request.args.get('slide', 1, type=int)
    if not 1 <= n <= len(slides):
        abort(404)
    width, height = social.SIZES[size]
    look = request.args.get('look')
    response = render_template('social/slide.html', slide=slides[n - 1], n=n, slides=len(slides), fmt=fmt,
                               size=size, width=width, height=height, address=social.address(size, code),
                               look=look if look in LOOK_FONTS else None)
    return response, 200, {'X-Robots-Tag': 'noindex', 'X-Slides': str(len(slides))}


@social_bp.route('/social/recipe/<int:recipe_id>/<fmt>')
def recipe_post(recipe_id, fmt):
    recipe = db.session.get(Recipe, recipe_id)
    if fmt not in social.FORMATS or not recipe or recipe.schema_version != 2 or (
            recipe.status != 'approved' and not viewer_is_admin()):
        abort(404)
    from services.recipe_v2.view import page
    view = page(recipe)
    slides = social.recipe_slides(view, fmt, dish_images(recipe)['dish'], _size())
    return _slide(slides, fmt, title=view['title'], count=slides[0].get('count'))


@social_bp.route('/social/pantry')
def pantry_post():
    slides = social.pantry_slides(_size())
    return _slide(slides, 'pantry', count=slides[0]['count'])


@social_bp.route('/social/week')
def week_post():
    """One shop, five dinners: the week services/social_week.py picks, or the five in ?ids=1,2,3,4,5 in that order."""
    from services.recipe_v2.view import page
    asked = request.args.get('ids')
    if asked:
        try:
            ids = [int(i) for i in asked.split(',')]
        except ValueError:
            abort(404)
    else:
        ids = social_week.pick(social_week.candidates())
    recipes = [db.session.get(Recipe, i) for i in ids]
    if len(recipes) != len(social_week.WEEK_DAYS) or any(
            not r or r.schema_version != 2 or (r.status != 'approved' and not viewer_is_admin()) for r in recipes):
        abort(404)
    views = [page(r) for r in recipes]
    slides = social_week.week_slides(views, [dish_images(r)['dish'] for r in recipes], _size())
    return _slide(slides, 'week', count=slides[0]['count'], titles=[v['title'] for v in views])
