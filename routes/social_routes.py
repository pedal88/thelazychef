"""Slides for TikTok and Instagram posts (services/social.py, services/social_series.py, docs/SOCIAL.md): one page per
slide, photographed by scripts/social_render.py. Public like the recipe pages they are drawn from, but kept out of
search engines."""
from flask import Blueprint, abort, render_template, request

from database.models import Recipe, db
from routes._shared import dish_images, equipment_image, look_of, viewer_is_admin
from services import social, social_series, social_week

social_bp = Blueprint('social', __name__)


def _size():
    size = request.args.get('size', 'ig')
    if size not in social.SIZES:
        abort(404)
    return size


def _slide(slides, fmt, caption, headers=None):
    """The page for ?slide=n (from 1), at ?size=ig or tt, with the post's ?code for the address on the last slide, in
    the site's look (routes/_shared.SITE_LOOK), another of the style trial's (?look=c|d|e|f) or today's (?look=today).
    ?caption=1 gives a first draft of the post's text (caption() makes it). headers go on every answer: what the
    series post was made of, for scripts/social_render.py."""
    size = _size()
    code = request.args.get('code')
    extra = {'X-Robots-Tag': 'noindex', 'X-Slides': str(len(slides)), **(headers or {})}
    if request.args.get('caption'):
        return caption(), 200, {'Content-Type': 'text/plain; charset=utf-8', **extra}
    n = request.args.get('slide', 1, type=int)
    if not 1 <= n <= len(slides):
        abort(404)
    width, height = social.SIZES[size]
    response = render_template('social/slide.html', slide=slides[n - 1], n=n, slides=len(slides), fmt=fmt,
                               size=size, width=width, height=height, address=social.address(size, code),
                               look=look_of(request.args.get('look')))
    return response, 200, extra


def _recipe(recipe_id):
    """An approved v2 recipe (a draft for an admin), or 404."""
    recipe = db.session.get(Recipe, recipe_id)
    if not recipe or recipe.schema_version != 2 or (recipe.status != 'approved' and not viewer_is_admin()):
        abort(404)
    return recipe


def _post(recipe):
    """The recipe as the series see it (services/social_series.post_of)."""
    from services.recipe_v2.view import equipment_list, page
    view = page(recipe)
    # The air fryer's image is always at hand, from the catalog when no step names it
    items = view['equipment'] + equipment_list(['airfryer'])
    return social_series.post_of(recipe, view, dish_images(recipe)['dish'], {e['id']: equipment_image(e) for e in items})


def _hook_and_cta(posts, slug=None):
    """?hook=<group> and ?cta=<group> on a post outside the series: the words and the CTA, or None for each when
    not asked or not a group (then the post is as it always was)."""
    size = _size()
    r = posts[0]
    f = social_series.facts(posts)
    sd = social_series.seed(slug or 'post', 0, [p['id'] for p in posts])
    text = social_series.hook(request.args.get('hook'), f, sd)
    call = social_series.cta(request.args.get('cta'), f, size, social.address(size, request.args.get('code')), sd)
    return text, call, r


@social_bp.route('/social/recipe/<int:recipe_id>/<fmt>')
def recipe_post(recipe_id, fmt):
    if fmt not in social.FORMATS:
        abort(404)
    recipe = _recipe(recipe_id)
    post = _post(recipe)
    text, call, _ = _hook_and_cta([post])
    view = post['view']
    slides = social.recipe_slides(view, fmt, post['image'], _size(), hook=text, cta=call)
    return _slide(slides, fmt, lambda: social.caption(fmt, _size(), request.args.get('code'), title=view['title'],
                                                      count=slides[0].get('count')))


@social_bp.route('/social/pantry')
def pantry_post():
    slides = social.pantry_slides(_size())
    return _slide(slides, 'pantry', lambda: social.caption('pantry', _size(), request.args.get('code'),
                                                           count=slides[0]['count']))


def _ids(asked):
    try:
        return [int(i) for i in asked.split(',')]
    except ValueError:
        abort(404)


@social_bp.route('/social/week')
def week_post():
    """One shop, five dinners: the week services/social_week.py picks, or the five in ?ids=1,2,3,4,5 in that order."""
    from services.recipe_v2.view import page
    asked = request.args.get('ids')
    ids = _ids(asked) if asked else social_week.pick(social_week.candidates())
    recipes = [db.session.get(Recipe, i) for i in ids]
    if len(recipes) != len(social_week.WEEK_DAYS) or any(
            not r or r.schema_version != 2 or (r.status != 'approved' and not viewer_is_admin()) for r in recipes):
        abort(404)
    views = [page(r) for r in recipes]
    posts = [social_series.post_of(r, v, dish_images(r)['dish'], {}) for r, v in zip(recipes, views)]
    _, call, _ = _hook_and_cta(posts)
    slides = social_week.week_slides(views, [p['image'] for p in posts], _size(), cta=call)
    return _slide(slides, 'week', lambda: social.caption('week', _size(), request.args.get('code'),
                                                         count=slides[0]['count'], titles=[v['title'] for v in views]))


@social_bp.route('/social/post')
def series_post():
    """A post of a series (services/social_series.SERIES): ?series=<slug>, the recipes in ?ids= (as many as the
    series takes) or the ones the series picks next, ?n= the post's number (else the next in the log), ?hook= and
    ?cta= the groups. The answer says what was made: X-Recipes, X-N, X-Hook, X-Hook-Text, X-Cta, X-Views, X-Look."""
    slug = request.args.get('series')
    if slug not in social_series.SERIES:
        abort(404)
    series = social_series.SERIES[slug]
    asked = request.args.get('ids')
    ids = _ids(asked) if asked else social_series.pick(slug)
    if len(ids) != series['count']:
        abort(404)
    posts = [_post(_recipe(i)) for i in ids]
    n = request.args.get('n', type=int) or social_series.next_n(slug)
    size = _size()
    code = request.args.get('code')
    slides, facts, group, text, call = social_series.slides(slug, posts, size, n, request.args.get('hook'),
                                                            request.args.get('cta'), code)
    headers = {'X-Recipes': ','.join(str(i) for i in ids), 'X-N': str(n), 'X-Hook': group, 'X-Hook-Text': text,
               'X-Cta': call['group'], 'X-Views': social_series.views_used(slides),
               'X-Look': look_of(request.args.get('look')) or 'today'}
    return _slide(slides, 'series', lambda: social_series.caption(slug, posts, facts, text, call, size, code), headers)
