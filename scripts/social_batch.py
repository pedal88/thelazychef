"""A day of TikTok and Instagram posts in one go: plan them, log them as drafts with their codes, render every slide
in both sizes, and put them where the phone can reach them (docs/SOCIAL.md, "A day of posts").

    python -m scripts.social_batch 2026-11-03                    # the day's series (below)
    python -m scripts.social_batch 2026-11-03 --plan day.txt     # the posts in a plan
    python -m scripts.social_batch 2026-11-03 --dry-run          # show the plan, log and render nothing

Without a plan a day is the four series that run side by side (airfryer, got, protein, dishes) and a fifth post:
Guess the dinner on Mondays and Fridays, a cuisine week on Wednesdays, else one of the four again by turn
(~/promptlab-runs/social/notes/serier.md). Each series picks its own recipes and number, as on /social/post.

A plan has a post per line: a series or a format, the recipes if they are to be fixed (comma separated), then
hook=, cta= and n= if they are to be fixed, and for a format after | the words it tries. # starts a comment.

    airfryer hook=number cta=follow
    got 323,326,329 hook=search
    guess
    map 345 cta=save | 4 lines, 1 plate, 42 minutes
    week 320,324,334,341,353
    pantry

For a series the script asks the site first what it chose (the slide page's headers: recipes, number, hook, CTA per
platform, views, look) and logs the post in the Funnel page's post log as a draft on both platforms under one code,
through the social API with the content API's key (CONTENT_API_KEY or the Keychain item, as scripts/content.py). The
next post of the same series then sees those recipes as used and takes the next number. Then both sizes are rendered
with that code and those choices fixed (scripts/social_render.py). A series that has run out is skipped and said so.

The slides go to ~/promptlab-runs/social/<day>/: a folder per post and size with the PNGs, caption.txt and title.txt
(the hook's words, for TikTok's title), day.txt listing the posts, and plan.json with what was logged. Running the same
day again reads plan.json, plans only the posts it lacks and renders only what is missing (--force renders again;
--replan plans the whole day anew, which logs new drafts). Each folder is copied to --phone (an iCloud Drive folder by
default), so it is on the phone without AirDrop.

Nothing is posted and nothing costs money. Put each post up by hand (docs/SOCIAL.md) and mark it posted on the Funnel
page. --base (or LAZYCHEF_URL) points it at another copy of the app, e.g. http://127.0.0.1:8000.
"""
import argparse
import datetime
import json
import os
import shutil
import sys
import urllib.error
from pathlib import Path

import requests

from scripts.content import _key
from scripts.social_render import CHROME, CTAS, HOOKS, PLATFORM_OF_SIZE, SERIES, fetch, page_url, render, tls

PHONE = Path.home() / 'Library' / 'Mobile Documents' / 'com~apple~CloudDocs' / 'The Lazy Chef'
SIZES = ('tt', 'ig')
FORMATS = ('map', 'grid', 'pantry', 'week')
# A day without a plan: the four series that run side by side, and the fifth post by weekday (Monday is 0)
DAY_SERIES = ('airfryer', 'got', 'protein', 'dishes')
FIFTH = {0: 'guess', 2: 'cuisine', 4: 'guess'}


def day_plan(day):
    """The posts of a day without a plan: DAY_SERIES, then FIFTH's series for the weekday or one of DAY_SERIES by
    turn."""
    fifth = FIFTH.get(day.weekday(), DAY_SERIES[day.toordinal() % len(DAY_SERIES)])
    return [{'kind': slug} for slug in DAY_SERIES + (fifth,)]


def parse_plan(text):
    """[{'kind', 'ids', 'hook', 'cta', 'n', 'words'}] from a plan's lines (only the keys a line gives besides kind);
    raises ValueError on a line it cannot read."""
    posts = []
    for number, line in enumerate(text.splitlines(), 1):
        line = line.split('#', 1)[0]
        head, _, words = line.partition('|')
        tokens = head.split()
        if not tokens:
            continue
        kind, post = tokens[0], {'kind': tokens[0]}
        problem = None
        if kind not in SERIES and kind not in FORMATS:
            problem = f'{kind} is not a series ({", ".join(SERIES)}) or a format ({", ".join(FORMATS)})'
        for token in tokens[1:]:
            key, eq, value = token.partition('=')
            if not eq and all(x.isdigit() for x in token.split(',')) and 'ids' not in post:
                post['ids'] = [int(x) for x in token.split(',')]
            elif key == 'hook' and value in HOOKS or key == 'cta' and value in CTAS:
                post[key] = value
            elif key == 'n' and value.isdigit() and kind in SERIES:
                post['n'] = int(value)
            else:
                problem = problem or f'"{token}" is not recipes (1,2,3), hook=<{"|".join(HOOKS)}>, ' \
                                     f'cta=<{"|".join(CTAS)}> or n=<number> (series)'
        if kind in ('map', 'grid') and len(post.get('ids') or []) != 1:
            problem = problem or f'{kind} takes one recipe'
        if kind == 'pantry' and post.get('ids') or kind == 'week' and post.get('ids') and len(post['ids']) != 5:
            problem = problem or ('pantry takes no recipes' if kind == 'pantry' else 'a week takes five recipes')
        if words.strip():
            if kind in SERIES:
                problem = problem or 'a series writes its own hook: give hook=<group>, not words after |'
            post['words'] = words.strip()
        if problem:
            raise ValueError(f'line {number}: {problem}')
        posts.append(post)
    return posts


def api(base, path, body):
    resp = requests.post(f'{base.rstrip("/")}/api/social{path}', json=body,
                         headers={'Authorization': f'Bearer {_key()}'}, timeout=120)
    try:
        answer = resp.json()
    except ValueError:
        sys.exit(f'{resp.status_code} from {path}: {resp.text[:300]}')
    if resp.status_code >= 400:
        sys.exit(f'{resp.status_code} from {path}:\n' + '\n'.join(
            f'  - {e}' for e in answer.get('errors') or [answer.get('error', resp.status_code)]))
    return answer


def ids_text(ids):
    return ','.join(str(i) for i in ids) if ids else None


def plan_post(post, base, look, context):
    """(the draft to log, the slide pages' query without size and code, the page's format, its recipe), or None when
    a series has nothing left to post. A series is asked what it chooses, in both sizes (the CTA can differ: no bio
    link on TikTok)."""
    kind = post['kind']
    if kind in SERIES:
        asked = {'series': kind, 'ids': ids_text(post.get('ids')), 'n': post.get('n'), 'hook': post.get('hook'),
                 'cta': post.get('cta'), 'look': look}
        heads = {}
        for size in SIZES:
            try:
                heads[size] = fetch(page_url(base, 'series', None, **asked, size=size, slide=1), context)[0]
            except urllib.error.HTTPError as e:
                if e.code != 404:
                    raise
                return None
        h = heads['tt']
        draft = {'format': 'series', 'series': kind, 'series_n': int(h['X-N']),
                 'ids': [int(i) for i in h['X-Recipes'].split(',')], 'hook': h['X-Hook-Text'],
                 'hook_group': h['X-Hook'], 'views': h['X-Views'], 'look': h['X-Look'], 'slides': int(h['X-Slides']),
                 'cta_group': {PLATFORM_OF_SIZE[size]: heads[size]['X-Cta'] for size in SIZES}}
        query = {**asked, 'ids': h['X-Recipes'], 'n': h['X-N'], 'hook': h['X-Hook']}
        return draft, query, 'series', None
    recipe = post['ids'][0] if kind in ('map', 'grid') else None
    draft = {'format': kind, 'recipe_id': recipe, 'ids': post.get('ids') if kind == 'week' else None,
             'hook': post.get('words'), 'hook_group': post.get('hook'), 'cta_group': post.get('cta')}
    query = {'ids': ids_text(post.get('ids')) if kind == 'week' else None, 'hook': post.get('hook'),
             'cta': post.get('cta'), 'look': look}
    return draft, query, kind, recipe


def folder_name(place, entry):
    what = entry['series'] and f"{entry['series']}{entry['series_n']}" or entry['format']
    recipes = (entry['recipe_ids'] or '').replace(',', '-') or None
    return '-'.join(str(x) for x in (place, f"code{entry['code']}", what, recipes) if x)


def rendered(folder):
    return (folder / 'caption.txt').exists() and any(folder.glob('*.png'))


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('day', type=datetime.date.fromisoformat, help='the day the posts go up, e.g. 2026-11-03')
    p.add_argument('--plan', type=Path, help="the posts, a line each (see above); else the day's series")
    p.add_argument('--dry-run', action='store_true', help='show the plan; log and render nothing')
    p.add_argument('--replan', action='store_true', help="plan the day anew even when it has a plan.json")
    p.add_argument('--force', action='store_true', help='render slides again that are already there')
    p.add_argument('--look', choices=['today', 'c', 'd', 'e', 'f'], help="another look than the site's")
    p.add_argument('--base', default=os.environ.get('LAZYCHEF_URL', 'https://thelazychef.app'))
    p.add_argument('--chrome', default=os.environ.get('CHROME', CHROME))
    p.add_argument('--out', type=Path, default=Path.home() / 'promptlab-runs' / 'social')
    p.add_argument('--phone', type=Path, default=PHONE if PHONE.parent.exists() else None,
                   help=f'where the phone finds the slides (default {PHONE}, when iCloud Drive is there)')
    p.add_argument('--no-phone', action='store_true', help='copy nothing to the phone folder')
    args = p.parse_args()

    if args.plan:
        try:
            posts = parse_plan(args.plan.read_text(encoding='utf-8'))
        except ValueError as e:
            p.error(f'{args.plan}: {e}')
    else:
        posts = day_plan(args.day)
    if args.dry_run:
        for place, post in enumerate(posts, 1):
            print(f"{place}. {' '.join(f'{k}={v}' if k != 'kind' else v for k, v in post.items())}")
        return

    day_folder = args.out / args.day.isoformat()
    manifest = day_folder / 'plan.json'
    entries = json.loads(manifest.read_text(encoding='utf-8')) if manifest.exists() and not args.replan else []
    context = tls()
    day_folder.mkdir(parents=True, exist_ok=True)
    done = {entry['place'] for entry in entries}
    for place, post in enumerate(posts, 1):
        if place not in done:
            planned = plan_post(post, args.base, args.look, context)
            if planned is None:
                print(f"{place}. {post['kind']}: nothing left to post (the series has run out, or a recipe is not "
                      'public); skipped')
                continue
            draft, query, fmt, recipe = planned
            logged = api(args.base, '/drafts', {'day': args.day.isoformat(), 'posts': [draft]})['posts'][0]
            entries.append({**logged, 'place': place, 'page': fmt, 'recipe': recipe, 'query': query})
            manifest.write_text(json.dumps(entries, indent=1, ensure_ascii=False), encoding='utf-8')

    summary = []
    for entry in sorted(entries, key=lambda e: e['place']):
        name = folder_name(entry['place'], entry)
        for size in SIZES:
            folder = day_folder / name / size
            if args.force or not rendered(folder):
                render(args.base, args.chrome, folder, entry['page'], entry['recipe'],
                       {**entry['query'], 'size': size, 'code': entry['code']}, context)
            if entry['hook']:
                (folder / 'title.txt').write_text(entry['hook'], encoding='utf-8')
            if args.phone and not args.no_phone:
                shutil.copytree(folder, args.phone / args.day.isoformat() / f'{name}-{PLATFORM_OF_SIZE[size]}',
                                dirs_exist_ok=True)
        summary.append(f"{entry['place']}. code {entry['code']}  {entry['title']}"
                       + ('' if entry['new'] else '  (logged before: same code)'))

    text = (f'{args.day.isoformat()}: {len(entries)} posts, drafts on TikTok and Instagram in the post log\n\n'
            + '\n'.join(summary)
            + f"\n\nThe slides: {day_folder}"
            + (f"\nOn the phone: {args.phone / args.day.isoformat()}" if args.phone and not args.no_phone else '')
            + f"\nWhen a post is up, mark it posted: {args.base.rstrip('/')}/admin/funnel#posts\n")
    (day_folder / 'day.txt').write_text(text, encoding='utf-8')
    print('\n' + text)


if __name__ == '__main__':
    sys.exit(main())
