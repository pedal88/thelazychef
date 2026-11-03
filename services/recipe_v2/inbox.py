"""The video inbox: cooking videos shared from the phone, saved to look at later (table video_inbox).

Saving makes nothing and costs nothing: the link is kept, and Pål picks later what to make. A video is known by its
key, so the same video shared twice or linked another way is one row, and a video already made into a recipe is marked.
"""
import re
from urllib.parse import parse_qs, urlparse, urlunparse

from database.models import Recipe, VideoInbox, db
from services.recipe_v2.sources import is_video

LINK = re.compile(r'https?://[^\s<>"\']+', re.IGNORECASE)
# The ways the same video is linked: (host, pattern on the path, the key's prefix)
KEYS = (('tiktok.com', re.compile(r'/video/(\d+)'), 'tiktok'),
        ('instagram.com', re.compile(r'/(?:reels?|p|tv)/([\w-]+)'), 'instagram'),
        ('youtube.com', re.compile(r'/(?:shorts|embed|live)/([\w-]+)'), 'youtube'),
        ('youtu.be', re.compile(r'/([\w-]+)'), 'youtube'))


def first_link(text):
    """The first link in what was shared: an app can send words around it ("Look at this! https://…")."""
    found = LINK.search(text or '')
    return found.group(0).rstrip('.,;:!?)') if found else None


def clean_url(url):
    """The link without its tracking (?igsh=…, ?_t=…). Only a YouTube watch link needs its query."""
    parts = urlparse(url)
    video = parse_qs(parts.query).get('v', [''])[0] if parts.path.rstrip('/') == '/watch' else ''
    return urlunparse(parts._replace(query=f'v={video}' if video else '', fragment=''))


def video_key(url):
    """The same for every link to one video. A short link (vm.tiktok.com/abc) has only itself to go by."""
    parts = urlparse(url)
    host = (parts.hostname or '').lower().removeprefix('www.')
    if host.endswith('youtube.com') and parts.path.rstrip('/') == '/watch' and parse_qs(parts.query).get('v'):
        return 'youtube:' + parse_qs(parts.query)['v'][0]
    for name, pattern, prefix in KEYS:
        if host == name or host.endswith('.' + name):
            found = pattern.search(parts.path)
            if found:
                return f'{prefix}:{found.group(1)}'
    return f"{host}{parts.path.rstrip('/')}"


def add(shared):
    """Save what was shared. Returns (row, 'saved' or 'again'); (None, None) when it holds no video link. Sharing a
    discarded video again takes it back. The caller commits."""
    link = first_link(shared)
    if not link or not is_video(link):
        return None, None
    url = clean_url(link)
    key = video_key(url)
    row = db.session.execute(db.select(VideoInbox).filter_by(video_key=key)).scalar_one_or_none()
    if row is not None:
        row.status = 'new'
        return row, 'again'
    row = VideoInbox(url=url, video_key=key)
    db.session.add(row)
    return row, 'saved'


def made_from():
    """{video key: recipe id} of the recipes made from a video, the newest for a video made twice."""
    rows = db.session.execute(db.select(Recipe.id, Recipe.source_input).where(
        Recipe.source_type == 'video', Recipe.source_input.isnot(None)).order_by(Recipe.id)).all()
    return {video_key(source): rid for rid, source in rows}


def rows(status='new'):
    """The rows with the status, newest first, as (row, id of the recipe made from it or None)."""
    made = made_from()
    found = db.session.execute(db.select(VideoInbox).filter_by(status=status).order_by(VideoInbox.id.desc())).scalars()
    return [(row, made.get(row.video_key)) for row in found]
