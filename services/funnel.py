"""Where users come from, for the TikTok and Instagram funnel (routes/funnel_routes.py).

A visit can bring a ref code: the short addresses (thelazychef.app/tiktok, /ig, and /tiktok/3, which gives tiktok-3 so
one post can be told from another) or ?ref= on any page. The first code of a browser session is kept in the session;
when the visitor signs up, it is saved on the user with their answer to "How did you find us?". The admin Funnel page
counts sign-ups and the users who saved or made a recipe, per channel and week.

A visit is counted (ReferralVisit, per code and day) only when a page has been open in a browser for a few seconds: the
page asks for it (seen(), from base.html). The moment a post goes up, Meta fetches every address in it from some twenty
machines, some as a link preview robot and some as a browser that never stays, and before 31.10.2026 each of those
counted as a visit (7 and 8 for the first two Instagram posts).

The post log (SocialPost) puts each post's own numbers, copied from TikTok or Instagram, beside the visits and sign-ups
its code brought, so a post can be judged by how many came, not only by how many saw it (docs/SOCIAL.md).
"""
import datetime
import re

from flask import session
from sqlalchemy import case, func

from database.models import (Recipe, RecipeComponent, ReferralVisit, SocialPost, SocialPostStat, User,
                             UserRecipeInteraction, db)
from services import social_week

# The answers to "How did you find us?" on the sign-up form: (stored value, label)
SOURCES = [
    ('tiktok', 'TikTok'),
    ('instagram', 'Instagram'),
    ('search', 'Google or another search'),
    ('friend', 'A friend'),
    ('other', 'Somewhere else'),
]

# A ref code's first word and the channel it belongs to (ig-3 and instagram-reel-2 are both Instagram)
_CHANNEL_OF_REF = {'tiktok': 'tiktok', 'tt': 'tiktok', 'ig': 'instagram', 'instagram': 'instagram'}

CHANNELS = [value for value, _ in SOURCES] + ['unknown']
CHANNEL_LABELS = dict(SOURCES, unknown='Not known')

SESSION_KEY = 'ref'
SEEN_KEY = 'ref_seen'  # the session's visit has been counted

# Programs that fetch a page without a person behind them: link previews, search engines, scripts. Case matters, so a
# phone named CUBOT is not taken for one.
_ROBOTS = re.compile(r'bot\b|bot/|crawl|spider|slurp|facebookexternalhit|facebookcatalog|meta-external|WhatsApp|'
                     r'Headless|python-|curl/|Wget|Go-http-client')

# The post log: where a post went up (funnel channels), what kind it is (scripts/social_render.py's formats), and the
# platform numbers copied in for it
PLATFORMS = [('tiktok', 'TikTok'), ('instagram', 'Instagram')]
POST_FORMATS = ['map', 'grid', 'pantry', 'week', 'other']
STAT_FIELDS = ['views', 'likes', 'comments', 'saves', 'shares', 'profile_visits']
POST_STATUSES = [('draft', 'Draft'), ('posted', 'Posted')]

# A day's posts planned by scripts/social_batch.py: the formats it renders, the ones it suggests in turn when it is
# given no plan, the parts a map's recipe has so its lines meet (docs/SOCIAL.md), and how long a recipe rests after a
# post
RENDERED_FORMATS = ['map', 'grid', 'pantry', 'week']
DAY_FORMATS = ['map', 'grid']
MAP_PARTS = (3, 4)
RECIPE_REST_DAYS = 60
FORMAT_TITLES = {'pantry': 'The foundation pantry', 'week': 'One shop, five dinners'}


def clean_ref(value):
    """A ref code as stored: lower case, letters, digits, - and _, at most 60 characters; None when nothing is left."""
    ref = re.sub(r'[^a-z0-9_-]+', '', (value or '').strip().lower())[:60]
    return ref or None


def is_robot(user_agent):
    return not user_agent or bool(_ROBOTS.search(user_agent))


def remember(ref, user_agent):
    """Keeps the first ref code of this browser session. Later codes are ignored, so a visitor who came from TikTok and
    then opens a shared ?ref=ig link stays a TikTok visitor. Robots get none. The visit is counted by seen()."""
    ref = clean_ref(ref)
    if not ref or session.get(SESSION_KEY) or is_robot(user_agent):
        return
    session[SESSION_KEY] = ref


def unseen():
    """Whether this session brought a code whose visit has not been counted yet: then the page asks seen() to."""
    return bool(session.get(SESSION_KEY)) and not session.get(SEEN_KEY)


def seen(user_agent):
    """Counts the session's visit for its code, once. Returns whether it counted."""
    ref = session.get(SESSION_KEY)
    if not ref or session.get(SEEN_KEY) or is_robot(user_agent):
        return False
    session[SEEN_KEY] = True
    count_visit(ref, datetime.date.today())
    return True


def count_visit(ref, day):
    """Adds one to the code's count for the day in a single statement, so visits that come at the same moment neither
    get lost nor collide on the row they both create."""
    table = ReferralVisit.__table__
    dialect = db.engine.dialect.name
    if dialect == 'postgresql':
        from sqlalchemy.dialects.postgresql import insert
    elif dialect == 'sqlite':
        from sqlalchemy.dialects.sqlite import insert
    else:
        raise NotImplementedError(dialect)
    statement = insert(table).values(ref=ref, day=day, count=1)
    db.session.execute(statement.on_conflict_do_update(
        index_elements=[table.c.ref, table.c.day], set_={'count': table.c.count + 1}))
    db.session.commit()


def session_ref():
    return session.get(SESSION_KEY)


def channel(user):
    """The channel a user came through: their ref code first (it is measured), then their answer, else 'unknown'."""
    if user.signup_ref:
        first = user.signup_ref.split('-', 1)[0].split('_', 1)[0]
        if first in _CHANNEL_OF_REF:
            return _CHANNEL_OF_REF[first]
    if user.signup_source in CHANNEL_LABELS:
        return user.signup_source
    return 'unknown'


def _monday(day):
    return day - datetime.timedelta(days=day.weekday())


def report(weeks=12, today=None):
    """The numbers on the Funnel page. Admins are left out. Users from before the tracking (no created_at) count in the
    totals but not in any week.

    {'weeks': [{'start', 'signups': {channel: n}, 'total'}], newest first,
     'channels': [{'key', 'label', 'signups', 'saved', 'made'}],
     'totals': {'signups', 'saved', 'made', 'untracked'},
     'refs': [{'ref', 'visits', 'visits_28', 'signups', 'made'}], most visits first,
     'posts': post_log(), 'next_code': next_code()}"""
    today = today or datetime.date.today()
    users = db.session.execute(db.select(User).where(User.is_admin.is_not(True))).scalars().all()
    saved_ids = set(db.session.execute(
        db.select(UserRecipeInteraction.user_id).where(UserRecipeInteraction.status == 'favorite')).scalars())
    made_ids = set(db.session.execute(
        db.select(UserRecipeInteraction.user_id).where(
            (UserRecipeInteraction.is_made.is_(True)) | (UserRecipeInteraction.made_count > 0))).scalars())

    this_week = _monday(today)
    starts = [this_week - datetime.timedelta(weeks=i) for i in range(weeks)]
    by_week = {start: {key: 0 for key in CHANNELS} for start in starts}
    by_channel = {key: {'signups': 0, 'saved': 0, 'made': 0} for key in CHANNELS}
    by_ref = {}
    for user in users:
        key = channel(user)
        by_channel[key]['signups'] += 1
        by_channel[key]['saved'] += user.id in saved_ids
        by_channel[key]['made'] += user.id in made_ids
        if user.created_at:
            start = _monday(user.created_at.date())
            if start in by_week:
                by_week[start][key] += 1
        if user.signup_ref:
            row = by_ref.setdefault(user.signup_ref, {'signups': 0, 'made': 0})
            row['signups'] += 1
            row['made'] += user.id in made_ids

    since = today - datetime.timedelta(days=27)
    visits = db.session.execute(
        db.select(ReferralVisit.ref, func.sum(ReferralVisit.count),
                  func.sum(case((ReferralVisit.day >= since, ReferralVisit.count), else_=0)))
        .group_by(ReferralVisit.ref)).all()
    refs = {ref: {'ref': ref, 'visits': int(total or 0), 'visits_28': int(recent or 0), 'signups': 0, 'made': 0}
            for ref, total, recent in visits}
    for ref, row in by_ref.items():
        refs.setdefault(ref, {'ref': ref, 'visits': 0, 'visits_28': 0, 'signups': 0, 'made': 0}).update(row)

    return {
        'weeks': [{'start': start, 'signups': by_week[start], 'total': sum(by_week[start].values())}
                  for start in starts],
        'channels': [{'key': key, 'label': CHANNEL_LABELS[key], **by_channel[key]} for key in CHANNELS],
        'totals': {'signups': len(users), 'saved': len(saved_ids & {u.id for u in users}),
                   'made': len(made_ids & {u.id for u in users}),
                   'untracked': sum(1 for u in users if not u.created_at)},
        'refs': sorted(refs.values(), key=lambda r: (-r['visits'], -r['signups'], r['ref'])),
        'posts': post_log(refs),
        'next_code': next_code(),
    }


def post_ref(post):
    """The ref code a post's short address gives: thelazychef.app/tiktok/5 is tiktok-5, /ig/5 is instagram-5."""
    return f'{post.platform}-{post.code}'


def post_log(refs):
    """The posts, newest first, each with its latest platform numbers and what its code brought (refs as in
    report()). per_1000 is visits per 1000 views: how well a post sends people on, which views alone do not say."""
    posts = db.session.execute(
        db.select(SocialPost).order_by(SocialPost.posted_on.desc(), SocialPost.id.desc())).scalars().all()
    rows = []
    for post in posts:
        brought = refs.get(post_ref(post), {})
        stats = sorted(post.stats, key=lambda s: s.day)
        latest = next((s for s in reversed(stats) if s.views is not None), stats[-1] if stats else None)
        visits = brought.get('visits', 0)
        views = latest.views if latest else None
        rows.append({'post': post, 'ref': post_ref(post), 'latest': latest, 'visits': visits,
                     'signups': brought.get('signups', 0), 'made': brought.get('made', 0),
                     'per_1000': round(visits * 1000 / views, 1) if views else None})
    return rows


def next_code():
    """The code for the next post: one above every number in use, in the post log or in a ref code a visit or a
    sign-up brought (tiktok-5, ig-5), so a post rendered with it is told apart from all before it."""
    used = list(db.session.execute(db.select(SocialPost.code)).scalars())
    used += [ref.split('-', 1)[1] for ref in db.session.execute(db.select(ReferralVisit.ref).distinct()).scalars()
             if '-' in ref]
    used += [ref.split('-', 1)[1] for ref in db.session.execute(
        db.select(User.signup_ref).where(User.signup_ref.is_not(None)).distinct()).scalars() if '-' in ref]
    return str(max((int(code) for code in used if code.isdigit()), default=0) + 1)


def suggest(day, n=5):
    """n posts for a day, when none are planned by hand: weeknight dinners with a dish image (the week post's
    candidates) that no post has drawn on in the RECIPE_REST_DAYS before it, in DAY_FORMATS by turn, a map only from a
    recipe with MAP_PARTS parts. [{'format', 'recipe_id', 'title'}], fewer when the recipes run out."""
    rested = set(db.session.execute(db.select(SocialPost.recipe_id).where(
        SocialPost.recipe_id.is_not(None),
        SocialPost.posted_on > day - datetime.timedelta(days=RECIPE_REST_DAYS))).scalars())
    free = [i for i in sorted(social_week.candidates()) if i not in rested]
    parts = dict(db.session.execute(
        db.select(RecipeComponent.recipe_id, func.count(RecipeComponent.id))
        .where(RecipeComponent.recipe_id.in_(free)).group_by(RecipeComponent.recipe_id)).all())
    titles = dict(db.session.execute(db.select(Recipe.id, Recipe.title).where(Recipe.id.in_(free))).all())
    picked = []
    for k in range(n):
        fmt = DAY_FORMATS[k % len(DAY_FORMATS)]
        fits = [i for i in free if fmt != 'map' or parts.get(i, 0) in MAP_PARTS]
        if not fits:
            fmt, fits = 'grid', free
        if not fits:
            break
        chosen = fits[0]
        free.remove(chosen)
        picked.append({'format': fmt, 'recipe_id': chosen, 'title': titles[chosen]})
    return picked


def _plan_item(item):
    """(format, recipe, week ids, hook) of a planned post, or a string saying what is wrong with it."""
    fmt = item.get('format')
    if fmt not in RENDERED_FORMATS:
        return f'format must be one of {", ".join(RENDERED_FORMATS)}, not {fmt!r}'
    recipe = None
    if fmt in ('map', 'grid'):
        recipe_id = item.get('recipe_id')
        recipe = db.session.get(Recipe, recipe_id) if isinstance(recipe_id, int) else None
        if recipe is None or recipe.status != 'approved' or recipe.schema_version != 2:
            return f'{fmt} needs an approved recipe, and {recipe_id!r} is not one'
    ids = item.get('ids') or None
    if ids is not None and (fmt != 'week' or not isinstance(ids, list) or len(ids) != 5
                            or not all(isinstance(i, int) for i in ids)):
        return 'ids are the five recipe ids of a week post'
    hook = (item.get('hook') or '').strip()[:200] or None
    return fmt, recipe, ids, hook


def plan_drafts(day, items):
    """Logs a day's planned posts as drafts, each on both platforms under one code (thelazychef.app/tiktok/5 and
    /ig/5), and returns ([{'code', 'format', 'recipe_id', 'ids', 'title', 'hook', 'new'}], errors). Nothing is saved
    when an item is wrong. A post the day already has (same format, recipe and week) keeps its code, so the script can
    run again; a hook given again replaces the old one."""
    checked = [_plan_item(item) for item in items]
    errors = [f'post {n}: {c}' for n, c in enumerate(checked, 1) if isinstance(c, str)]
    if errors:
        return [], errors
    planned = []
    for fmt, recipe, ids, hook in checked:
        notes = f'Recipes {",".join(str(i) for i in ids)}' if ids else None
        title = recipe.title[:200] if recipe else FORMAT_TITLES[fmt]
        found = db.session.execute(db.select(SocialPost).filter_by(
            posted_on=day, format=fmt, recipe_id=recipe.id if recipe else None, notes=notes, status='draft')
            .order_by(SocialPost.id)).scalars().first()
        code = found.code if found else next_code()
        for platform, _ in PLATFORMS:
            post = db.session.execute(db.select(SocialPost).filter_by(platform=platform, code=code)).scalar()
            if post is None:
                post = SocialPost(platform=platform, code=code, format=fmt, recipe_id=recipe.id if recipe else None,
                                  title=title, notes=notes, posted_on=day, status='draft')
                db.session.add(post)
            if hook:
                post.hook = hook
        db.session.flush()  # so the next post's code is one above this one
        planned.append({'code': code, 'format': fmt, 'recipe_id': recipe.id if recipe else None, 'ids': ids,
                        'title': title, 'hook': hook or (found.hook if found else None), 'new': found is None})
    db.session.commit()
    return planned, []


def _text(form, key, length):
    return (form.get(key) or '').strip()[:length] or None


def save_post(post, form):
    """Fills a post from the form on the post page; returns what is wrong, or None when it is saved."""
    platform = form.get('platform')
    fmt = form.get('format')
    code = clean_ref(form.get('code'))
    status = form.get('status') or 'posted'
    if platform not in dict(PLATFORMS):
        return 'Pick TikTok or Instagram.'
    if status not in dict(POST_STATUSES):
        return 'Pick draft or posted.'
    if fmt not in POST_FORMATS:
        return 'Pick a format.'
    if not code or '-' in code:
        return 'Give the code from the address on the last slide, e.g. 5 for thelazychef.app/tiktok/5.'
    taken = db.session.execute(db.select(SocialPost).filter_by(platform=platform, code=code)).scalar()
    if taken and taken is not post:
        return f'{dict(PLATFORMS)[platform]} already has a post with code {code}.'
    recipe = None
    if (form.get('recipe_id') or '').strip():
        if not form['recipe_id'].strip().isdigit():
            return 'The recipe is its number, e.g. 297.'
        recipe = db.session.get(Recipe, int(form['recipe_id']))
        if recipe is None:
            return f'There is no recipe {form["recipe_id"].strip()}.'
    title = _text(form, 'title', 200) or (recipe.title[:200] if recipe else None)
    if not title:
        return 'Give the post a title, or the recipe it is drawn from.'
    try:
        posted_on = datetime.date.fromisoformat(form.get('posted_on') or '')
    except ValueError:
        return 'Give the day it went up.'
    post.platform, post.code, post.format, post.title, post.posted_on = platform, code, fmt, title, posted_on
    post.status = status
    post.recipe_id = recipe.id if recipe else None
    post.hook, post.sound, post.url = _text(form, 'hook', 200), _text(form, 'sound', 120), _text(form, 'url', 300)
    post.notes = _text(form, 'notes', 5000)
    if post.id is None:
        db.session.add(post)
    db.session.commit()
    return None


def save_stat(post, form):
    """Keeps the platform's numbers for a post on a day after it went up, replacing what that day had; returns what is
    wrong, or None."""
    day = (form.get('day') or '').strip()
    if not day.isdigit() or not 0 <= int(day) <= 365:
        return 'Give the number of days since it went up, e.g. 2 or 7.'
    numbers = {}
    for key in STAT_FIELDS:
        value = (form.get(key) or '').replace(' ', '').replace(',', '').strip()
        if value and not value.isdigit():
            return f'{key.replace("_", " ").capitalize()} must be a whole number.'
        numbers[key] = int(value) if value else None
    if all(v is None for v in numbers.values()):
        return 'Give at least one number.'
    stat = next((s for s in post.stats if s.day == int(day)), None)
    if stat is None:
        stat = SocialPostStat(day=int(day))
        post.stats.append(stat)
    for key, value in numbers.items():
        setattr(stat, key, value)
    db.session.commit()
    return None
