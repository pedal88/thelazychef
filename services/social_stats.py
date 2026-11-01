"""The platforms' numbers for the post log, fetched instead of typed in (docs/SOCIAL.md, services/funnel.py).

Instagram: the Graph API through the Meta app "The Lazy Chef stats" (Instagram API with Unified login, in development
mode), with a system-user token that never expires (INSTAGRAM_ACCESS_TOKEN) for the account INSTAGRAM_USER_ID. Once a
day (the Cloud Scheduler job social-stats calls /internal/tasks/social-stats, or Fetch from Instagram on the Funnel
page) the account's latest posts are read and matched to the post log: by the code in the caption
(thelazychef.app/ig/5), else by the post's link. A draft the batch logged becomes posted on the day Instagram says it
went up, with its link. Each posted Instagram post then gets its numbers for the day after it went up it is now: every
day for the first FETCH_DAILY days, and on the days in FETCH_LATE. A row typed in by hand for that day is left alone.
Days are counted in UTC, as Instagram's timestamps are. The Graph API costs nothing.

TikTok has no fetch: its Accounts API needs a verified company (~/promptlab-runs/social/notes/automatisering.md).
"""
import datetime
import os
import re

import requests

from database.models import SocialPost, SocialPostStat, db

GRAPH = 'https://graph.facebook.com/v26.0'
# Instagram's metric for a carousel -> the post log's field
METRICS = {'views': 'views', 'reach': 'reach', 'likes': 'likes', 'comments': 'comments', 'saved': 'saves',
           'shares': 'shares', 'profile_visits': 'profile_visits'}
FETCH_DAILY = 14
FETCH_LATE = (30,)
MEDIA_PAGES = 4  # 25 posts a page: the latest 100
CODE = re.compile(r'thelazychef\.app/ig/([a-z0-9_]+)', re.IGNORECASE)


class StatsError(Exception):
    """Instagram did not answer, or answered with an error; the message is Meta's, never the token."""


def configured():
    return bool(os.environ.get('INSTAGRAM_ACCESS_TOKEN') and os.environ.get('INSTAGRAM_USER_ID'))


def graph_get(path, params):
    """GET a Graph API path with the token: the JSON answer, or StatsError."""
    try:
        res = requests.get(f'{GRAPH}/{path}', timeout=30,
                           params={**params, 'access_token': os.environ['INSTAGRAM_ACCESS_TOKEN']})
        body = res.json()
    except (requests.RequestException, ValueError):
        # Not from the exception: its text can hold the address with the token
        raise StatsError('Instagram did not answer') from None
    if res.status_code >= 400 or 'error' in body:
        raise StatsError((body.get('error') or {}).get('message') or f'Instagram answered {res.status_code}')
    return body


def media(get=graph_get):
    """The account's latest posts, newest first: [{'id', 'caption', 'permalink', 'timestamp', 'media_type'}]."""
    path = f"{os.environ['INSTAGRAM_USER_ID']}/media"
    params = {'fields': 'id,caption,permalink,timestamp,media_type', 'limit': 25}
    items = []
    for _ in range(MEDIA_PAGES):
        body = get(path, params)
        items += body.get('data', [])
        paging = body.get('paging') or {}
        after = (paging.get('cursors') or {}).get('after')
        if not paging.get('next') or not after:
            break
        params = {**params, 'after': after}
    return items


def insights(media_id, get=graph_get):
    """{post log field: number} for one post; a metric Instagram does not give is left out."""
    body = get(f'{media_id}/insights', {'metric': ','.join(METRICS)})
    return {METRICS[m['name']]: (m.get('values') or [{}])[0].get('value') for m in body.get('data', [])
            if m.get('name') in METRICS}


def code_of(caption):
    """The post's code from the address in its caption (thelazychef.app/ig/5 -> '5'), or None."""
    found = CODE.search(caption or '')
    return found.group(1).lower() if found else None


def due(day):
    return 0 <= day <= FETCH_DAILY or day in FETCH_LATE


def fetch_instagram(today=None, get=graph_get, now=None):
    """Reads the account's posts and keeps today's numbers for every logged post that is due. Returns
    {'read', 'matched', 'posted', 'saved', 'unlogged': [links], 'errors': [...]}; StatsError when the posts cannot be
    read at all."""
    today = today or datetime.datetime.now(datetime.timezone.utc).date()
    now = now or datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
    logged = db.session.execute(db.select(SocialPost).filter_by(platform='instagram')).scalars().all()
    by_code = {p.code: p for p in logged}
    by_url = {p.url.rstrip('/'): p for p in logged if p.url}
    summary = {'read': 0, 'matched': 0, 'posted': 0, 'saved': 0, 'unlogged': [], 'errors': []}
    for item in media(get):
        summary['read'] += 1
        code = code_of(item.get('caption'))
        post = by_code.get(code) if code else None
        post = post or by_url.get((item.get('permalink') or '').rstrip('/'))
        if post is None:
            summary['unlogged'].append(item.get('permalink') or item['id'])
            continue
        summary['matched'] += 1
        if post.status == 'draft':
            went_up = datetime.datetime.strptime(item['timestamp'], '%Y-%m-%dT%H:%M:%S%z')
            post.status, post.posted_on = 'posted', went_up.astimezone(datetime.timezone.utc).date()
            summary['posted'] += 1
        post.url = post.url or item.get('permalink')
        day = (today - post.posted_on).days
        if not due(day):
            continue
        stat = next((s for s in post.stats if s.day == day), None)
        if stat is not None and stat.source == 'manual':
            continue
        try:
            numbers = insights(item['id'], get)
        except StatsError as e:
            summary['errors'].append(f'instagram-{post.code}: {e}')
            continue
        if stat is None:
            stat = SocialPostStat(day=day)
            post.stats.append(stat)
        for key, value in numbers.items():
            setattr(stat, key, value)
        stat.source, stat.fetched_at = 'instagram', now
        summary['saved'] += 1
    db.session.commit()
    return summary


def report(summary):
    """One line for the Funnel page and the job's log."""
    line = (f"Instagram: {summary['read']} posts read, {summary['matched']} in the log, {summary['saved']} numbers "
            f"saved, {summary['posted']} drafts marked posted.")
    if summary['unlogged']:
        line += f" Not in the log: {len(summary['unlogged'])}."
    if summary['errors']:
        line += ' Errors: ' + '; '.join(summary['errors'][:3])
    return line
