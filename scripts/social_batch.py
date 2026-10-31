"""A day of TikTok and Instagram posts in one go: plan them, log them as drafts with their codes, render every slide
in both sizes, and put them where the phone can reach them (docs/SOCIAL.md, "A day of posts").

    python -m scripts.social_batch 2026-11-03                    # the five posts the site suggests for the day
    python -m scripts.social_batch 2026-11-03 --plan day.txt     # the posts in a plan
    python -m scripts.social_batch 2026-11-03 --dry-run          # show the plan, log and render nothing

A plan has a post per line: the format, the recipe for map and grid (the five ids for a week, or none to let the site
pick), and after | the hook, the words on the first slide or the title the post tries. # starts a comment.

    map 345 | 4 lines, 1 plate, 42 minutes
    grid 297 | Guess the dinner
    week 320,324,334,341,353 | One shop, five dinners
    pantry

Each post is logged in the Funnel page's post log as a draft on both platforms under one code (the social API, with
the content API's key: CONTENT_API_KEY or the Keychain item, as scripts/content.py), then rendered from the site with
that code (scripts/social_render.py). Running the same day again keeps the codes and skips slides already rendered
(--force renders them again). The slides go to ~/promptlab-runs/social/<day>/, with day.txt listing the posts, and a
copy per platform to --phone (an iCloud Drive folder by default), so they are on the phone without AirDrop.

Nothing is posted and nothing costs money. Put each post up by hand (docs/SOCIAL.md) and mark it posted on the Funnel
page. --base (or LAZYCHEF_URL) points it at another copy of the app, e.g. http://127.0.0.1:8000.
"""
import argparse
import datetime
import os
import shutil
import sys
from pathlib import Path

import requests

from scripts.content import _key
from scripts.social_render import CHROME, PLATFORM_OF_SIZE, render, tls

PHONE = Path.home() / 'Library' / 'Mobile Documents' / 'com~apple~CloudDocs' / 'The Lazy Chef'
SIZES = ('tt', 'ig')


def parse_plan(text):
    """[{'format', 'recipe_id', 'ids', 'hook'}] from a plan's lines; raises ValueError on a line it cannot read."""
    posts = []
    for n, line in enumerate(text.splitlines(), 1):
        line = line.split('#', 1)[0]
        words, _, hook = line.partition('|')
        words = words.split()
        if not words:
            continue
        fmt, rest = words[0], words[1:]
        post = {'format': fmt, 'hook': hook.strip() or None}
        try:
            if fmt in ('map', 'grid'):
                if len(rest) != 1:
                    raise ValueError
                post['recipe_id'] = int(rest[0])
            elif fmt == 'week' and rest:
                post['ids'] = [int(i) for i in rest[0].split(',')]
            elif rest:
                raise ValueError
        except ValueError:
            raise ValueError(f'line {n}: "{line.strip()}" is not "map 345 | hook", "week 1,2,3,4,5" or "pantry"')
        posts.append(post)
    return posts


def api(base, method, path, **kw):
    resp = requests.request(method, f'{base.rstrip("/")}/api/social{path}',
                            headers={'Authorization': f'Bearer {_key()}'}, timeout=120, **kw)
    try:
        body = resp.json()
    except ValueError:
        sys.exit(f'{resp.status_code} from {path}: {resp.text[:300]}')
    if resp.status_code >= 400:
        sys.exit(f'{resp.status_code} from {path}:\n' + '\n'.join(
            f'  - {e}' for e in body.get('errors') or [body.get('error', resp.status_code)]))
    return body


def folder_name(n, post):
    what = post['recipe_id'] or ('-'.join(str(i) for i in post['ids']) if post['ids'] else None)
    return '-'.join(str(x) for x in (n, f"code{post['code']}", post['format'], what) if x is not None)


def rendered(folder):
    return (folder / 'caption.txt').exists() and any(folder.glob('*.png'))


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('day', type=datetime.date.fromisoformat, help='the day the posts go up, e.g. 2026-11-03')
    p.add_argument('--plan', type=Path, help='the posts, a line each (see above); else the site suggests them')
    p.add_argument('-n', type=int, default=5, help='how many posts the site suggests (default 5)')
    p.add_argument('--dry-run', action='store_true', help='show the plan; log and render nothing')
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
        posts = api(args.base, 'GET', '/suggest', params={'day': args.day.isoformat(), 'n': args.n})['posts']
        posts = [{'format': x['format'], 'recipe_id': x['recipe_id'], 'hook': None} for x in posts]
    if not posts:
        sys.exit('No posts to make: the plan is empty, or no recipe has rested long enough.')
    if args.dry_run:
        for n, post in enumerate(posts, 1):
            print(f"{n}. {post['format']} {post.get('recipe_id') or post.get('ids') or ''}  {post.get('hook') or ''}")
        return

    planned = api(args.base, 'POST', '/drafts', json={'day': args.day.isoformat(), 'posts': posts})['posts']
    day_folder = args.out / args.day.isoformat()
    context = tls()
    summary = []
    for n, post in enumerate(planned, 1):
        name = folder_name(n, post)
        ids = ','.join(str(i) for i in post['ids']) if post['ids'] else None
        for size in SIZES:
            folder = day_folder / name / size
            if args.force or not rendered(folder):
                render(args.base, args.chrome, folder, post['format'], post['recipe_id'], size, code=post['code'],
                       look=args.look, ids=ids, context=context)
            if post['hook']:
                (folder / 'title.txt').write_text(post['hook'], encoding='utf-8')
            if args.phone and not args.no_phone:
                phone = args.phone / args.day.isoformat() / f'{name}-{PLATFORM_OF_SIZE[size]}'
                shutil.copytree(folder, phone, dirs_exist_ok=True)
        summary.append(f"{n}. code {post['code']}  {post['format']:<6} {post['title']}"
                       + (f"\n   hook: {post['hook']}" if post['hook'] else '')
                       + ('' if post['new'] else '\n   (logged before: same code)'))

    text = (f'{args.day.isoformat()}: {len(planned)} posts, drafts on TikTok and Instagram in the post log\n\n'
            + '\n'.join(summary)
            + f"\n\nThe slides: {day_folder}"
            + (f"\nOn the phone: {args.phone / args.day.isoformat()}" if args.phone and not args.no_phone else '')
            + f"\nWhen a post is up, mark it posted: {args.base.rstrip('/')}/admin/funnel#posts\n")
    (day_folder / 'day.txt').write_text(text, encoding='utf-8')
    print('\n' + text)


if __name__ == '__main__':
    sys.exit(main())
