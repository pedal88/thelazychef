"""Review the pantry against the core definition (RECIPE_MODEL_V2.md, "Kjerne og lang hale").

    python scripts/ingredient_symbols.py export                   # CSV of active ingredients from production
    python scripts/pantry_review.py classify --input <csv>        # new run in ~/promptlab-runs/pantry-<time>
    python scripts/pantry_review.py gaps --run <dir>              # missing core ingredients and aliases
    python scripts/pantry_review.py review --run <dir>            # writes review.html
    python scripts/pantry_review.py apply --run <dir> --decisions <json>   # data migration from the decisions

classify lets Claude sort every ingredient into core, long tail, not a
cooking ingredient or duplicate, with a base ingredient and a short reason.
gaps proposes core ingredients that are missing per cuisine, and aliases.
review.html shows it all: change what is wrong and export the decisions,
which apply turns into a data migration. Nothing is deleted: not cooking
ingredients and duplicates become inactive. The script itself changes nothing
in the database.

Needs ANTHROPIC_API_KEY. Costs about USD 1 for classify and 0.2 for gaps.
"""
import argparse
import csv
import datetime
import html
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv()

from jinja2 import Environment, FileSystemLoader  # noqa: E402

from promptlab.run import RUNS_DIR  # noqa: E402

LABELS = ('core', 'long_tail', 'not_cooking', 'duplicate')
CHUNK = 60
MAX_NEW = 120
env = Environment(loader=FileSystemLoader(str(ROOT / 'data' / 'prompts')))

CLASSIFY_SCHEMA = {
    'type': 'object', 'additionalProperties': False, 'required': ['items'],
    'properties': {'items': {'type': 'array', 'items': {
        'type': 'object', 'additionalProperties': False, 'required': ['id', 'label', 'of', 'base', 'reason'],
        'properties': {'id': {'type': 'integer'}, 'label': {'type': 'string', 'enum': list(LABELS)},
                       'of': {'type': 'string'}, 'base': {'type': 'string'}, 'reason': {'type': 'string'}}}}},
}
GAPS_SCHEMA = {
    'type': 'object', 'additionalProperties': False, 'required': ['new', 'aliases'],
    'properties': {
        'new': {'type': 'array', 'items': {
            'type': 'object', 'additionalProperties': False,
            'required': ['name', 'main_category', 'sub_category', 'base', 'cuisines', 'why'],
            'properties': {'name': {'type': 'string'}, 'main_category': {'type': 'string'}, 'sub_category': {'type': 'string'},
                           'base': {'type': 'string'}, 'cuisines': {'type': 'array', 'items': {'type': 'string'}},
                           'why': {'type': 'string'}}}},
        'aliases': {'type': 'array', 'items': {
            'type': 'object', 'additionalProperties': False, 'required': ['alias', 'of', 'why'],
            'properties': {'alias': {'type': 'string'}, 'of': {'type': 'string'}, 'why': {'type': 'string'}}}},
    },
}


def read_csv(path):
    with open(path, newline='', encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        r['id'] = int(r['id'])
        for k, v in r.items():
            if v in ('', '\\N'):
                r[k] = None
    return rows


def load(run, name, default):
    path = run / name
    return json.loads(path.read_text()) if path.exists() else default


def save(run, name, data):
    tmp = run / (name + '.tmp')
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    tmp.replace(run / name)


def ask(system, user, schema, call=None):
    from services.ai_models import RECIPE_V2_EFFORT, RECIPE_V2_MODEL
    from services.recipe_v2 import claude

    msg, usage = (call or claude.call)(RECIPE_V2_MODEL, RECIPE_V2_EFFORT, [{'role': 'user', 'content': user}],
                                       system=system, schema=schema)
    if msg.stop_reason in ('refusal', 'max_tokens'):
        raise RuntimeError(f'stop_reason {msg.stop_reason}')
    return json.loads(claude.text_of(msg)), usage


def classify(run, rows, call=None, workers=3):
    """Sort every ingredient. Resumable: chunks already done are skipped."""
    done = load(run, 'classify.json', {})
    names = {r['name'].lower() for r in rows}
    pantry = '\n'.join(f"{r['id']} | {r['name']} | {r.get('main_category') or ''} / {r.get('sub_category') or ''}" for r in rows)
    system = env.get_template('pantry/classify.jinja2').render(pantry=pantry)
    chunks = [rows[i:i + CHUNK] for i in range(0, len(rows), CHUNK)]
    todo = [c for c in chunks if not all(str(r['id']) in done for r in c)]
    print(f'{len(rows)} ingredients, {len(todo)} of {len(chunks)} chunks to sort')
    cost = []

    def work(chunk):
        ids = {r['id'] for r in chunk}
        user = 'Sort these entries:\n' + '\n'.join(f"{r['id']} | {r['name']}" for r in chunk)
        data, usage = ask(system, user, CLASSIFY_SCHEMA, call)
        cost.append(usage.get('cost_usd', 0))
        out = {}
        for item in data['items']:
            if item['id'] not in ids:
                continue
            for ref in ('of', 'base'):
                if item[ref] and item[ref].lower() not in names:
                    item['reason'] += f' [{ref} "{item[ref]}" is not in the pantry]'
                    item[ref] = ''
            out[str(item['id'])] = item
        return out

    with ThreadPoolExecutor(max_workers=workers) as pool:
        for out in pool.map(work, todo):
            done.update(out)
            save(run, 'classify.json', done)
            print(f'  {len(done)} of {len(rows)} sorted', flush=True)
    missing = [r['name'] for r in rows if str(r['id']) not in done]
    if missing:
        print(f'{len(missing)} not sorted (e.g. {", ".join(missing[:5])}). Run classify --run again.')
    print(f'Cost: about USD {sum(cost):.2f}')
    return done


def gaps(run, rows, call=None):
    sorted_ = load(run, 'classify.json', {})
    pantry = '\n'.join(f"{r['name']} | {sorted_.get(str(r['id']), {}).get('label', '')}" for r in rows)
    cats = sorted({(r.get('main_category') or '', r.get('sub_category') or '') for r in rows})
    system = env.get_template('pantry/gaps.jinja2').render(
        pantry=pantry, categories='\n'.join(f'{m} / {s}' for m, s in cats), max_new=MAX_NEW)
    data, usage = ask(system, 'List the missing core ingredients and the aliases.', GAPS_SCHEMA, call)
    names = {r['name'].lower() for r in rows}
    data['new'] = [n for n in data['new'] if n['name'].lower() not in names]
    data['aliases'] = [a for a in data['aliases'] if a['of'].lower() in names and a['alias'].lower() not in names]
    save(run, 'gaps.json', data)
    print(f"{len(data['new'])} new core ingredients and {len(data['aliases'])} aliases proposed. "
          f"Cost: about USD {usage.get('cost_usd', 0):.2f}")
    return data


REVIEW_HEAD = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Pantry review</title><style>
:root{--bg:#fafaf9;--fg:#1c1917;--muted:#78716c;--line:#e7e5e4;--card:#fff;--core:#16a34a;--tail:#2563eb;--off:#a8a29e;--dup:#d97706}
@media (prefers-color-scheme:dark){:root{--bg:#1c1917;--fg:#f5f5f4;--muted:#a8a29e;--line:#44403c;--card:#292524}}
body{margin:0;padding:0 16px 40px;background:var(--bg);color:var(--fg);font:14px/1.45 system-ui,sans-serif}
header{position:sticky;top:0;background:var(--bg);padding:10px 0;border-bottom:1px solid var(--line);display:flex;gap:12px;flex-wrap:wrap;align-items:center;z-index:2}
h2{font-size:17px;margin:26px 0 4px} .hint{color:var(--muted);margin:0 0 8px;max-width:70ch}
table{border-collapse:collapse;width:100%} td{padding:5px 8px 5px 0;border-bottom:1px solid var(--line);vertical-align:top}
td.n{font-weight:600;white-space:nowrap} td.r{color:var(--muted);font-size:13px} td.c{color:var(--muted);font-size:12px;white-space:nowrap}
select,input[type=text]{font:inherit;padding:2px 4px;border:1px solid var(--line);border-radius:6px;background:var(--card);color:var(--fg)}
input[type=text]{width:12em} .wrap{overflow-x:auto} .count{font-weight:600}
tr[data-l=core] td.n{color:var(--core)} tr[data-l=long_tail] td.n{color:var(--tail)} tr[data-l=not_cooking] td.n{color:var(--off);text-decoration:line-through} tr[data-l=duplicate] td.n{color:var(--dup)}
button{font:inherit;padding:6px 14px;border-radius:8px;border:1px solid var(--line);background:var(--card);color:var(--fg);cursor:pointer}
</style></head><body>"""


def review(run, rows):
    esc = html.escape
    sorted_ = load(run, 'classify.json', {})
    found = load(run, 'gaps.json', {'new': [], 'aliases': []})
    order = {'not_cooking': 0, 'duplicate': 1, 'core': 2, 'long_tail': 3}
    titles = {
        'not_cooking': ('Not a cooking ingredient', 'Set inactive, not deleted. They can come back later (red wine, beer).'),
        'duplicate': ('Duplicates', 'Merged into the entry in "of": its name becomes an alias, and it is set inactive, so it can be undone.'),
        'core': ('Core', 'What most dishes need. Curated in full: symbol, nutrition, density, allergens.'),
        'long_tail': ('Long tail', 'Kept because a recipe may need it. Not shown by default in the pantry overview.'),
    }
    by = {}
    for r in rows:
        item = sorted_.get(str(r['id']))
        by.setdefault(item['label'] if item else 'core', []).append((r, item))
    opts = lambda cur: ''.join(f'<option value="{k}"{" selected" if k == cur else ""}>{titles[k][0]}</option>' for k in LABELS)  # noqa: E731
    sections = []
    for label in sorted(by, key=order.get):
        trs = []
        for r, item in sorted(by[label], key=lambda x: ((x[0].get('main_category') or ''), x[0]['name'])):
            item = item or {'label': 'core', 'of': '', 'base': '', 'reason': 'not sorted'}
            trs.append(
                f'<tr data-id="{r["id"]}" data-l="{item["label"]}"><td class="n">{esc(r["name"])}</td>'
                f'<td class="c">{esc(r.get("main_category") or "")} / {esc(r.get("sub_category") or "")}</td>'
                f'<td><select class="l">{opts(item["label"])}</select></td>'
                f'<td>of <input type="text" class="of" value="{esc(item["of"])}"></td>'
                f'<td>base <input type="text" class="base" value="{esc(item["base"])}"></td>'
                f'<td class="r">{esc(item["reason"])}</td></tr>')
        t, h = titles[label]
        sections.append(f'<h2>{t} <span class="count">({len(trs)})</span></h2><p class="hint">{h}</p><div class="wrap"><table>{"".join(trs)}</table></div>')
    new = ''.join(
        f'<tr data-new="{n}"><td><input type="checkbox" checked></td><td><input type="text" class="name" value="{esc(x["name"])}"></td>'
        f'<td class="c">{esc(x["main_category"])} / {esc(x["sub_category"])}</td><td>base <input type="text" class="base" value="{esc(x["base"])}"></td>'
        f'<td class="r">{esc(", ".join(x["cuisines"]))}: {esc(x["why"])}</td></tr>' for n, x in enumerate(found['new']))
    aliases = ''.join(
        f'<tr data-alias="{n}"><td><input type="checkbox" checked></td><td class="n">{esc(a["alias"])}</td><td>→ {esc(a["of"])}</td>'
        f'<td class="r">{esc(a["why"])}</td></tr>' for n, a in enumerate(found['aliases']))
    page = REVIEW_HEAD + f"""<header><strong>Pantry review · {esc(run.name)}</strong><span id="sum"></span><button id="export">Export decisions</button></header>
<p class="hint">Claude's suggestions against the core definition. Change what is wrong: the group, "of" for duplicates, and the base ingredient. Untick new ingredients and aliases you do not want. Then export; the decisions become a data migration.</p>
{''.join(sections)}
<h2>Proposed new core ingredients <span class="count">({len(found['new'])})</span></h2><p class="hint">Missing for common cuisines. Ticked ones are added as core and get symbols.</p><div class="wrap"><table>{new}</table></div>
<h2>Proposed aliases <span class="count">({len(found['aliases'])})</span></h2><p class="hint">Names recipes use that should match an existing entry.</p><div class="wrap"><table>{aliases}</table></div>
<script>
const RUN = {json.dumps(run.name)}, NEW = {json.dumps(found['new'], ensure_ascii=False)}, ALIASES = {json.dumps(found['aliases'], ensure_ascii=False)};
function sum() {{
  const c = {{}}; document.querySelectorAll('tr[data-id]').forEach(tr => {{ const l = tr.querySelector('.l').value; tr.dataset.l = l; c[l] = (c[l] || 0) + 1; }});
  document.getElementById('sum').textContent = `core ${{c.core||0}} · long tail ${{c.long_tail||0}} · inactive ${{c.not_cooking||0}} · duplicates ${{c.duplicate||0}}`;
}}
document.addEventListener('change', sum); sum();
document.getElementById('export').onclick = () => {{
  const items = {{}}; document.querySelectorAll('tr[data-id]').forEach(tr => items[tr.dataset.id] = {{label: tr.querySelector('.l').value, of: tr.querySelector('.of').value.trim(), base: tr.querySelector('.base').value.trim()}});
  const added = [...document.querySelectorAll('tr[data-new]')].filter(tr => tr.querySelector('input[type=checkbox]').checked)
    .map(tr => Object.assign({{}}, NEW[+tr.dataset.new], {{name: tr.querySelector('.name').value.trim(), base: tr.querySelector('.base').value.trim()}}));
  const aliases = [...document.querySelectorAll('tr[data-alias]')].filter(tr => tr.querySelector('input[type=checkbox]').checked).map(tr => ALIASES[+tr.dataset.alias]);
  const stamp = new Date().toISOString().slice(0, 19).replace(/[-:T]/g, '');
  const blob = new Blob([JSON.stringify({{run: RUN, items, new: added, aliases}}, null, 2)], {{type: 'application/json'}});
  Object.assign(document.createElement('a'), {{href: URL.createObjectURL(blob), download: `pantry-decisions-${{RUN}}-${{stamp}}.json`}}).click();
}};
</script></body></html>"""
    path = run / 'review.html'
    path.write_text(page)
    return path


def plan(rows, decisions):
    """The exported decisions as data for the migration. Ingredients are referred to by
    food_id, which is the same in every database; a new ingredient by "new:<name>"."""
    by_id = {str(r['id']): r for r in rows}
    by_name = {r['name'].lower(): r for r in rows}
    items = decisions['items']
    new = {n['name'].lower(): n for n in decisions['new']}

    def item(name):
        return items[str(by_name[name.lower()]['id'])]

    def winner(name, seen=()):
        """Follow duplicates to the entry that is kept."""
        key = name.lower()
        if key in new:
            return 'new:' + key
        if key not in by_name:
            raise SystemExit(f'"{name}" is neither in the pantry nor a new ingredient')
        it = item(key)
        if it['label'] == 'duplicate':
            if key in seen:
                raise SystemExit(f'Duplicates point at each other: {" -> ".join(seen + (key,))}. Pick the one to keep.')
            return winner(it['of'], seen + (key,))
        return by_name[key]['food_id']

    def kept(ref):
        return ref.startswith('new:') or items[str(next(r['id'] for r in rows if r['food_id'] == ref))]['label'] in ('core', 'long_tail')

    out = {'tiers': {}, 'inactive': [], 'merge': {}, 'bases': {}, 'new': [], 'aliases': []}
    for rid, it in sorted(items.items(), key=lambda x: int(x[0])):
        row = by_id[rid]
        fid = row['food_id']
        if it['label'] in ('core', 'long_tail'):
            out['tiers'][fid] = it['label']
            base = winner(it['base']) if it['base'] else None
            if base and base != fid and kept(base):
                out['bases'][fid] = base
        elif it['label'] == 'not_cooking':
            out['inactive'].append(fid)
        else:
            target = winner(it['of'], (row['name'].lower(),))
            if not kept(target):
                raise SystemExit(f'"{row["name"]}" is a duplicate of "{it["of"]}", which is not kept')
            out['merge'][fid] = (target, it.get('alias', True))
    for n in decisions['new']:
        base = winner(n['base']) if n['base'] else None
        out['new'].append((n['name'].lower(), n['main_category'], n['sub_category'], base if base and kept(base) else None))
    active = {r['name'].lower() for r in rows if items[str(r['id'])]['label'] in ('core', 'long_tail')} | set(new)
    for a in decisions['aliases']:
        if a['alias'].lower() not in active:
            out['aliases'].append((a['alias'].lower(), winner(a['of'])))
    return out


MIGRATION = '''"""pantry review {run}

The pantry decisions from {run} (RECIPE_MODEL_V2.md, "Kjerne og lang hale"):
{n_core} core and {n_tail} long tail ingredients get their tier, {n_bases} get a base
ingredient, {n_new} new core ingredients are added and {n_aliases} aliases. Nothing is deleted:
{n_inactive} that are not cooking ingredients are set inactive, and {n_merge} duplicates are
set inactive with their recipe lines and aliases moved to the entry that is kept,
and their name added as an alias of it.

Rows are found by food_id, and rows that are missing are skipped, so the
migration also runs on databases with another pantry.

Downgrade sets the statuses, tiers and base ingredients back and removes the
aliases and the new ingredients it added (a new ingredient a recipe already
uses is set inactive instead). Recipe lines and aliases moved from a duplicate
stay with the entry that was kept.

Made by scripts/pantry_review.py apply.

Revision ID: {revision}
Revises: {down}
Create Date: {date}

"""
import datetime

from alembic import op
import sqlalchemy as sa


revision = '{revision}'
down_revision = '{down}'
branch_labels = None
depends_on = None

SOURCE = 'pantry-review'  # data_source of the new ingredients
# food_id: tier
TIERS = {tiers}
# not a cooking ingredient: set inactive
INACTIVE = {inactive}
# duplicate food_id: (food_id or "new:<name>" of the entry that is kept, add the duplicate's name as an alias)
MERGE = {merge}
# food_id: base ingredient
BASES = {bases}
# (name, main_category, sub_category, base ingredient)
NEW = {new}
# (alias, ingredient)
ALIASES = {aliases}


def _q(conn, sql, **params):
    return conn.execute(sa.text(sql), params)


def _refs(conn):
    """food_id -> id, plus "new:<name>" -> id for the new ingredients."""
    refs = dict(_q(conn, 'SELECT food_id, id FROM ingredient').all())
    for name, *_ in NEW:
        found = _q(conn, "SELECT id FROM ingredient WHERE lower(name) = :n AND status = 'active' ORDER BY id", n=name).first()
        if found:
            refs['new:' + name] = found[0]
    return refs


def _alias(conn, name, ingredient_id):
    if ingredient_id and not _q(conn, 'SELECT 1 FROM ingredient_alias WHERE name = :n', n=name).first():
        _q(conn, 'INSERT INTO ingredient_alias (ingredient_id, name, created_at) VALUES (:i, :n, :t)',
           i=ingredient_id, n=name, t=datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None))


def upgrade():
    conn = op.get_bind()
    refs = _refs(conn)
    number = max((int(f) for f in refs if f and f.isdigit()), default=0)
    for name, main, sub, _ in NEW:
        if 'new:' + name in refs:
            continue
        number += 1
        _q(conn, "INSERT INTO ingredient (food_id, name, main_category, sub_category, default_unit, is_staple, "
                 "has_transparent_image, status, tier, data_source, created_at) "
                 "VALUES (:f, :n, :m, :s, 'g', :no, :no, 'active', 'core', :src, :t)",
           f=f'{{number:06d}}', n=name, m=main, s=sub, no=False, src=SOURCE, t=datetime.date.today().isoformat())
    refs = _refs(conn)
    for fid, tier in TIERS.items():
        _q(conn, 'UPDATE ingredient SET tier = :t WHERE food_id = :f', t=tier, f=fid)
    bases = dict(BASES, **{{'new:' + name: base for name, _, _, base in NEW if base}})
    for ref, base in bases.items():
        if refs.get(ref) and refs.get(base):
            _q(conn, 'UPDATE ingredient SET base_ingredient_id = :b WHERE id = :i', b=refs[base], i=refs[ref])
    for fid in INACTIVE:
        _q(conn, "UPDATE ingredient SET status = 'inactive' WHERE food_id = :f AND status = 'active'", f=fid)
    for loser, (winner, alias) in MERGE.items():
        lid, wid = refs.get(loser), refs.get(winner)
        if not lid or not wid:
            continue
        for table in ('recipe_ingredient', 'recipe_line', 'ingredient_alias'):
            _q(conn, f'UPDATE {{table}} SET ingredient_id = :w WHERE ingredient_id = :l', w=wid, l=lid)
        _q(conn, "UPDATE ingredient SET status = 'inactive' WHERE id = :l", l=lid)
        if alias:
            _alias(conn, _q(conn, 'SELECT lower(name) FROM ingredient WHERE id = :l', l=lid).scalar(), wid)
    for name, ref in ALIASES:
        _alias(conn, name, refs.get(ref))


def downgrade():
    conn = op.get_bind()
    refs = _refs(conn)
    added = [(name, refs.get(ref)) for name, ref in ALIASES]
    for loser, (winner, alias) in MERGE.items():
        if alias and refs.get(loser):
            added.append((_q(conn, 'SELECT lower(name) FROM ingredient WHERE id = :l', l=refs[loser]).scalar(), refs.get(winner)))
    for name, ingredient_id in added:
        _q(conn, 'DELETE FROM ingredient_alias WHERE name = :n AND ingredient_id = :i', n=name, i=ingredient_id)
    for fid in INACTIVE + list(MERGE):
        _q(conn, "UPDATE ingredient SET status = 'active' WHERE food_id = :f AND status = 'inactive'", f=fid)
    for fid in list(TIERS) + list(MERGE) + INACTIVE:
        _q(conn, 'UPDATE ingredient SET tier = NULL, base_ingredient_id = NULL WHERE food_id = :f', f=fid)
    for name, *_ in NEW:
        for (i,) in _q(conn, 'SELECT id FROM ingredient WHERE lower(name) = :n AND data_source = :s', n=name, s=SOURCE).all():
            _q(conn, 'UPDATE ingredient SET base_ingredient_id = NULL WHERE base_ingredient_id = :i', i=i)
            used = _q(conn, 'SELECT 1 FROM recipe_ingredient WHERE ingredient_id = :i UNION ALL '
                            'SELECT 1 FROM recipe_line WHERE ingredient_id = :i', i=i).first()
            if used:
                _q(conn, "UPDATE ingredient SET status = 'inactive', tier = NULL WHERE id = :i", i=i)
            else:
                _q(conn, 'DELETE FROM ingredient_alias WHERE ingredient_id = :i', i=i)
                _q(conn, 'DELETE FROM ingredient WHERE id = :i', i=i)
'''


def apply(run, rows, decisions, down_revision, versions=ROOT / 'migrations' / 'versions'):
    """Write the migration for the exported decisions. Returns its path."""
    import pprint
    import uuid

    p = plan(rows, decisions)
    revision = uuid.uuid4().hex[:12]
    fmt = lambda x: pprint.pformat(x, width=110, sort_dicts=True)  # noqa: E731
    text = MIGRATION.format(
        run=run.name, revision=revision, down=down_revision, date=datetime.date.today().isoformat(),
        n_core=sum(t == 'core' for t in p['tiers'].values()), n_tail=sum(t == 'long_tail' for t in p['tiers'].values()),
        n_bases=len(p['bases']), n_new=len(p['new']), n_aliases=len(p['aliases']), n_inactive=len(p['inactive']),
        n_merge=len(p['merge']), tiers=fmt(p['tiers']), inactive=fmt(p['inactive']), merge=fmt(p['merge']),
        bases=fmt(p['bases']), new=fmt(p['new']), aliases=fmt(p['aliases']))
    path = versions / f'{revision}_pantry_review_{run.name.replace("-", "_")}.py'
    path.write_text(text)
    return path


def head_revision():
    import re

    revs, downs = set(), set()
    for f in (ROOT / 'migrations' / 'versions').glob('*.py'):
        text = f.read_text()
        rev = re.search(r"^revision = '(\w+)'", text, re.M)
        down = re.search(r"^down_revision = '(\w+)'", text, re.M)
        if rev:
            revs.add(rev.group(1))
        if down:
            downs.add(down.group(1))
    heads = revs - downs
    if len(heads) != 1:
        raise SystemExit(f'Expected one migration head, found {sorted(heads)}')
    return heads.pop()


def main(argv=None):
    ap = argparse.ArgumentParser(prog='python scripts/pantry_review.py')
    sub = ap.add_subparsers(dest='command', required=True)
    p = sub.add_parser('classify', help='sort every ingredient (new run with --input, continue with --run)')
    p.add_argument('--input', type=Path)
    p.add_argument('--run', type=Path)
    p = sub.add_parser('gaps', help='propose missing core ingredients and aliases')
    p.add_argument('--run', type=Path, required=True)
    p = sub.add_parser('review', help='write review.html')
    p.add_argument('--run', type=Path, required=True)
    p = sub.add_parser('apply', help='write a data migration from the exported decisions')
    p.add_argument('--run', type=Path, required=True)
    p.add_argument('--decisions', type=Path, required=True)
    args = ap.parse_args(argv)

    if args.command == 'apply':
        decisions = json.loads(args.decisions.read_text())
        print(apply(args.run, read_csv(args.run / 'ingredients.csv'), decisions, head_revision()))
        return

    if args.command == 'classify':
        if not args.input and not args.run:
            raise SystemExit('Give --input (a CSV from scripts/ingredient_symbols.py export) or --run')
        run = args.run or RUNS_DIR / f"pantry-{datetime.datetime.now():%Y%m%d-%H%M}"
        run.mkdir(parents=True, exist_ok=True)
        if args.input:
            (run / 'ingredients.csv').write_bytes(args.input.read_bytes())
        classify(run, read_csv(run / 'ingredients.csv'))
        print(f'Next: python scripts/pantry_review.py gaps --run {run}')
    else:
        rows = read_csv(args.run / 'ingredients.csv')
        if args.command == 'gaps':
            gaps(args.run, rows)
        print(review(args.run, rows))


if __name__ == '__main__':
    main()
