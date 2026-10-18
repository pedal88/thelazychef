"""Make ingredient symbols for the whole pantry, review them, and roll them out.

    python scripts/ingredient_symbols.py export                  # active ingredients from production (read only)
    python scripts/ingredient_symbols.py generate --input <csv>  # new run in ~/promptlab-runs/symbols-<time>
    python scripts/ingredient_symbols.py review --run <dir>      # review.html: reject the wrong ones, with a note
    python scripts/ingredient_symbols.py decide --run <dir> --decisions <decisions-....json>
    python scripts/ingredient_symbols.py generate --run <dir> --redo   # the rejected ones again, with their notes
    ... review, decide and redo until you are happy ...
    python scripts/ingredient_symbols.py promote --run <dir>

generate is resumable: run it again with --run and it does what is missing
or failed. decide records the review in the run's manifest, so each review
only shows the images you have not decided on yet. promote uploads the
approved images as 512 px WebP to gs://thelazychef-assets/pantry/symbols/<run>/
and writes one data migration that sets image_url. The migration keeps the
old URLs, so downgrade restores them. Rejected ones keep their image; their
review notes go into image_notes for later.

generate needs GOOGLE_API_KEY and costs about USD 0.04 per image. export and
promote need gcloud logged in.
"""
import argparse
import csv
import datetime
import html
import json
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv()

from promptlab.run import RUNS_DIR  # noqa: E402
from services.ingredient_symbols import symbol_prompt, web_image  # noqa: E402

PROJECT = 'thelazychefai-prod'
INSTANCE = 'lazy-chef-db-eu'
DATABASE = 'lazy-chef-db'
EXPORT_BUCKET = 'gs://thelazychef-ops-exports'
ASSET_BUCKET = 'thelazychef-assets'
VERSIONS = ROOT / 'migrations' / 'versions'
COLUMNS = ['id', 'food_id', 'name', 'main_category', 'sub_category', 'image_form', 'image_notes', 'image_url']


# --- export -----------------------------------------------------------------

def export(out: Path) -> Path:
    """Active ingredients from production via a Cloud SQL CSV export (no DB password)."""
    stamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
    remote = f'{EXPORT_BUCKET}/ingredients-{stamp}.csv'
    query = f"SELECT {', '.join(COLUMNS)} FROM ingredient WHERE status = 'active' ORDER BY id"
    subprocess.run(['gcloud', 'sql', 'export', 'csv', INSTANCE, remote, f'--project={PROJECT}',
                    f'--database={DATABASE}', f'--query={query}'], check=True)
    raw = out.with_suffix('.raw')
    subprocess.run(['gcloud', 'storage', 'cp', remote, str(raw), f'--project={PROJECT}'], check=True)
    subprocess.run(['gcloud', 'storage', 'rm', remote, f'--project={PROJECT}'], check=True)
    with open(raw, newline='', encoding='utf-8') as src, open(out, 'w', newline='', encoding='utf-8') as dst:
        writer = csv.writer(dst)
        writer.writerow(COLUMNS)
        writer.writerows(csv.reader(src))
    raw.unlink()
    return out


def read_ingredients(path: Path) -> list[dict]:
    """Rows from an export CSV. Empty and \\N (the Cloud SQL null) become None."""
    with open(path, newline='', encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
    for row in rows:
        for key, value in row.items():
            row[key] = None if value in ('', '\\N') else value
        row['id'] = int(row['id'])
    return rows


# --- the run ----------------------------------------------------------------
# manifest.json maps ingredient id to an entry:
#   name, food_id, categories, image_form   from the export
#   db_notes, live_url                      image_notes and image_url in production now
#   image_notes                             notes the prompt uses: db_notes plus review notes
#   version, image, thumb, prompt, meta, error
#   status                                  new (not reviewed), approved or rejected

def load_manifest(run: Path) -> dict:
    path = run / 'manifest.json'
    return json.loads(path.read_text()) if path.exists() else {}


def save_manifest(run: Path, manifest: dict) -> None:
    tmp = run / 'manifest.json.tmp'
    tmp.write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
    tmp.replace(run / 'manifest.json')


def join_notes(*parts) -> str | None:
    return ' '.join(p.strip() for p in parts if p and p.strip()) or None


def new_entry(row: dict) -> dict:
    return {
        'id': row['id'], 'food_id': row['food_id'], 'name': row['name'],
        'main_category': row.get('main_category'), 'sub_category': row.get('sub_category'),
        'image_form': row.get('image_form'), 'image_notes': row.get('image_notes'),
        'db_notes': row.get('image_notes'), 'live_url': row.get('image_url'),
        'version': 0, 'image': None, 'status': 'new',
    }


def generate(run: Path, ingredients: list[dict], only: set[int] | None = None, redo: bool = False,
             workers: int = 4, dry_run: bool = False, generate_one=None) -> dict:
    """Generate the images that are missing, failed, named in only, or rejected (redo)."""
    if generate_one is None:
        from services.ingredient_symbols import generate_symbol as generate_one

    (run / 'images').mkdir(parents=True, exist_ok=True)
    manifest = load_manifest(run)
    lock = threading.Lock()

    todo = []
    for row in ingredients:
        entry = manifest.get(str(row['id']))
        if only is not None:
            wanted = row['id'] in only
        elif redo:
            wanted = bool(entry) and entry['status'] == 'rejected'
        else:
            wanted = not entry or not entry.get('image')
        if wanted:
            todo.append(entry or new_entry(row))

    print(f"{len(todo)} to generate, about USD {len(todo) * 0.04:.0f} ({len(manifest)} already in the run)")
    if dry_run:
        for entry in todo[:3]:
            print(f"\n--- {entry['name']}\n{symbol_prompt(entry)}")
        return manifest

    def work(entry):
        entry = dict(entry)
        try:
            png, prompt, meta = generate_one(entry)
            version = entry['version'] + 1
            stem = f"images/{entry['id']}-v{version}"
            (run / f'{stem}.png').write_bytes(png)
            (run / f'{stem}.thumb.webp').write_bytes(web_image(png, 256))
            entry.update(version=version, image=f'{stem}.png', thumb=f'{stem}.thumb.webp', prompt=prompt,
                         meta=meta, error=None, status='new')
        except Exception as e:  # noqa: BLE001 - recorded, the run goes on
            entry.update(error=str(e)[:300], status='new')
        with lock:
            manifest[str(entry['id'])] = entry
            save_manifest(run, manifest)
            status = 'ERROR ' + entry['error'][:80] if entry.get('error') else 'ok'
            print(f"  {entry['id']} {entry['name']}: {status}", flush=True)

    with ThreadPoolExecutor(max_workers=workers) as pool:
        list(pool.map(work, todo))
    failed = sum(1 for e in manifest.values() if e.get('error'))
    if failed:
        print(f"{failed} failed. Run generate --run {run} again to retry them.")
    return manifest


# --- review -----------------------------------------------------------------

REVIEW = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Symbol review</title><style>
:root{{--bg:#fafaf9;--fg:#1c1917;--muted:#78716c;--line:#e7e5e4;--card:#fff;--no:#dc2626}}
@media (prefers-color-scheme:dark){{:root{{--bg:#1c1917;--fg:#f5f5f4;--muted:#a8a29e;--line:#44403c;--card:#292524}}}}
body{{margin:0;padding:0 16px 16px;background:var(--bg);color:var(--fg);font:14px/1.4 system-ui,sans-serif}}
header{{position:sticky;top:0;background:var(--bg);padding:10px 0;display:flex;gap:12px;flex-wrap:wrap;align-items:center;z-index:2;border-bottom:1px solid var(--line)}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:12px;margin-top:12px}}
.card{{background:var(--card);border:2px solid var(--line);border-radius:10px;padding:10px}}
.card.rejected{{border-color:var(--no)}} .pair{{display:flex;gap:6px}}
.pair figure{{margin:0;flex:1;text-align:center;font-size:11px;color:var(--muted)}}
.pair img{{width:100%;aspect-ratio:1;object-fit:contain;background:#fff;border-radius:6px}}
.empty{{aspect-ratio:1;display:flex;align-items:center;justify-content:center;border:1px dashed var(--line);border-radius:6px}}
h3{{font-size:14px;margin:6px 0 2px}} .cat,.hint{{color:var(--muted);font-size:12px}} .err{{color:var(--no);font-size:12px}}
button{{font:inherit;border:1px solid var(--line);background:var(--card);color:var(--fg);border-radius:6px;padding:3px 10px;cursor:pointer;margin-top:6px}}
textarea{{width:100%;box-sizing:border-box;margin-top:6px;font:inherit;display:none}} .rejected textarea{{display:block}}
</style></head><body>
<header><strong>{run}</strong><span id="count"></span>
<label><input type="checkbox" id="onlyRejected"> only rejected</label>
<button id="export">Export decisions</button></header>
<p class="hint">Everything starts approved. Reject the wrong ones and say what is wrong: the note goes into the
prompt when they are made again, and into image_notes. Then export and run decide.</p>
<div class="grid">{cards}</div>
<script>
const RUN = {run_json};
const decisions = {{}};
document.querySelectorAll('.card').forEach(c => decisions[c.dataset.id] = {{status: c.classList.contains('rejected') ? 'rejected' : 'approved', notes: ''}});
function paint() {{
  const all = Object.values(decisions), rejected = all.filter(d => d.status === 'rejected').length;
  document.getElementById('count').textContent = `${{all.length - rejected}} approved, ${{rejected}} rejected`;
  const only = document.getElementById('onlyRejected').checked;
  document.querySelectorAll('.card').forEach(c => c.style.display = only && decisions[c.dataset.id].status !== 'rejected' ? 'none' : '');
}}
document.addEventListener('click', e => {{
  const b = e.target.closest('[data-toggle]'); if (!b) return;
  const card = b.closest('.card'), d = decisions[card.dataset.id];
  d.status = d.status === 'approved' ? 'rejected' : 'approved';
  card.classList.toggle('rejected', d.status === 'rejected');
  b.textContent = d.status === 'approved' ? 'Reject' : 'Approve';
  if (d.status === 'rejected') card.querySelector('textarea').focus();
  paint();
}});
document.addEventListener('input', e => {{ if (e.target.matches('textarea')) decisions[e.target.closest('.card').dataset.id].notes = e.target.value; }});
document.getElementById('onlyRejected').onchange = paint;
document.getElementById('export').onclick = () => {{
  const stamp = new Date().toISOString().slice(0, 19).replace(/[-:T]/g, '');
  const blob = new Blob([JSON.stringify({{run: RUN, decisions}}, null, 2)], {{type: 'application/json'}});
  Object.assign(document.createElement('a'), {{href: URL.createObjectURL(blob), download: `decisions-${{RUN}}-${{stamp}}.json`}}).click();
}};
paint();
</script></body></html>"""


def review(run: Path) -> Path:
    """review.html with the images not decided on yet, today's image next to the new one."""
    esc = html.escape
    pending = [e for e in load_manifest(run).values() if e['status'] == 'new']
    cards = []
    for e in sorted(pending, key=lambda e: (e.get('main_category') or '', e.get('sub_category') or '', e['name'])):
        failed = not e.get('image') or e.get('error')
        old = f'<img loading="lazy" src="{esc(e["live_url"])}" alt="">' if e.get('live_url') else '<div class="empty">none</div>'
        new = (f'<div class="empty err">{esc(e.get("error") or "not generated")}</div>' if failed
               else f'<img loading="lazy" src="{esc(e["thumb"])}" alt="">')
        notes = f'<div class="cat">notes: {esc(e["image_notes"])}</div>' if e.get('image_notes') else ''
        cards.append(
            f'<div class="card{" rejected" if failed else ""}" data-id="{e["id"]}">'
            f'<div class="pair"><figure>{old}<figcaption>now</figcaption></figure>'
            f'<figure>{new}<figcaption>new (v{e["version"]})</figcaption></figure></div>'
            f'<h3>{esc(e["name"])}</h3><div class="cat">{esc(e.get("main_category") or "")} / '
            f'{esc(e.get("sub_category") or "")}</div>{notes}'
            f'<button data-toggle>{"Approve" if failed else "Reject"}</button>'
            f'<textarea rows="2" placeholder="What is wrong?"></textarea></div>')
    path = run / 'review.html'
    path.write_text(REVIEW.format(run=esc(run.name), run_json=json.dumps(run.name), cards=''.join(cards)))
    print(f"{len(cards)} to review")
    return path


def decide(run: Path, decisions_file: Path) -> dict:
    """Record an exported review in the manifest. Review notes are added to image_notes."""
    data = json.loads(decisions_file.read_text())
    if data.get('run') != run.name:
        raise SystemExit(f"{decisions_file.name} is from run {data.get('run')}, not {run.name}")
    manifest = load_manifest(run)
    counts = {'approved': 0, 'rejected': 0, 'skipped': 0}
    for key, d in data['decisions'].items():
        entry = manifest.get(str(key))
        if not entry or entry['status'] != 'new':
            counts['skipped'] += 1  # decided earlier, or made again after this review
            continue
        ok = d.get('status') == 'approved' and entry.get('image') and not entry.get('error')
        status = 'approved' if ok else 'rejected'
        entry['status'] = status
        if status == 'rejected':
            entry['image_notes'] = join_notes(entry.get('image_notes'), d.get('notes'))
        counts[status] += 1
    save_manifest(run, manifest)
    left = sum(1 for e in manifest.values() if e['status'] == 'new')
    print(f"{counts['approved']} approved, {counts['rejected']} rejected, {counts['skipped']} skipped; {left} not reviewed")
    return counts


# --- promote ----------------------------------------------------------------

MIGRATION = '''"""ingredient symbols {run}

New ingredient symbols from run {run}, approved in review: {approved}
ingredients get the new image_url and image_prompt, and image_notes with
any review notes. {rejected} rejected ones keep their image and get their
review notes in image_notes. The images are in
gs://{bucket}/pantry/symbols/{run}/.

Downgrade restores the old image_url and image_notes. The old image_prompt
is not kept: it belonged to the retired image pipeline.

Made by scripts/ingredient_symbols.py promote.

Revision ID: {rev}
Revises: {down}
Create Date: {date}

"""
from alembic import op
import sqlalchemy as sa


revision = '{rev}'
down_revision = '{down}'
branch_labels = None
depends_on = None

# id: (food_id, new_url, new_prompt, new_notes, old_url, old_notes)
APPROVED = {approved_map}

# id: (food_id, new_notes, old_notes)
NOTES = {notes_map}


def upgrade():
    conn = op.get_bind()
    for i, (food_id, url, prompt, notes, _old_url, _old_notes) in APPROVED.items():
        conn.execute(sa.text(
            "UPDATE ingredient SET image_url = :u, image_prompt = :p, image_notes = :n, has_transparent_image = false "
            "WHERE id = :i AND food_id = :f"), {{'u': url, 'p': prompt, 'n': notes, 'i': i, 'f': food_id}})
    for i, (food_id, notes, _old_notes) in NOTES.items():
        conn.execute(sa.text("UPDATE ingredient SET image_notes = :n WHERE id = :i AND food_id = :f"),
                     {{'n': notes, 'i': i, 'f': food_id}})


def downgrade():
    conn = op.get_bind()
    for i, (food_id, _url, _prompt, _notes, old_url, old_notes) in APPROVED.items():
        conn.execute(sa.text(
            "UPDATE ingredient SET image_url = :u, image_prompt = NULL, image_notes = :n WHERE id = :i AND food_id = :f"),
            {{'u': old_url, 'n': old_notes, 'i': i, 'f': food_id}})
    for i, (food_id, _notes, old_notes) in NOTES.items():
        conn.execute(sa.text("UPDATE ingredient SET image_notes = :n WHERE id = :i AND food_id = :f"),
                     {{'n': old_notes, 'i': i, 'f': food_id}})
'''


def current_head() -> str:
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    config = Config()
    config.set_main_option('script_location', str(ROOT / 'migrations'))
    return ScriptDirectory.from_config(config).get_current_head()


def promote(run: Path, upload: bool = True, versions: Path = VERSIONS, down: str | None = None) -> Path:
    """Upload the approved images and write the data migration. Returns its path."""
    import pprint
    import uuid

    slug = run.name.replace('-', '_')
    if any(versions.glob(f'*_ingredient_symbols_{slug}.py')):
        raise SystemExit(f'A migration for {run.name} exists already. Make a new run for more changes.')
    manifest = load_manifest(run)
    pending = [e['name'] for e in manifest.values() if e['status'] == 'new']
    if pending:
        raise SystemExit(f"{len(pending)} not reviewed yet (e.g. {', '.join(pending[:5])}). Review and decide first.")

    web = run / 'web'
    web.mkdir(exist_ok=True)
    approved, notes = {}, {}
    for e in sorted(manifest.values(), key=lambda e: e['id']):
        if e['status'] == 'approved':
            name = f"{e['food_id']}-v{e['version']}.webp"
            (web / name).write_bytes(web_image((run / e['image']).read_bytes()))
            url = f"https://storage.googleapis.com/{ASSET_BUCKET}/pantry/symbols/{run.name}/{name}"
            approved[e['id']] = (e['food_id'], url, e['prompt'], e.get('image_notes'), e.get('live_url'), e.get('db_notes'))
        elif e.get('image_notes') != e.get('db_notes'):
            notes[e['id']] = (e['food_id'], e.get('image_notes'), e.get('db_notes'))
    if not approved and not notes:
        raise SystemExit('Nothing to promote')

    if upload and approved:
        subprocess.run(['gcloud', 'storage', 'cp', '--recursive', f'{web}/*',
                        f'gs://{ASSET_BUCKET}/pantry/symbols/{run.name}/', f'--project={PROJECT}',
                        '--cache-control=public, max-age=31536000'], check=True)

    rev = uuid.uuid4().hex[:12]
    path = versions / f'{rev}_ingredient_symbols_{slug}.py'
    path.write_text(MIGRATION.format(
        run=run.name, approved=len(approved), rejected=len(manifest) - len(approved), bucket=ASSET_BUCKET,
        rev=rev, down=down or current_head(), date=datetime.date.today().isoformat(),
        approved_map=pprint.pformat(approved, width=120), notes_map=pprint.pformat(notes, width=120)))
    return path


# --- command line -----------------------------------------------------------

def main(argv=None):
    parser = argparse.ArgumentParser(prog='python scripts/ingredient_symbols.py')
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('export', help='active ingredients from production to a CSV')
    p.add_argument('--out', type=Path, default=RUNS_DIR / f"ingredients-{datetime.date.today()}.csv")
    p = sub.add_parser('generate', help='make images (new run with --input, continue with --run)')
    p.add_argument('--input', type=Path, help='CSV from export, for a new run')
    p.add_argument('--run', type=Path, help='continue this run')
    p.add_argument('--only', help='comma separated ingredient ids to make again')
    p.add_argument('--redo', action='store_true', help='make the rejected ones again, with their notes')
    p.add_argument('--limit', type=int, help='only the first N ingredients (for a test run)')
    p.add_argument('--workers', type=int, default=4)
    p.add_argument('--dry-run', action='store_true', help='count and show prompts, no images')
    p = sub.add_parser('review', help='write review.html')
    p.add_argument('--run', type=Path, required=True)
    p = sub.add_parser('decide', help='record an exported review')
    p.add_argument('--run', type=Path, required=True)
    p.add_argument('--decisions', type=Path, required=True)
    p = sub.add_parser('promote', help='upload approved images and write the migration')
    p.add_argument('--run', type=Path, required=True)
    p.add_argument('--no-upload', action='store_true')
    args = parser.parse_args(argv)

    if args.command == 'export':
        args.out.parent.mkdir(parents=True, exist_ok=True)
        print(export(args.out))
    elif args.command == 'review':
        print(review(args.run))
    elif args.command == 'decide':
        decide(args.run, args.decisions)
    elif args.command == 'promote':
        path = promote(args.run, upload=not args.no_upload)
        print(f"Migration written: {path.relative_to(ROOT)}. Commit it on a branch and open a PR.")
    else:
        if not args.input and not args.run:
            raise SystemExit('Give --input (a CSV from export) for a new run, or --run to continue one')
        run = args.run or RUNS_DIR / f"symbols-{datetime.datetime.now():%Y%m%d-%H%M}"
        run.mkdir(parents=True, exist_ok=True)
        if args.input:
            (run / 'ingredients.csv').write_bytes(args.input.read_bytes())
        ingredients = read_ingredients(run / 'ingredients.csv')[:args.limit]
        only = {int(i) for i in args.only.split(',')} if args.only else None
        generate(run, ingredients, only=only, redo=args.redo, workers=args.workers, dry_run=args.dry_run)
        if not args.dry_run:
            print(review(run))


if __name__ == '__main__':
    main()
