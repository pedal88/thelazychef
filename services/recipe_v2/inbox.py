"""The video inbox: cooking videos shared from the phone, saved to look at later (table video_inbox).

Saving makes no recipe: the link is kept, and Pål picks later what to make. A video is known by its key, so the same
video shared twice or linked another way is one row, and a video already made into a recipe is marked.

Each saved video is looked up in the background (look_up): its caption with yt-dlp, without downloading it, then one
small Claude call for the dish's name, the recipes it looks most like and suggested metadata. It need not be perfect,
since making the recipe has its own logic. Under a cent a video; no video goes to Gemini here.

Many links can be saved at once, from pasted text or a file such as TikTok's data download (sort, save_many). The text
can be anything: links are read out of it, so nothing here depends on the file's format.
"""
import io
import json
import os
import re
import zipfile
from urllib.parse import parse_qs, urlparse, urlunparse

from jinja2 import Environment, FileSystemLoader

from database.models import Recipe, VideoInbox, db
from schemas.recipe_v2 import CUISINES, MEAL_TYPES
from services import ai_models
from services.recipe_v2 import claude
from services.recipe_v2.sources import is_video

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
env = Environment(loader=FileSystemLoader(os.path.join(ROOT, 'data', 'prompts')))
CAPTION_MAX = 4000  # what the model reads of a caption
SIMILAR_MAX = 3
NO_DETAILS = 'Could not read the video\'s details. It may be private or blocked; it can still be tried as a recipe.'
MAX_LINKS = 1000  # new videos saved at once: a whole data download also lists every video watched
MAX_TEXT = 30 * 1024 * 1024  # bytes read from what is pasted or uploaded; Cloud Run takes 32 MB a request
COST_A_VIDEO = 0.01  # at most, in USD (docs/SERVICES_AND_COSTS.md)

LINK = re.compile(r'https?://[^\s<>"\'\\,\]}]+', re.IGNORECASE)
SHORT_LINKS = ('vm.tiktok.com', 'vt.tiktok.com')  # hosts where a link only says what it is once it is opened
# The ways the same video is linked: (host, pattern on the path, the key's prefix)
KEYS = (('tiktok.com', re.compile(r'/video/(\d+)'), 'tiktok'),
        ('tiktokv.com', re.compile(r'/video/(\d+)'), 'tiktok'),
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


def links_in(text):
    """Every link in the text, whatever the text is: a list, a message or a JSON file with its slashes escaped."""
    text = (text or '').replace('\\/', '/').replace('\\u002F', '/').replace('\\u002f', '/')
    return [m.rstrip('.;:!?)') for m in LINK.findall(text)]


def text_of_upload(data, filename=''):
    """The text of an uploaded file. A zip file gives the text of the files in it, as far as MAX_TEXT goes."""
    if not (filename or '').lower().endswith('.zip'):
        return data[:MAX_TEXT].decode('utf-8', errors='replace')
    parts, left = [], MAX_TEXT
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        for info in z.infolist():
            if left > 0 and not info.is_dir() and info.filename.lower().endswith(('.txt', '.json', '.csv', '.html')):
                with z.open(info) as f:
                    part = f.read(left)
                left -= len(part)
                parts.append(part.decode('utf-8', errors='replace'))
    return '\n'.join(parts)


def _one_video(url):
    """The key of a link to one video we can read; None for other links on those hosts (a profile, a sound)."""
    try:
        if not is_video(url):
            return None
        key = video_key(url)
        host, path = (urlparse(url).hostname or '').lower(), urlparse(url).path
    except ValueError:  # not a real address
        return None
    short = host in SHORT_LINKS or (host.endswith('tiktok.com') and path.startswith('/t/'))
    if len(url) > 1000 or len(key) > 300 or not (short or key.startswith(('tiktok:', 'instagram:', 'youtube:'))):
        return None
    return key


def sort(text):
    """What the links in a text are, saving nothing: {'new': clean links, 'known': how many are in the inbox or made
    already, or there twice, 'other': how many are no video}."""
    seen = set(db.session.execute(db.select(VideoInbox.video_key)).scalars()) | set(made_from())
    new, known, other = [], 0, 0
    for link in links_in(text):
        try:
            url = clean_url(link)
        except ValueError:  # not a real address
            other += 1
            continue
        key = _one_video(url)
        if key is None:
            other += 1
        elif key in seen:
            known += 1
        else:
            seen.add(key)
            new.append(url)
    return {'new': new, 'known': known, 'other': other}


def save_many(text):
    """Save the new videos in the text, up to MAX_LINKS; a discarded video stays discarded. Returns the rows. The caller
    commits and queues the look-ups."""
    rows = [VideoInbox(url=url, video_key=video_key(url)) for url in sort(text)['new'][:MAX_LINKS]]
    db.session.add_all(rows)
    db.session.flush()
    return rows


def waiting():
    """The ids of the videos in the inbox that have not been looked up."""
    return list(db.session.execute(db.select(VideoInbox.id).where(
        VideoInbox.status == 'new', VideoInbox.webpage_url.is_(None), VideoInbox.dish_name.is_(None),
        VideoInbox.meta_error.is_(None)).order_by(VideoInbox.id)).scalars())


def _proteins():
    with open(os.path.join(ROOT, 'data', 'constraints', 'main_protein.json'), encoding='utf-8') as f:
        types = json.load(f)['protein_types']
    return list(dict.fromkeys(label for t in types for label in t['examples'])) + ['Other']


def schema():
    return {'type': 'object', 'additionalProperties': False,
            'required': ['is_recipe', 'dish_name', 'cuisine', 'main_protein', 'meal_types', 'similar'],
            'properties': {'is_recipe': {'type': 'boolean'}, 'dish_name': {'type': 'string'},
                           'cuisine': {'type': 'string', 'enum': list(CUISINES)},
                           'main_protein': {'type': 'string', 'enum': _proteins()},
                           'meal_types': {'type': 'array', 'items': {'type': 'string', 'enum': list(MEAL_TYPES)}},
                           'similar': {'type': 'array', 'items': {'type': 'integer'}}}}


def recipe_titles():
    """{id: title} of the approved recipes, without versions: what a video can look like."""
    return dict(db.session.execute(db.select(Recipe.id, Recipe.title).where(
        Recipe.status == 'approved', Recipe.schema_version == 2, Recipe.base_recipe_id.is_(None)).order_by(Recipe.id)).all())


def describe(row, title, call=None):
    """What the caption says the video is, in one small call. Only what the app knows is kept: the text comes from
    strangers, and the answer only ever fills these fields."""
    titles = recipe_titles()
    system = env.get_template('recipe_v2/inbox.jinja2').render(recipes=titles)
    user = f"TITLE\n{title or ''}\n\nUPLOADER\n{row.uploader or ''}\n\nCAPTION\n{(row.caption or '')[:CAPTION_MAX]}"
    msg, _ = (call or claude.call)(ai_models.VIDEO_INBOX_MODEL, ai_models.VIDEO_INBOX_EFFORT, [{'role': 'user', 'content': user}],
                                   system=system, schema=schema())
    answer = json.loads(claude.text_of(msg))
    row.dish_name = (answer.get('dish_name') or '').strip()[:200] or None
    row.similar = [i for i in dict.fromkeys(answer.get('similar') or []) if i in titles][:SIMILAR_MAX]
    row.suggestions = {k: answer.get(k) for k in ('is_recipe', 'cuisine', 'main_protein', 'meal_types')}


def look_up(row, extract=None, call=None):
    """Fill the row from the video's page and its caption. A video that cannot be read keeps its link and says why. A
    short link that turns out to be a video already in the inbox is removed: returns the row that stays. The caller commits."""
    from services.social_media_service import SocialMediaExtractor

    try:
        info = (extract or SocialMediaExtractor.extract_metadata)(row.url)
    except ValueError:  # private, removed or blocked: trying again does not help
        row.meta_error = NO_DETAILS
        return row
    row.webpage_url = clean_url(info['webpage_url']) if info.get('webpage_url') else None
    row.caption, row.duration_s = info.get('caption'), int(info['duration']) if info.get('duration') else None
    row.uploader = (info.get('uploader') or '')[:200] or None
    key = video_key(row.webpage_url or row.url)
    if key != row.video_key:
        other = db.session.execute(db.select(VideoInbox).filter_by(video_key=key)).scalar_one_or_none()
        if other is not None:
            db.session.delete(row)
            return other
        row.video_key = key
    row.meta_error = None
    if row.caption or info.get('title'):  # nothing to read costs nothing
        describe(row, info.get('title'), call=call)
    return row


def lines(ids):
    """The chosen videos as lines for Many recipes at once (services/recipe_v2/batch.py), in the order of the list."""
    found = db.session.execute(db.select(VideoInbox).where(VideoInbox.id.in_(ids)).order_by(VideoInbox.id.desc())).scalars()
    return '\n'.join(row.webpage_url or row.url for row in found)


def rows(status='new'):
    """The rows with the status, newest first, as (row, id of the recipe made from it or None)."""
    made = made_from()
    found = db.session.execute(db.select(VideoInbox).filter_by(status=status).order_by(VideoInbox.id.desc())).scalars()
    return [(row, made.get(row.video_key)) for row in found]
