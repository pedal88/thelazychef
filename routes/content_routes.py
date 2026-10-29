"""Content: the home page and pages made of blocks (services/content, docs/CONTENT.md), the embeds for the
"interactive" block, and Admin -> Pages, where Claude's content packages are imported, previewed and published."""
import json
import uuid

from flask import Blueprint, abort, flash, make_response, redirect, render_template, request, url_for
from flask_login import current_user

from database.models import Page, PageEmbed, PageText, db
from services.content.blocks import KINDS, page_url
from services.content.pages import (DEFAULT_LANG, HOME, LANGS, ContentError, default_home, find_page, latest_text,
                                    live_text, package_of, publish, render_blocks, save_version, unpublish)
from utils.decorators import admin_required

content_bp = Blueprint('content', __name__)
EMBED_MAX = 2 * 1024 * 1024  # bytes of HTML
# Tells the page around it how tall the embed is (static/js/content.js sizes the frame)
RESIZE = ('<script>(function(){var id=%s;function h(){parent.postMessage({lazyEmbed:id,'
          'height:Math.ceil(document.documentElement.scrollHeight)},"*")}addEventListener("load",h);'
          'if(window.ResizeObserver)new ResizeObserver(h).observe(document.documentElement);h()})();</script>')


def _lang():
    lang = request.args.get('lang', DEFAULT_LANG)
    return lang if lang in LANGS else DEFAULT_LANG


def _user():
    return current_user if current_user.is_authenticated else None


def _render(page, text, lang, preview=None):
    return render_template('page.html', page=page, text=text, lang=lang, preview=preview,
                           blocks=render_blocks(text, _user(), lang))


@content_bp.route('/')
def home():
    """The home page when it is published; until then Discover, as before."""
    page, lang = find_page(HOME), _lang()
    text = page and live_text(page, lang)
    if not text:
        return render_template('landing.html')
    return _render(page, text, lang)


@content_bp.route('/guides/<slug>')
def page(slug):
    found, lang = find_page(slug), _lang()
    text = found and found.kind != 'home' and live_text(found, lang)
    if not text:
        abort(404)
    return _render(found, text, lang)


@content_bp.route('/content/interactive/<embed_id>')
def embed(embed_id):
    """An interactive's HTML, sandboxed: its own origin, no cookies, no access to the app, only shown in a frame on
    the app's own pages."""
    found = db.session.get(PageEmbed, embed_id) or abort(404)
    html = found.html + RESIZE % json.dumps(found.id)
    resp = make_response(html)
    resp.headers['Content-Type'] = 'text/html; charset=utf-8'
    resp.headers['Content-Security-Policy'] = ('sandbox allow-scripts allow-popups allow-popups-to-escape-sandbox; '
                                               "frame-ancestors 'self'")
    resp.headers['X-Content-Type-Options'] = 'nosniff'
    resp.headers['Referrer-Policy'] = 'no-referrer'
    return resp


# --- Admin -> Pages -----------------------------------------------------------------------------------------------

@content_bp.route('/admin/pages')
@admin_required
def admin_pages():
    pages = db.session.execute(db.select(Page).order_by(Page.kind != 'home', Page.slug)).scalars().all()
    rows = [{'page': p, 'url': page_url(p), 'langs': [
        {'lang': code, 'latest': latest_text(p, code), 'live': next((t for t in sorted(p.texts, key=lambda t: -t.version)
                                                                    if t.lang == code and t.published_at), None)}
        for code in LANGS if latest_text(p, code)]} for p in pages]
    embeds = db.session.execute(db.select(PageEmbed.id, PageEmbed.title, PageEmbed.created_at)
                                .order_by(PageEmbed.created_at.desc())).all()
    return render_template('admin/pages.html', rows=rows, embeds=embeds, has_home=find_page(HOME) is not None,
                           kinds=KINDS)


def _save(data, back):
    try:
        text = save_version(data)
    except ContentError as e:
        db.session.rollback()
        for msg in e.errors:
            flash(msg, 'error')
        return back
    db.session.commit()
    flash(f'Saved version {text.version} ({LANGS[text.lang]}) of "{text.page.slug}". Preview it, then publish.', 'success')
    return redirect(url_for('content.admin_page', page_id=text.page_id, lang=text.lang))


@content_bp.route('/admin/pages/import', methods=['POST'])
@admin_required
def admin_import():
    """A content package (JSON) from Claude -> a new draft version."""
    try:
        data = json.loads(request.form.get('package', ''))
    except ValueError as e:
        flash(f'That is not JSON: {e}', 'error')
        return redirect(url_for('content.admin_pages'))
    return _save(data, redirect(url_for('content.admin_pages')))


@content_bp.route('/admin/pages/home', methods=['POST'])
@admin_required
def admin_make_home():
    """The first home page, as a draft to preview and publish."""
    if find_page(HOME):
        return redirect(url_for('content.admin_page', page_id=find_page(HOME).id))
    return _save(default_home(), redirect(url_for('content.admin_pages')))


@content_bp.route('/admin/pages/<int:page_id>')
@admin_required
def admin_page(page_id):
    found = db.session.get(Page, page_id) or abort(404)
    lang = _lang()
    texts = sorted((t for t in found.texts if t.lang == lang), key=lambda t: -t.version)
    latest = texts[0] if texts else None
    package = json.dumps(package_of(latest), indent=2, ensure_ascii=False) if latest else ''
    return render_template('admin/page_edit.html', page=found, lang=lang, langs=LANGS, texts=texts, latest=latest,
                           package=package, url=page_url(found))


@content_bp.route('/admin/pages/<int:page_id>/save', methods=['POST'])
@admin_required
def admin_save(page_id):
    """The edited package from the page's form -> a new version (of the same page)."""
    found = db.session.get(Page, page_id) or abort(404)
    back = redirect(url_for('content.admin_page', page_id=page_id))
    try:
        data = json.loads(request.form.get('package', ''))
    except ValueError as e:
        flash(f'That is not JSON: {e}', 'error')
        return back
    if not isinstance(data, dict) or data.get('slug') != found.slug:
        flash(f'The slug must stay "{found.slug}"; import a package to make another page.', 'error')
        return back
    return _save(data, back)


@content_bp.route('/admin/pages/text/<int:text_id>/preview')
@admin_required
def admin_preview(text_id):
    text = db.session.get(PageText, text_id) or abort(404)
    return _render(text.page, text, text.lang, preview=text)


@content_bp.route('/admin/pages/text/<int:text_id>/publish', methods=['POST'])
@admin_required
def admin_publish(text_id):
    text = db.session.get(PageText, text_id) or abort(404)
    shown = publish(text)
    db.session.commit()
    flash(f'Version {shown.version} is live.', 'success')
    return redirect(url_for('content.admin_page', page_id=shown.page_id, lang=shown.lang))


@content_bp.route('/admin/pages/<int:page_id>/unpublish', methods=['POST'])
@admin_required
def admin_unpublish(page_id):
    found = db.session.get(Page, page_id) or abort(404)
    lang = request.form.get('lang', DEFAULT_LANG)
    unpublish(found, lang)
    db.session.commit()
    flash(f'"{found.slug}" ({LANGS.get(lang, lang)}) is no longer shown to visitors.', 'success')
    return redirect(url_for('content.admin_page', page_id=page_id, lang=lang))


@content_bp.route('/admin/embeds', methods=['POST'])
@admin_required
def admin_embed_upload():
    """A self-contained HTML file (or pasted HTML) for an "interactive" block."""
    title = request.form.get('title', '').strip()
    upload = request.files.get('file')
    html = upload.read().decode('utf-8', errors='replace') if upload and upload.filename else request.form.get('html', '')
    if not title or not html.strip():
        flash('An interactive needs a title and its HTML.', 'error')
    elif len(html.encode('utf-8')) > EMBED_MAX:
        flash('The HTML is larger than 2 MB. Put images in the asset store and link to them.', 'error')
    else:
        found = PageEmbed(id=uuid.uuid4().hex, title=title[:200], html=html)
        db.session.add(found)
        db.session.commit()
        flash(f'Uploaded "{found.title}". Use it with {{"kind": "interactive", "settings": {{"embed": "{found.id}", '
              f'"title": "{found.title}"}}}}', 'success')
    return redirect(url_for('content.admin_pages'))
