"""Contact sheet: one row per sample, one column per variant combination.

Open sheet.html in a browser, give cells 1-5 and mark the best in each row,
then "Export scores" and run `python -m promptlab score <run> scores.json`.
"""
import html
import json
from pathlib import Path

PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Prompt lab: {title}</title>
<style>
:root {{ --bg:#fafaf9; --fg:#1c1917; --muted:#78716c; --line:#e7e5e4; --card:#fff; --accent:#c2410c; }}
@media (prefers-color-scheme: dark) {{ :root {{ --bg:#1c1917; --fg:#f5f5f4; --muted:#a8a29e; --line:#44403c; --card:#292524; --accent:#fb923c; }} }}
body {{ margin:0; padding:16px; background:var(--bg); color:var(--fg); font:14px/1.4 system-ui,sans-serif; }}
header {{ display:flex; flex-wrap:wrap; gap:12px; align-items:baseline; margin-bottom:12px; }}
h1 {{ font-size:18px; margin:0; }} .meta {{ color:var(--muted); }}
button {{ font:inherit; border:1px solid var(--line); background:var(--card); color:var(--fg); border-radius:6px; padding:2px 8px; cursor:pointer; }}
button.on {{ background:var(--accent); border-color:var(--accent); color:#fff; }}
.wrap {{ overflow-x:auto; }} table {{ border-collapse:collapse; }}
th, td {{ border:1px solid var(--line); padding:8px; vertical-align:top; background:var(--card); }}
th {{ position:sticky; top:0; font-weight:600; text-align:left; }}
td.sample {{ font-weight:600; white-space:nowrap; }}
img {{ width:{size}px; height:{size}px; object-fit:contain; display:block; background:repeating-conic-gradient(var(--line) 0 25%, transparent 0 50%) 0 0/16px 16px; }}
pre {{ white-space:pre-wrap; max-width:420px; max-height:300px; overflow:auto; margin:0; }}
details {{ max-width:{size}px; color:var(--muted); font-size:12px; }} .err {{ color:#dc2626; max-width:{size}px; }}
.score {{ display:flex; gap:4px; margin-top:6px; flex-wrap:wrap; }}
</style></head><body>
<header><h1>{title}</h1><span class="meta">{meta}</span>
<button id="export">Export scores</button><span class="meta" id="count"></span></header>
<div class="wrap"><table><thead><tr><th>Sample</th>{heads}</tr></thead><tbody>{rows}</tbody></table></div>
<script>
const run = {data};
const scores = Object.fromEntries(run.cells.filter(c => c.score).map(c => [c.id, c.score]));
function paint() {{
  document.querySelectorAll('[data-cell]').forEach(b => {{
    const s = scores[b.dataset.cell] || {{}};
    b.classList.toggle('on', b.dataset.kind === 'best' ? !!s.best : s.value === Number(b.dataset.value));
  }});
  document.getElementById('count').textContent = Object.keys(scores).length + ' scored';
}}
document.addEventListener('click', e => {{
  const b = e.target.closest('[data-cell]'); if (!b) return;
  const id = b.dataset.cell, s = scores[id] || (scores[id] = {{}});
  if (b.dataset.kind === 'best') {{
    const row = b.dataset.row;
    run.cells.filter(c => c.sample === row && c.id !== id && scores[c.id]).forEach(c => delete scores[c.id].best);
    s.best = !s.best;
  }} else {{
    const v = Number(b.dataset.value); s.value = s.value === v ? undefined : v;
  }}
  paint();
}});
document.getElementById('export').onclick = () => {{
  const blob = new Blob([JSON.stringify(scores, null, 2)], {{type: 'application/json'}});
  const a = Object.assign(document.createElement('a'), {{href: URL.createObjectURL(blob), download: 'scores.json'}});
  a.click();
}};
paint();
</script></body></html>
"""


def _cell_html(cell: dict, kind: str) -> str:
    esc = html.escape
    if cell.get('output') is None:
        body = f'<div class="err">{esc(cell.get("error", "not run (dry run)"))}</div>'
    elif kind == 'image':
        body = f'<img src="{esc(cell["output"])}" alt="{esc(cell["sample"])}" loading="lazy">'
    else:
        body = f'<pre>{esc(cell["output"])}</pre>'
    buttons = ''.join(
        f'<button data-cell="{cell["id"]}" data-value="{v}">{v}</button>' for v in range(1, 6)
    ) + f'<button data-cell="{cell["id"]}" data-kind="best" data-row="{esc(cell["sample"])}">best</button>'
    return f'<td>{body}<details><summary>prompt</summary>{esc(cell["prompt"])}</details><div class="score">{buttons}</div></td>'


def write_sheet(folder: Path, record: dict, size: int = 220) -> Path:
    variants = list(dict.fromkeys(c['variant'] for c in record['cells']))
    samples = list(dict.fromkeys(c['sample'] for c in record['cells']))
    by_key = {(c['sample'], c['variant']): c for c in record['cells']}
    heads = ''.join(f'<th>{html.escape(v)}</th>' for v in variants)
    rows = ''.join(
        f'<tr><td class="sample">{html.escape(s)}</td>'
        + ''.join(_cell_html(by_key[(s, v)], record['kind']) if (s, v) in by_key else '<td></td>' for v in variants)
        + '</tr>'
        for s in samples
    )
    meta = f"{record['model']} · {record['started']} · commit {record['git_commit']}{' (prompts uncommitted)' if record['git_dirty'] else ''}"
    data = json.dumps(record, ensure_ascii=False).replace('</', '<\\/')
    page = PAGE.format(title=html.escape(record['task']), meta=html.escape(meta), heads=heads, rows=rows, data=data, size=size)
    path = folder / 'sheet.html'
    path.write_text(page)
    return path
