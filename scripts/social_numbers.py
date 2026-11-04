"""TikTok's numbers for the week into the Funnel page's post log, read off a screenshot of Posts in TikTok Studio into a
CSV (docs/SOCIAL.md, "TikTok's numbers"). TikTok itself is never touched by this script.

    python -m scripts.social_numbers numbers.csv                  # says what the rows come to, saves nothing
    python -m scripts.social_numbers numbers.csv --apply          # and saves them
    python -m scripts.social_numbers numbers.csv --on 2026-11-08  # read on another day than today

The CSV has a header and a row per post: code, views, likes, comments, and if the list or a post's page shows them shares and
saves, and posted_on (YYYY-MM-DD) for a post still a draft in the log, which marks it posted. It goes through the social API
with the content API's key (CONTENT_API_KEY or the Keychain item, as scripts/content.py). Nothing is saved when one row is
wrong. It costs nothing. --base (or LAZYCHEF_URL) points it at another copy of the app.
"""
import argparse
import csv
import datetime
import os
import sys

from scripts.social_batch import api

COLUMNS = ('code', 'views', 'likes', 'comments', 'shares', 'saves', 'posted_on')


def read_rows(path):
    """The CSV's rows with the columns it fills: [{'code': '6', 'views': '276', …}]."""
    with open(path, encoding='utf-8-sig', newline='') as f:
        rows = [{key: (row.get(key) or '').strip() for key in COLUMNS if (row.get(key) or '').strip()}
                for row in csv.DictReader(f)]
    return [row for row in rows if row]


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('csv', help='the numbers, a row per post')
    p.add_argument('--on', type=datetime.date.fromisoformat, default=datetime.date.today(),
                   help='the day they were read (default today)')
    p.add_argument('--apply', action='store_true', help='save them; without it nothing is saved')
    p.add_argument('--base', default=os.environ.get('LAZYCHEF_URL', 'https://thelazychef.app'))
    args = p.parse_args()

    rows = read_rows(args.csv)
    if not rows:
        sys.exit(f'{args.csv}: no rows')
    answer = api(args.base, '/tiktok-numbers', json={'on': args.on.isoformat(), 'dry_run': not args.apply, 'posts': rows})
    for post in answer['posts']:
        numbers = ', '.join(f'{key} {post[key]}' for key in ('views', 'likes', 'comments', 'shares', 'saves')
                            if post.get(key) is not None)
        print(f"{post['ref']}  day {post['day']}{'  marked posted' if post['marked_posted'] else ''}: {numbers}")
    print(f"\n{len(answer['posts'])} posts {'saved' if answer['saved'] else 'checked, nothing saved: --apply saves them'}")


if __name__ == '__main__':
    sys.exit(main())
