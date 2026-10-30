"""Photograph a TikTok or Instagram post: every slide as a PNG, and a first draft of the text (docs/SOCIAL.md).

    python -m scripts.social_render map 345 --size ig --code 1     # Dinner as a subway map, recipe 345, for Instagram
    python -m scripts.social_render grid 345 --size tt --code 2    # Everything in a dish, for TikTok
    python -m scripts.social_render pantry --size tt --code 3      # The foundation pantry
    python -m scripts.social_render map 345 --look e               # in another look than the site's (today, c, d, e, f)
    python -m scripts.social_render week --size tt --code 4        # One shop, five dinners (the site picks the five)
    python -m scripts.social_render week --ids 320,324,334,341,353 # ... or these five, in this order

Reads the public slide pages (/social/…) from production by default, or --base http://127.0.0.1:8000 for a local app,
and takes each picture with headless Chrome (--chrome, or $CHROME; the macOS path by default). Nothing is written to
production and nothing costs money. The pictures go to ~/promptlab-runs/social/<date>-<format>-<recipe>-<size>/, outside
the repo: they hold recipe content. --code is the post's code in the address on the last slide
(thelazychef.app/tiktok/3), so the Funnel page tells this post's visits from the others'.
"""
import argparse
import datetime
import os
import ssl
import subprocess
import sys
import tempfile
import urllib.parse
import urllib.request
from pathlib import Path

CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'


def tls():
    """certifi's certificates when it is there: python.org's Python on macOS has none of its own until its Install
    Certificates script has run, and https to the site fails."""
    try:
        import certifi
    except ImportError:
        return None
    return ssl.create_default_context(cafile=certifi.where())


SIZES = {'ig': (1080, 1350), 'tt': (1080, 1920)}
# Headless Chrome now and then hangs on a page and never takes the picture, and a request to the site can stall: both
# are stopped after SHOT_SECONDS and tried again, SHOT_TRIES times in all; Chrome each time with a profile of its own,
# so a stuck one cannot lock the next
SHOT_SECONDS = 90
SHOT_TRIES = 3


def fetch(url, context):
    """(headers, text) of a page, tried again when it stalls."""
    for attempt in range(1, SHOT_TRIES + 1):
        try:
            with urllib.request.urlopen(url, context=context, timeout=SHOT_SECONDS) as response:
                return response.headers, response.read().decode('utf-8')
        except TimeoutError:
            if attempt == SHOT_TRIES:
                raise
            print(f'{url}: no answer, trying again')


def shoot(chrome, width, height, target, url):
    for attempt in range(1, SHOT_TRIES + 1):
        with tempfile.TemporaryDirectory(prefix='social-chrome-') as profile:
            try:
                # virtual-time-budget lets the fonts and the symbols load before the picture is taken
                subprocess.run([chrome, '--headless', '--disable-gpu', '--hide-scrollbars',
                                f'--user-data-dir={profile}', '--force-device-scale-factor=1',
                                f'--window-size={width},{height}',
                                '--virtual-time-budget=10000', f'--screenshot={target}', url],
                               check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=SHOT_SECONDS)
                return
            except subprocess.TimeoutExpired:
                if attempt == SHOT_TRIES:
                    raise
                print(f'{target.name}: Chrome hung, trying again')


def page_url(base, fmt, recipe, **args):
    path = f'/social/{fmt}' if fmt in ('pantry', 'week') else f'/social/recipe/{recipe}/{fmt}'
    return f'{base.rstrip("/")}{path}?{urllib.parse.urlencode({k: v for k, v in args.items() if v})}'


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('format', choices=['map', 'grid', 'pantry', 'week'])
    p.add_argument('recipe', nargs='?', type=int, help='the recipe id (map and grid only)')
    p.add_argument('--ids', help='week: the five recipe ids, comma separated, instead of the ones the site picks')
    p.add_argument('--size', choices=sorted(SIZES), default='ig')
    p.add_argument('--code', help="the post's code in the address, e.g. 3 for thelazychef.app/tiktok/3")
    p.add_argument('--look', choices=['today', 'c', 'd', 'e', 'f'],
                   help="another look than the site's (routes/_shared.SITE_LOOK): one of the style trial's, or today's")
    p.add_argument('--base', default='https://thelazychef.app')
    p.add_argument('--chrome', default=os.environ.get('CHROME', CHROME))
    p.add_argument('--out', type=Path, default=Path.home() / 'promptlab-runs' / 'social')
    args = p.parse_args()
    if (args.format in ('pantry', 'week')) == (args.recipe is not None):
        p.error('give a recipe id for map and grid, and none for pantry and week')

    query = {'size': args.size, 'code': args.code, 'look': args.look, 'ids': args.ids}
    first = page_url(args.base, args.format, args.recipe, **query, slide=1)
    context = tls()
    count = int(fetch(first, context)[0]['X-Slides'])
    caption = fetch(page_url(args.base, args.format, args.recipe, **query, caption=1), context)[1]

    name = '-'.join(str(x) for x in (datetime.date.today().isoformat(), args.format, args.recipe, args.size, args.code,
                                     args.look and f'look-{args.look}')
                    if x is not None)
    folder = args.out / name
    folder.mkdir(parents=True, exist_ok=True)
    width, height = SIZES[args.size]
    for n in range(1, count + 1):
        target = folder / f'{n:02d}.png'
        shoot(args.chrome, width, height, target, page_url(args.base, args.format, args.recipe, **query, slide=n))
        print(f'{target}')
    (folder / 'caption.txt').write_text(caption, encoding='utf-8')
    print(f'\n{count} slides and caption.txt in {folder}\n\n{caption}')


if __name__ == '__main__':
    sys.exit(main())
