"""The images of pages (docs/CONTENT.md, Images). A package names an image by file name ("cast-iron.svg"); it is
uploaded in Admin -> Pages under the page's slug and stored in the bucket at content/<slug>/<name>-<hash>.<ext>,
so a new upload of the same name gets a new address and is never served stale from a cache. A full address
(https://...) or a path on the site (/static/...) is used as it is."""
import hashlib
import re

from database.models import ContentAsset, db

NAME = re.compile(r'^[a-z0-9][a-z0-9_-]*\.(svg|png|jpg|jpeg|webp|gif)$')
MAX_BYTES = 5 * 1024 * 1024


def is_address(ref):
    return ref.startswith(('https://', 'http://', '/'))


def find(slug, name):
    return db.session.execute(db.select(ContentAsset).where(ContentAsset.slug == slug, ContentAsset.name == name)).scalar_one_or_none()


def resolve(slug, ref):
    """The address of an image named in a page, or None when it is not uploaded (yet)."""
    if not ref:
        return None
    if is_address(ref):
        return ref
    found = find(slug, ref)
    return found.url if found else None


def check(slug, ref, label, errors):
    """Adds to errors when ref is neither an address nor an image uploaded for the page."""
    if ref is None or ref == '':
        return
    if not isinstance(ref, str):
        errors.append(f'{label} must be a file name or an address')
    elif not is_address(ref) and not find(slug, ref):
        errors.append(f'{label}: no image "{ref}" uploaded for "{slug}" (Admin -> Pages -> Images)')


def save(slug, name, data, storage):
    """Stores an uploaded image for the page slug under name. Returns the ContentAsset; the caller commits."""
    name = name.lower()
    if not NAME.match(name):
        raise ValueError(f'"{name}": a file name in lower case letters, digits, "-" and "_", ending .svg, .png, .jpg, .webp or .gif')
    if len(data) > MAX_BYTES:
        raise ValueError(f'"{name}" is larger than 5 MB')
    stem, ext = name.rsplit('.', 1)
    url = storage.save(data, f'{stem}-{hashlib.sha256(data).hexdigest()[:8]}.{ext}', f'content/{slug}')
    found = find(slug, name)
    if found:
        found.url = url
    else:
        found = ContentAsset(slug=slug, name=name, url=url)
        db.session.add(found)
    return found


def of_page(slug):
    return db.session.execute(db.select(ContentAsset).where(ContentAsset.slug == slug).order_by(ContentAsset.name)).scalars().all()
