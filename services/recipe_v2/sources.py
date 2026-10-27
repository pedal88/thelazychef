"""Read a recipe from a link, for v2 generation (docs/RECIPE_MODEL_V2.md, section 7).

Most recipe sites carry the recipe as schema.org JSON-LD: the ingredients and
steps without ads and life stories. That is read first. Otherwise the page
text is used, kept long enough to reach the recipe card: the old scraper cut
pages at 20 000 characters, which drops the recipe on long blogs (phase 0b).

Some sites block scripts (Cloudflare and similar). That is not worth retrying;
the user is asked to paste the text instead.

A video link (TikTok, Instagram, YouTube) is downloaded and watched by Gemini, which writes down the recipe it shows
(data/prompts/recipe_v2/video_text.jinja2); Claude cannot watch video. The text then goes through round 1 like a
pasted recipe.
"""
import json
import re
from html import unescape

PAGE_TEXT_MAX = 60000
VIDEO_HOSTS = re.compile(r'(^|\.)(tiktok\.com|tiktokv\.com|instagram\.com|youtube\.com|youtu\.be)$', re.IGNORECASE)
HEADERS = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
                         '(KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36',
           'Accept': 'text/html,application/xhtml+xml', 'Accept-Language': 'en-US,en;q=0.9,nb;q=0.8'}


class SourceError(Exception):
    """The link cannot be read. The message is safe to show the user."""


def is_link(text):
    return bool(re.fullmatch(r'https?://\S+', (text or '').strip()))


def is_video(url):
    from urllib.parse import urlparse

    return bool(VIDEO_HOSTS.search(urlparse(url).hostname or ''))


def _public(url):
    """Only http(s) to public addresses: the server must not be steered to internal ones (metadata server, localhost)."""
    import ipaddress
    import socket
    from urllib.parse import urlparse

    parts = urlparse(url)
    if parts.scheme not in ('http', 'https') or not parts.hostname:
        return False
    try:
        infos = socket.getaddrinfo(parts.hostname, None)
    except OSError:
        return False
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
            return False
    return True


def fetch_recipe_text(url, get=None, public=None):
    """The recipe on the page as text for round 1. Returns (text, how): how is 'jsonld' or 'page'."""
    import requests
    from bs4 import BeautifulSoup

    if is_video(url):
        raise SourceError('This is a video link: it is read as a video, not as a page.')
    get, public = get or requests.get, public or _public
    try:
        for _ in range(5):  # follow redirects one by one, so each target is checked
            if not public(url):
                raise SourceError('This link cannot be read. Paste the recipe text instead.')
            resp = get(url, headers=HEADERS, timeout=15, allow_redirects=False)
            if resp.status_code in (301, 302, 303, 307, 308) and resp.headers.get('Location'):
                from urllib.parse import urljoin
                url = urljoin(url, resp.headers['Location'])
                continue
            break
        else:
            raise SourceError('The link redirects too many times. Paste the recipe text instead.')
    except requests.RequestException:
        raise SourceError('Could not reach the page. Check the link, or paste the recipe text instead.')
    if resp.status_code in (401, 403, 429):
        raise SourceError('This site blocks automatic reading. Paste the recipe text instead.')
    if resp.status_code >= 400:
        raise SourceError(f'The page answered with an error ({resp.status_code}). Check the link, or paste the recipe text.')

    soup = BeautifulSoup(resp.content, 'html.parser')
    for script in soup.find_all('script', type='application/ld+json'):
        try:
            found = next(jsonld_recipes(json.loads(script.string or 'null')), None)
        except ValueError:
            continue
        if found and found.get('recipeIngredient'):
            return jsonld_text(found), 'jsonld'
    for tag in soup(['script', 'style', 'nav', 'footer', 'header']):
        tag.decompose()
    text = soup.get_text(separator=' ', strip=True)[:PAGE_TEXT_MAX]
    if len(text) < 200:
        raise SourceError('Found no recipe on the page. Paste the recipe text instead.')
    return text, 'page'


def jsonld_recipes(node):
    """Every schema.org Recipe in a JSON-LD block, also inside @graph and mainEntity."""
    if isinstance(node, list):
        for n in node:
            yield from jsonld_recipes(n)
    elif isinstance(node, dict):
        types = node.get('@type') if isinstance(node.get('@type'), list) else [node.get('@type')]
        if 'Recipe' in types:
            yield node
        for k in ('@graph', 'mainEntity'):
            if k in node:
                yield from jsonld_recipes(node[k])


def _clean(x):
    return unescape(re.sub(r'<[^>]+>', ' ', str(x))).strip()


def jsonld_text(r):
    """A schema.org Recipe as plain recipe text for round 1."""
    yields = r.get('recipeYield')
    yields = ', '.join(map(str, yields)) if isinstance(yields, list) else yields
    lines = [_clean(r.get('name', '')), f'Servings: {_clean(yields)}' if yields else '', '', 'Ingredients:']
    lines += [f'- {_clean(i)}' for i in r.get('recipeIngredient', [])]
    lines += ['', 'Method:']

    def steps(items, n=0):
        out = []
        for it in items if isinstance(items, list) else [items]:
            if isinstance(it, str):
                n += 1
                out.append(f'{n}. {_clean(it)}')
            elif it.get('@type') == 'HowToSection':
                out.append(_clean(it.get('name', '')) + ':')
                sub, n = steps(it.get('itemListElement', []), n)
                out += sub
            else:
                n += 1
                out.append(f"{n}. {_clean(it.get('text') or it.get('name', ''))}")
        return out, n

    lines += steps(r.get('recipeInstructions', []))[0]
    if r.get('description'):
        lines += ['', 'Note: ' + _clean(r['description'])]
    return '\n'.join(lines)


VIDEO_WAIT = 180  # seconds Gemini may take to process an uploaded video


def fetch_video_text(url, download=None, watch=None):
    """The recipe a cooking video shows, as text for round 1. download and watch can stand in for yt-dlp and Gemini in
    tests: download(url) -> {'video_path', 'caption', 'thumbnail_path'}; watch(path, caption) -> text."""
    from services.social_media_service import SocialMediaExtractor

    try:
        video = (download or SocialMediaExtractor.download_video)(url)
    except ValueError:  # private, removed or not a video: trying again does not help
        raise SourceError('Could not get the video. Check that it is public, or paste the recipe text instead.')
    try:
        text = (watch or _watch)(video['video_path'], video.get('caption') or '')
    finally:
        SocialMediaExtractor.cleanup(video['video_path'], video.get('thumbnail_path'))
    if not (text or '').strip():
        raise SourceError('No recipe could be read from the video. Paste the recipe text instead.')
    return text


def _watch(path, caption):
    """Gemini watches the video and writes down the recipe, with the caption as help."""
    import os
    import time

    from google.genai import types
    from jinja2 import Environment, FileSystemLoader
    from services.ai_models import GEMINI_TEXT, gemini_client

    client = gemini_client()
    ref = client.files.upload(file=path)
    waited = 0
    while ref.state and ref.state.name == 'PROCESSING':
        if waited >= VIDEO_WAIT:
            raise TimeoutError('Gemini did not finish processing the video')
        time.sleep(3)
        waited += 3
        ref = client.files.get(name=ref.name)
    if ref.state and ref.state.name == 'FAILED':
        raise SourceError('The video could not be read. Paste the recipe text instead.')
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    prompt = Environment(loader=FileSystemLoader(os.path.join(root, 'data', 'prompts'))).get_template(
        'recipe_v2/video_text.jinja2').render(caption=caption)
    resp = client.models.generate_content(model=GEMINI_TEXT, contents=[types.Part.from_uri(file_uri=ref.uri, mime_type=ref.mime_type), prompt])
    return resp.text
