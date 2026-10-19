"""Review the pantry against the core definition (RECIPE_MODEL_V2.md, "Kjerne og lang hale").

    python scripts/ingredient_symbols.py export                   # CSV of active ingredients from production
    python scripts/pantry_review.py classify --input <csv>        # new run in ~/promptlab-runs/pantry-<time>
    python scripts/pantry_review.py gaps --run <dir>              # missing core ingredients and aliases
    python scripts/pantry_review.py review --run <dir>            # writes review.html

classify lets Claude sort every ingredient into core, long tail, not a
cooking ingredient or duplicate, with a base ingredient and a short reason.
gaps proposes core ingredients that are missing per cuisine, and aliases.
review.html shows it all: change what is wrong and export the decisions,
which become a data migration in the next step. This script changes nothing
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
    args = ap.parse_args(argv)

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
