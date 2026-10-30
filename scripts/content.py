"""Send content to The Lazy Chef through the content API (docs/CONTENT.md, "The content API"): packages become draft
versions that Pål previews and publishes in Admin -> Pages. Nothing here publishes. Free: no AI calls.

    python -m scripts.content pages                                  # every page and its versions
    python -m scripts.content get frying-pans --lang no [--live] [-o docs/content/frying-pans/frying-pans.no.json]
    python -m scripts.content push docs/content/knives/knives.en.json  # its images first, then the package
    python -m scripts.content images knives docs/content/knives/chef.svg docs/content/knives/paring.svg
    python -m scripts.content interactive board.html --title "Knife picker"

The key is CONTENT_API_KEY, else the macOS Keychain item "thelazychef-content-api" (made once with
`security add-generic-password -a "$USER" -s thelazychef-content-api -w`). LAZYCHEF_URL points it at another copy of
the app (http://127.0.0.1:8000); the default is https://thelazychef.app.
"""
import argparse
import json
import os
import re
import subprocess
import sys

import requests

KEYCHAIN = 'thelazychef-content-api'
IMAGE = re.compile(r'^[a-z0-9][a-z0-9_-]*\.(svg|png|jpg|jpeg|webp|gif)$')


def _key():
    key = os.environ.get('CONTENT_API_KEY')
    if not key and sys.platform == 'darwin':
        found = subprocess.run(['security', 'find-generic-password', '-s', KEYCHAIN, '-w'],
                               capture_output=True, text=True)
        key = found.stdout.strip()
    if not key:
        sys.exit(f'No key: set CONTENT_API_KEY or add the Keychain item "{KEYCHAIN}" (see the docstring).')
    return key


def _call(method, path, **kw):
    base = os.environ.get('LAZYCHEF_URL', 'https://thelazychef.app').rstrip('/')
    resp = requests.request(method, f'{base}/api/content{path}', headers={'Authorization': f'Bearer {_key()}'},
                            timeout=60, **kw)
    try:
        body = resp.json()
    except ValueError:
        sys.exit(f'{resp.status_code} from {path}: {resp.text[:300]}')
    if resp.status_code >= 400:
        errors = body.get('errors') or [body.get('error', resp.status_code)]
        sys.exit(f'{resp.status_code} from {path}:\n' + '\n'.join(f'  - {e}' for e in errors))
    return body


def _strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for v in value.values():
            yield from _strings(v)
    elif isinstance(value, list):
        for v in value:
            yield from _strings(v)


def upload_images(slug, paths):
    files = [('images', (os.path.basename(p), open(p, 'rb'))) for p in paths]
    try:
        body = _call('POST', f'/pages/{slug}/images', files=files)
    finally:
        for _, (_, f) in files:
            f.close()
    for name in body['saved']:
        print(f'  image {name}')
    for e in body['errors']:
        print(f'  ! {e}')


def push(path, images=True):
    """The package's images that lie next to it (named in the package, uploaded first), then the package."""
    with open(path, encoding='utf-8') as f:
        package = json.load(f)
    if images:
        folder = os.path.dirname(os.path.abspath(path))
        names = sorted({s for s in _strings(package) if IMAGE.match(s) and os.path.isfile(os.path.join(folder, s))})
        if names:
            upload_images(package['slug'], [os.path.join(folder, n) for n in names])
    body = _call('POST', '/packages', json=package)
    print(f'Draft: {body["slug"]} ({body["lang"]}) version {body["version"]}')
    print(f'  preview  {body["preview"]}')
    print(f'  publish  {body["admin"]}')


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    sub = parser.add_subparsers(dest='cmd', required=True)
    sub.add_parser('pages')
    get = sub.add_parser('get')
    get.add_argument('slug')
    get.add_argument('--lang', default='en')
    get.add_argument('--version', type=int)
    get.add_argument('--live', action='store_true', help='what visitors see now')
    get.add_argument('-o', '--out', help='write the package to this file')
    p = sub.add_parser('push')
    p.add_argument('package')
    p.add_argument('--no-images', action='store_true')
    im = sub.add_parser('images')
    im.add_argument('slug')
    im.add_argument('files', nargs='+')
    it = sub.add_parser('interactive')
    it.add_argument('file')
    it.add_argument('--title', required=True)
    args = parser.parse_args()

    if args.cmd == 'pages':
        for page in _call('GET', '/pages')['pages']:
            langs = ', '.join(f'{lang} v{vs[0]["version"]}' + (' (live)' if vs[0]['published'] else
                              f' (draft; live v{next((v["version"] for v in vs if v["published"]), "-")})')
                              for lang, vs in page['langs'].items())
            print(f'{page["slug"]:24} {page["kind"]:8} {langs}')
    elif args.cmd == 'get':
        params = {'lang': args.lang, 'version': args.version, 'live': 1 if args.live else None}
        body = _call('GET', f'/pages/{args.slug}', params={k: v for k, v in params.items() if v})
        text = json.dumps(body['package'], indent=2, ensure_ascii=False) + '\n'
        if args.out:
            with open(args.out, 'w', encoding='utf-8') as f:
                f.write(text)
            print(f'{args.slug} ({args.lang}) version {body["version"]} -> {args.out}')
        else:
            print(text, end='')
    elif args.cmd == 'push':
        push(args.package, images=not args.no_images)
    elif args.cmd == 'images':
        upload_images(args.slug, args.files)
    elif args.cmd == 'interactive':
        with open(args.file, encoding='utf-8') as f:
            body = _call('POST', '/interactives', json={'title': args.title, 'html': f.read()})
        print(json.dumps(body['block'], ensure_ascii=False))


if __name__ == '__main__':
    main()
