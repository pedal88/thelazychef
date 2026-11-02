"""The Instagram queue: posts rendered by scripts/social_batch.py wait on the Funnel page as drafts with their slides
and text, Pål approves them with a time, and a Cloud Task publishes each at its time through the Graph API
(docs/SOCIAL.md, "The Instagram queue"). Nothing goes up without that approval.

A carousel is one container per slide (a JPEG on a public address, which Meta fetches), one for the carousel with the
text and the AI label, and media_publish. The API cannot add music to a carousel: a post that needs music is posted by
hand and marked posted. A task that finds its post cancelled or moved does nothing, and one that finds the post already
up on Instagram (a repeated task after a lost answer) only marks it, so a post never goes up twice. A failed post goes
back to draft with the reason shown in the queue; it is not retried by itself. The Graph API costs nothing.
"""
import datetime
import hashlib
import os
import time
from zoneinfo import ZoneInfo

from database.models import SocialPost, db
from services import social_stats
from services.recipe_v2 import tasks
from services.social_stats import StatsError, graph_get, graph_post

OSLO = ZoneInfo('Europe/Oslo')
PUBLISH_PATH = '/internal/tasks/social-publish/{id}'
# The times a day's posts are offered, in order of preference; a day of two gets 11:00 and 18:00
DEFAULT_TIMES = ('18:00', '11:00', '15:00', '07:00', '21:00')
MIN_SLIDES, MAX_SLIDES = 2, 20  # Instagram's limits for a carousel
MAX_SLIDE_BYTES = 8 * 1024 * 1024
READY_TRIES, READY_WAIT = 30, 2  # seconds: how long a container may take before it can be published
EARLY = datetime.timedelta(minutes=1)  # a task this much before its post's time belongs to an older time


def utcnow():
    return datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)


def slides_of(post):
    return (post.slide_urls or '').split('\n') if post.slide_urls else []


def save_slides(post, jpegs, caption, storage):
    """Puts a post's slides on storage for Meta to fetch and keeps them and the text on the post; returns what is wrong,
    or None. A slide's name holds its content's hash, as storage caches a name for a year and a post can be rendered
    again."""
    if not MIN_SLIDES <= len(jpegs) <= MAX_SLIDES:
        return f'a carousel has {MIN_SLIDES} to {MAX_SLIDES} slides, not {len(jpegs)}'
    for n, data in enumerate(jpegs, 1):
        if data[:3] != b'\xff\xd8\xff':
            return f'slide {n} is not a JPEG'
        if len(data) > MAX_SLIDE_BYTES:
            return f'slide {n} is over 8 MB'
    urls = [storage.save(data, f'{n:02d}-{hashlib.sha256(data).hexdigest()[:8]}.jpg', f'social/instagram-{post.code}')
            for n, data in enumerate(jpegs, 1)]
    post.slide_urls = '\n'.join(urls)
    post.caption = caption or post.caption
    post.publish_error = None
    db.session.commit()
    return None


def queue():
    """The Instagram posts with slides that are not up yet, by day: [{'day', 'posts': [{'post', 'slides', 'when'}]}].
    'when' is the time to offer in the form, in Oslo: the approved one, else the day's next default."""
    posts = db.session.execute(
        db.select(SocialPost).where(SocialPost.platform == 'instagram', SocialPost.slide_urls.is_not(None),
                                    SocialPost.status.in_(('draft', 'scheduled')))
        .order_by(SocialPost.posted_on, SocialPost.id)).scalars().all()
    days = {}
    for post in posts:
        days.setdefault(post.posted_on, []).append(post)
    out = []
    for day, members in days.items():
        times = sorted(DEFAULT_TIMES[:len(members)]) + [DEFAULT_TIMES[-1]] * max(len(members) - len(DEFAULT_TIMES), 0)
        rows = []
        for post, default in zip(members, times):
            when = (post.scheduled_at.replace(tzinfo=datetime.timezone.utc).astimezone(OSLO)
                    if post.scheduled_at else datetime.datetime.fromisoformat(f'{day.isoformat()}T{default}'))
            rows.append({'post': post, 'slides': slides_of(post), 'when': when.strftime('%Y-%m-%dT%H:%M')})
        out.append({'day': day, 'posts': rows})
    return out


def parse_when(value):
    """A time typed on the queue, in Oslo, as UTC without a zone; None when it cannot be read."""
    try:
        local = datetime.datetime.fromisoformat((value or '').strip())
    except ValueError:
        return None
    return local.replace(tzinfo=OSLO).astimezone(datetime.timezone.utc).replace(tzinfo=None)


def schedule(post, when, caption, now=None):
    """Approves a post to go up at when (UTC) and queues its task; returns what is wrong, or None."""
    now = now or utcnow()
    if post.status not in ('draft', 'scheduled') or not slides_of(post):
        return f'instagram-{post.code} cannot be scheduled'
    if when is None:
        return f'instagram-{post.code}: give a time'
    if when <= now:
        return f'instagram-{post.code}: the time has passed'
    post.caption = caption.strip() if caption and caption.strip() else post.caption
    post.status, post.scheduled_at, post.publish_error = 'scheduled', when, None
    db.session.commit()
    try:
        tasks._queue(PUBLISH_PATH.format(id=post.id), {}, at=when)
    except Exception as e:  # the queue did not take it: not scheduled after all
        post.status, post.scheduled_at = 'draft', None
        post.publish_error = 'The queue did not take it. Try again.'
        db.session.commit()
        print(f'social-publish: instagram-{post.code} not queued: {e}')
        return f'instagram-{post.code}: the queue did not take it. Try again.'
    return None


def cancel(post):
    """Back to draft; its task finds that and does nothing."""
    if post.status == 'scheduled':
        post.status, post.scheduled_at = 'draft', None
        db.session.commit()


def _ready(container, get, wait):
    for _ in range(READY_TRIES):
        status = get(container, {'fields': 'status_code'}).get('status_code')
        if status == 'FINISHED':
            return
        if status in ('ERROR', 'EXPIRED'):
            raise StatsError(f'Instagram could not read the post ({status})')
        wait(READY_WAIT)
    raise StatsError('Instagram took too long with the post')


def _went_up(post, media_id, permalink, now):
    post.status, post.posted_on, post.media_id = 'posted', now.date(), media_id
    post.url, post.publish_error = permalink or post.url, None
    db.session.commit()


def publish(post, get=graph_get, send=graph_post, wait=time.sleep, now=None):
    """What a post's task does, when it comes: returns 'posted', 'already up', 'failed', or why it did nothing."""
    now = now or utcnow()
    if post.status != 'scheduled':
        return 'not scheduled'
    if post.scheduled_at and post.scheduled_at - now > EARLY:
        return 'not yet'
    user = os.environ['INSTAGRAM_USER_ID']
    try:
        for item in get(f'{user}/media', {'fields': 'id,caption,permalink', 'limit': 25}).get('data', []):
            if social_stats.code_of(item.get('caption')) == post.code:
                _went_up(post, item['id'], item.get('permalink'), now)
                return 'already up'
        limit = (get(f'{user}/content_publishing_limit', {'fields': 'config,quota_usage'}).get('data') or [{}])[0]
        total = (limit.get('config') or {}).get('quota_total')
        if total and limit.get('quota_usage', 0) >= total:
            raise StatsError(f'Instagram\'s limit of {total} posts in 24 hours is reached')
        children = []
        for url in slides_of(post):
            child = send(f'{user}/media', {'image_url': url, 'is_carousel_item': 'true'})['id']
            _ready(child, get, wait)
            children.append(child)
        carousel = send(f'{user}/media', {'media_type': 'CAROUSEL', 'children': ','.join(children),
                                          'caption': post.caption or '', 'is_ai_generated': 'true'})['id']
        _ready(carousel, get, wait)
        media_id = send(f'{user}/media_publish', {'creation_id': carousel})['id']
    except (StatsError, KeyError) as e:
        post.status, post.scheduled_at = 'draft', None
        post.publish_error = str(e) if isinstance(e, StatsError) else 'Instagram gave no id for the post'
        db.session.commit()
        print(f'social-publish: instagram-{post.code} failed: {post.publish_error}')
        return 'failed'
    try:
        permalink = get(media_id, {'fields': 'permalink'}).get('permalink')
    except StatsError:
        permalink = None  # it is up; the daily fetch finds the link
    _went_up(post, media_id, permalink, now)
    return 'posted'
