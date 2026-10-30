"""The content API: what Claude Code uses to send content packages, images and interactives to the app as drafts,
instead of Pål pasting them in Admin -> Pages (docs/CONTENT.md, "The content API"). It needs the key in
CONTENT_API_KEY as a bearer token; without that variable it answers 401 to everything.

Nothing here publishes: a package becomes a draft version that Pål previews and publishes in Admin -> Pages."""
import hmac
import json
import os
import uuid
from functools import wraps

from flask import Blueprint, Response, jsonify, request

from database.models import Page, PageEmbed, db
from routes._shared import get_storage, public_url
from services.content import assets
from services.content.blocks import page_url
from services.content.pages import DEFAULT_LANG, LANGS, SLUG, ContentError, find_page, package_of, save_version

content_api_bp = Blueprint('content_api', __name__, url_prefix='/api/content')
EMBED_MAX = 2 * 1024 * 1024  # bytes of HTML, as in Admin -> Pages


def key_required(view):
    """The request carries CONTENT_API_KEY as "Authorization: Bearer <key>"."""
    @wraps(view)
    def decorated_function(*args, **kwargs):
        key = os.environ.get('CONTENT_API_KEY', '')
        sent = request.headers.get('Authorization', '')
        if not key or not sent.startswith('Bearer ') or not hmac.compare_digest(sent[7:].encode(), key.encode()):
            return jsonify({'error': 'unauthorized'}), 401
        return view(*args, **kwargs)
    return decorated_function


def _version(text):
    return {'version': text.version, 'published': text.published_at is not None, 'note': text.note,
            'created_at': text.created_at.isoformat(timespec='seconds')}


def _links(text):
    """Where Pål previews and publishes the version (both need his admin login)."""
    return {'preview': public_url('content.admin_preview', text_id=text.id),
            'admin': public_url('content.admin_page', page_id=text.page_id, lang=text.lang)}


@content_api_bp.route('/pages')
@key_required
def pages():
    """Every page with its versions per language."""
    found = db.session.execute(db.select(Page).order_by(Page.slug)).scalars().all()
    return jsonify({'pages': [{'slug': p.slug, 'kind': p.kind, 'url': page_url(p), 'langs': {
        code: [_version(t) for t in sorted(p.texts, key=lambda t: -t.version) if t.lang == code]
        for code in LANGS if any(t.lang == code for t in p.texts)}} for p in found]})


@content_api_bp.route('/pages/<slug>')
@key_required
def page(slug):
    """One version of a page as a package, to change or translate: ?lang= (en), ?version= (the newest), or
    ?live=1 for what visitors see now. Also the page's images."""
    found = find_page(slug)
    lang = request.args.get('lang', DEFAULT_LANG)
    texts = sorted((t for t in found.texts if t.lang == lang), key=lambda t: -t.version) if found else []
    if request.args.get('live'):
        texts = [t for t in texts if t.published_at]
    if request.args.get('version', type=int):
        texts = [t for t in texts if t.version == request.args.get('version', type=int)]
    if not texts:
        return jsonify({'error': f'no such version of "{slug}" ({lang})'}), 404
    body = {'package': package_of(texts[0]), **_version(texts[0]), **_links(texts[0]),
            'images': {a.name: a.url for a in assets.of_page(slug)}}
    # In the package's own key order (jsonify sorts), so a package saved to docs/content/ diffs cleanly
    return Response(json.dumps(body, ensure_ascii=False), mimetype='application/json')


@content_api_bp.route('/packages', methods=['POST'])
@key_required
def import_package():
    """A content package (the JSON body) -> a new draft version, as Admin -> Pages -> Import."""
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({'errors': ['the body must be a content package as JSON']}), 400
    try:
        text = save_version(data)
    except ContentError as e:
        db.session.rollback()
        return jsonify({'errors': e.errors}), 400
    db.session.commit()
    return jsonify({'slug': text.page.slug, 'lang': text.lang, **_version(text), **_links(text)}), 201


@content_api_bp.route('/pages/<slug>/images', methods=['POST'])
@key_required
def images(slug):
    """Images for a page by its slug (the page need not exist yet), as multipart "images"; each keeps its file name."""
    files = [f for f in request.files.getlist('images') if f and f.filename]
    if not SLUG.match(slug) or not files:
        return jsonify({'errors': ['give a page slug and one or more files as "images"']}), 400
    saved, errors = {}, []
    for f in files:
        try:
            saved[f.filename.lower()] = assets.save(slug, f.filename, f.read(), get_storage()).url
        except ValueError as e:
            errors.append(str(e))
    db.session.commit()
    return jsonify({'saved': saved, 'errors': errors}), 400 if errors and not saved else 200


@content_api_bp.route('/interactives', methods=['POST'])
@key_required
def interactive():
    """A self-contained HTML page for an "interactive" block: {"title", "html"} -> its id and the block to use."""
    data = request.get_json(silent=True) or {}
    title, html = str(data.get('title') or '').strip(), data.get('html')
    if not title or not isinstance(html, str) or not html.strip():
        return jsonify({'errors': ['an interactive needs a title and its html']}), 400
    if len(html.encode('utf-8')) > EMBED_MAX:
        return jsonify({'errors': ['the HTML is larger than 2 MB; put images in the page\'s images']}), 400
    found = PageEmbed(id=uuid.uuid4().hex, title=title[:200], html=html)
    db.session.add(found)
    db.session.commit()
    return jsonify({'id': found.id, 'block': {'kind': 'interactive',
                                              'settings': {'embed': found.id, 'title': found.title}}}), 201
