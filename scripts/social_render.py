"""Photograph a TikTok or Instagram post: every slide as a PNG, and a first draft of the text (docs/SOCIAL.md).

    python -m scripts.social_render map 345 --size ig --code 1     # Dinner as a subway map, recipe 345, for Instagram
    python -m scripts.social_render grid 345 --size tt --code 2    # Everything in a dish, for TikTok
    python -m scripts.social_render pantry --size tt --code 3      # The foundation pantry
    python -m scripts.social_render map 345 --look e               # in another look than the site's (today, c, d, e, f)
    python -m scripts.social_render week --size tt --code 4        # One shop, five dinners (the site picks the five)
    python -m scripts.social_render week --ids 320,324,334,341,353 # ... or these five, in this order
    python -m scripts.social_render --series airfryer --size tt --code 12          # the next Air fryer dinner
    python -m scripts.social_render --series got --ids 323,326,329 --n 4 --hook search --cta save --size ig --code 13
    python -m scripts.social_render grid 345 --hook guess --cta ask                # a hook and a CTA on a format

A series (--series: airfryer, got, protein, dishes, guess, cuisine; services/social_series.py) picks its own recipes
from the site unless --ids gives them (as many as the series takes: one, three for got, five for cuisine), and takes
the next number in the post log unless --n says which. --hook and --cta are groups (number, lazy, search, guess,
contrast; follow, save, send, ask, site, bio); a group that is not one falls back to the series' own. The same post
renders with the same words every time.

Reads the public slide pages (/social/…) from production by default, or --base http://127.0.0.1:8000 for a local app,
and takes each picture with headless Chrome (--chrome, or $CHROME; the macOS path by default). Nothing is written to
production and nothing costs money. The pictures go to ~/promptlab-runs/social/<date>-<format>-<recipe>-<size>/, outside
the repo: they hold recipe content. --code is the post's code in the address on the last slide
(thelazychef.app/tiktok/3), so the Funnel page tells this post's visits from the others': take the next free code the
Funnel page gives. With a code the script ends with the address that logs the post in the Funnel page's post log, the
form filled in (with the series, number, hook, CTA, recipes, views and look of a series post); open it when the post
is up.
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
PLATFORM_OF_SIZE = {'ig': 'instagram', 'tt': 'tiktok'}  # the post log's platforms (services/funnel.PLATFORMS)
SERIES = ['airfryer', 'got', 'protein', 'dishes', 'guess', 'cuisine']  # services/social_series.SERIES
HOOKS = ['number', 'lazy', 'search', 'guess', 'contrast']
CTAS = ['follow', 'save', 'send', 'ask', 'site', 'bio']
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
    if fmt == 'series':
        path = '/social/post'
    elif fmt in ('pantry', 'week'):
        path = f'/social/{fmt}'
    else:
        path = f'/social/recipe/{recipe}/{fmt}'
    return f'{base.rstrip("/")}{path}?{urllib.parse.urlencode({k: v for k, v in args.items() if v})}'


def log_url(base, size, code, fmt, recipe, **variant):
    """The Funnel page's form for a new post, filled in for this one."""
    query = {'platform': PLATFORM_OF_SIZE[size], 'code': code, 'format': fmt, 'recipe': recipe, **variant}
    return f'{base.rstrip("/")}/admin/funnel/posts/new?{urllib.parse.urlencode({k: v for k, v in query.items() if v})}'


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('format', nargs='?', choices=['map', 'grid', 'pantry', 'week'],
                   help='the format; none with --series')
    p.add_argument('recipe', nargs='?', type=int, help='the recipe id (map and grid only)')
    p.add_argument('--series', choices=SERIES, help='a series post instead of a format (services/social_series.py)')
    p.add_argument('--n', type=int, help="the series post's number; the next in the post log when left out")
    p.add_argument('--hook', choices=HOOKS, help='the hook group for the first slide')
    p.add_argument('--cta', choices=CTAS, help='the CTA group for the last slide')
    p.add_argument('--ids', help='week and a series: the recipe ids, comma separated, instead of the ones the site picks')
    p.add_argument('--size', choices=sorted(SIZES), default='ig')
    p.add_argument('--code', help="the post's code in the address, e.g. 3 for thelazychef.app/tiktok/3")
    p.add_argument('--look', choices=['today', 'c', 'd', 'e', 'f'],
                   help="another look than the site's (routes/_shared.SITE_LOOK): one of the style trial's, or today's")
    p.add_argument('--base', default='https://thelazychef.app')
    p.add_argument('--chrome', default=os.environ.get('CHROME', CHROME))
    p.add_argument('--out', type=Path, default=Path.home() / 'promptlab-runs' / 'social')
    args = p.parse_args()
    if args.series:
        if args.format or args.recipe:
            p.error('--series takes no format; give the recipes with --ids')
        fmt = 'series'
    elif not args.format:
        p.error('give a format (map, grid, pantry, week) or --series')
    elif (args.format in ('pantry', 'week')) == (args.recipe is not None):
        p.error('give a recipe id for map and grid, and none for pantry and week')
    else:
        fmt = args.format

    query = {'size': args.size, 'code': args.code, 'look': args.look, 'ids': args.ids, 'series': args.series,
             'n': args.n, 'hook': args.hook, 'cta': args.cta}
    context = tls()
    headers = fetch(page_url(args.base, fmt, args.recipe, **query, slide=1), context)[0]
    count = int(headers['X-Slides'])
    variant = {}
    if args.series:
        # What the site chose, fixed for the rest of the run: the recipes, the number, the hook's and CTA's groups
        query.update(ids=headers['X-Recipes'], n=headers['X-N'])
        variant = {'series': args.series, 'n': headers['X-N'], 'hook_group': headers['X-Hook'],
                   'hook': headers['X-Hook-Text'], 'cta': headers['X-Cta'], 'recipes': headers['X-Recipes'],
                   'views': headers['X-Views'], 'look': headers['X-Look'], 'slides': count}
        print(f"{args.series} #{headers['X-N']}: recipes {headers['X-Recipes']}, hook {headers['X-Hook']} "
              f"\"{headers['X-Hook-Text']}\", cta {headers['X-Cta']}")
    caption = fetch(page_url(args.base, fmt, args.recipe, **query, caption=1), context)[1]

    name = '-'.join(str(x) for x in (datetime.date.today().isoformat(), args.series or args.format,
                                     args.series and f"n{query['n']}", args.recipe, args.size, args.code,
                                     args.look and f'look-{args.look}')
                    if x is not None)
    folder = args.out / name
    folder.mkdir(parents=True, exist_ok=True)
    width, height = SIZES[args.size]
    for n in range(1, count + 1):
        target = folder / f'{n:02d}.png'
        shoot(args.chrome, width, height, target, page_url(args.base, fmt, args.recipe, **query, slide=n))
        print(f'{target}')
    (folder / 'caption.txt').write_text(caption, encoding='utf-8')
    print(f'\n{count} slides and caption.txt in {folder}\n\n{caption}')
    if args.code:
        recipe = args.recipe or (variant.get('recipes') or '').split(',')[0]
        print(f'\nWhen it is up, log it: {log_url(args.base, args.size, args.code, fmt, recipe, **variant)}')


if __name__ == '__main__':
    sys.exit(main())
