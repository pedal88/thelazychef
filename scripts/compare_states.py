"""The structuring prompt before and after the state catalog (26.10.2026), on the same recipes.

The five fasit dishes (their recorded source texts) and the recipes in data/pilot_v2/inputs/state_sources.json
(baking, desserts, Asian, grill, sauces, preserving) go through round 2 twice: with the code at --old (default
origin/main, checked out in a worktree next to the results) and with this checkout. Both use the model and effort
the app uses, and an empty pantry, so pantry ids are left out on both sides.

It also converts the old answers with services/recipe_v2/states.fill(), the way the saved v2 recipes will be
converted, so the report shows conversion next to a fresh structuring.

Run from the repo root. Needs ANTHROPIC_API_KEY; it is passed on to the runs and never printed or stored:

    ANTHROPIC_API_KEY=... ./venv/bin/python -m scripts.compare_states

Results and the report go outside the repo (the answers are long, and the repo is public), by default to
~/promptlab-runs/states-compare: old/<name>.json, new/<name>.json and report.md. Runs that exist are skipped;
--force runs them again. 15 recipes on both sides cost about 4 to 6 dollars. Nothing is written to a database.
"""
import argparse
import copy
import json
import os
import re
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Runs in the tree being tested: round 2 with its validator loop, the answer to the file in argv[1]
RUNNER = '''
import json, os, sys
sys.path.insert(0, os.getcwd())
from app import app, db
from services.recipe_v2 import generate
with app.app_context():
    db.create_all()
    recipe, attempts = generate.structure(sys.stdin.read())
with open(sys.argv[1], 'w', encoding='utf-8') as f:
    json.dump({'recipe': recipe, 'attempts': attempts}, f, ensure_ascii=False, indent=1)
'''


def sources():
    out = {}
    for f in sorted((ROOT / 'data' / 'pilot_v2' / 'results_0b' / 'opus-low' / 'fasit').glob('*.json')):
        out[f.stem] = json.loads(f.read_text())['source_text']
    out.update(json.loads((ROOT / 'data' / 'pilot_v2' / 'inputs' / 'state_sources.json').read_text())['sources'])
    return out


def old_tree(out, rev):
    tree = out / 'old-tree'
    if not tree.exists():
        subprocess.run(['git', 'fetch', '-q', 'origin', 'main'], cwd=ROOT, check=True)
        subprocess.run(['git', 'worktree', 'add', '-q', '--detach', str(tree), rev], cwd=ROOT, check=True)
    return tree


def run(tree, text, dest):
    with tempfile.TemporaryDirectory() as tmp:
        env = {**os.environ, 'DB_BACKEND': 'local', 'DATABASE_URL': f'sqlite:///{tmp}/pantry.db'}
        env.setdefault('GOOGLE_API_KEY', 'not-used')  # app.py wants one; round 2 calls Claude only
        p = subprocess.run([sys.executable, '-c', RUNNER, str(dest)], cwd=tree, input=text, text=True,
                           capture_output=True, env=env)
    if p.returncode:
        dest.with_suffix('.err').write_text(p.stderr[-4000:])
        return f'{dest.parent.name}/{dest.stem}: failed, see {dest.with_suffix(".err")}'
    return f'{dest.parent.name}/{dest.stem}: done'


def facts(res):
    """What one run says about states, notes, varieties and verbs."""
    from services.recipe_v2 import states

    empty = set(states.catalog()['empty_verbs']['en'] + states.catalog()['empty_verbs']['nb'])
    attempts = res.get('attempts') or []
    r = res.get('recipe') or {}
    lines, steps = r.get('ingredients') or [], r.get('steps') or []
    return {
        'valid': bool(res.get('recipe')), 'attempts': len(attempts),
        'failed_rules': [sorted({e['rule'] for e in a.get('errors') or []}, key=str) for a in attempts if not a.get('valid')],
        'cost_usd': round(sum(a.get('cost_usd') or 0 for a in attempts), 3),
        'seconds': round(sum(a.get('seconds') or 0 for a in attempts)),
        'lines': len(lines), 'steps': len(steps),
        'with_state': sum(1 for i in lines if i.get('state') or i.get('cut')),
        'with_grade': sum(1 for i in lines if i.get('grade')),
        'with_note': sum(1 for i in lines if i.get('prep_style')),
        'note_is_state': [f"{i['name']}: {i['prep_style']}" for i in lines
                          if i.get('prep_style') and states.from_text(i['prep_style'])[0]],
        'varieties': [f"{i['name']}: {i['variety']}" for i in lines if i.get('variety')],
        'empty_verbs': [f"{s.get('short')}" for s in steps if (s.get('verb') or '').lower() in empty],
    }


def said(i):
    """A line's state, grade, variety and note in a few words, for the table."""
    if not i:
        return '–'
    state = ' '.join(x for x in (i.get('state') or i.get('cut') or '', i.get('grade') or '') if x)
    bits = [state or '·'] + ([f"[{i['variety']}]"] if i.get('variety') else []) + ([f"«{i['prep_style']}»"] if i.get('prep_style') else [])
    return ' '.join(bits)


def pair(a, b):
    """Lines of two answers side by side, by name and in order (a dish can use the same ingredient twice)."""
    def key(i):
        return re.sub(r'\s+', ' ', (i.get('name') or '').lower()).strip()
    rest = list(b)
    rows = []
    for i in a:
        j = next((x for x in rest if key(x) == key(i)), None)
        if j is not None:
            rest.remove(j)
        rows.append((i, j))
    return rows + [(None, j) for j in rest]


def report(out, names):
    from services.recipe_v2 import states

    md = ['# Tilstandskatalogen: gammel mot ny strukturprompt', '',
          'Gammel = koden på main før katalogen. Konvertert = det gamle svaret gjennom `states.fill()`. '
          'Ny = denne grenen. Tilstand vises som id og grad, [variant], «notat»; · er ingen tilstand.', '']
    rows, totals = [], {'old': [], 'new': []}
    for name in names:
        res = {side: json.loads((out / side / f'{name}.json').read_text()) if (out / side / f'{name}.json').exists() else {}
               for side in ('old', 'new')}
        f = {side: facts(res[side]) for side in res}
        conv = copy.deepcopy(res['old'].get('recipe') or {})
        states.fill(conv)
        f['conv'] = facts({'recipe': conv, 'attempts': []})
        for side in totals:
            totals[side].append(f[side])
        rows.append((name, f, res, conv))

    md += ['## Oppsummert', '', '| | Gammel | Ny |', '|---|---|---|']

    def tot(side, k):
        return sum(x[k] if isinstance(x[k], (int, float)) else len(x[k]) for x in totals[side])
    for label, k in (('Gyldige', 'valid'), ('Forsøk i alt', 'attempts'), ('Linjer', 'lines'), ('Linjer med tilstand', 'with_state'),
                     ('Linjer med grad', 'with_grade'), ('Linjer med notat', 'with_note'), ('Notat som er en tilstand', 'note_is_state'),
                     ('Varianter', 'varieties'), ('Tomme verb', 'empty_verbs'), ('Kostnad (USD)', 'cost_usd'), ('Sekunder', 'seconds')):
        md.append(f"| {label} | {round(tot('old', k), 2)} | {round(tot('new', k), 2)} |")
    md += ['', f"Gyldig på første forsøk: gammel {sum(1 for x in totals['old'] if x['valid'] and x['attempts'] == 1)}, "
               f"ny {sum(1 for x in totals['new'] if x['valid'] and x['attempts'] == 1)} av {len(names)}.", '']

    for name, f, res, conv in rows:
        md += [f'## {name}', '']
        for side, label in (('old', 'Gammel'), ('conv', 'Konvertert'), ('new', 'Ny')):
            x = f[side]
            head = (f"{label}: {'gyldig' if x['valid'] else 'UGYLDIG'}, {x['attempts']} forsøk, {x['cost_usd']} USD"
                    + (f", feilet på regel {x['failed_rules']}" if x['failed_rules'] else '')) if side != 'conv' else label
            md.append(f"- {head}: {x['with_state']}/{x['lines']} linjer med tilstand, {x['with_grade']} med grad, {x['with_note']} med notat"
                      + (f"; notat som er tilstand: {', '.join(x['note_is_state'])}" if x['note_is_state'] else '')
                      + (f"; varianter: {', '.join(x['varieties'])}" if x['varieties'] else '')
                      + (f"; tomme verb: {', '.join(x['empty_verbs'])}" if x['empty_verbs'] else ''))
        md += ['', '| Linje | Gammel | Konvertert | Ny |', '|---|---|---|---|']
        conv_by = {i['local_id']: i for i in conv.get('ingredients') or []}
        for a, b in pair((res['old'].get('recipe') or {}).get('ingredients') or [], (res['new'].get('recipe') or {}).get('ingredients') or []):
            md.append(f"| {(a or b)['name']} | {said(a)} | {said(conv_by.get(a['local_id']) if a else None)} | {said(b)} |")
        md.append('')
    (out / 'report.md').write_text('\n'.join(md))
    return out / 'report.md'


def main():
    ap = argparse.ArgumentParser(description='The structuring prompt before and after the state catalog.')
    ap.add_argument('--old', default='origin/main', help='the code to compare with (a git revision)')
    ap.add_argument('--only', nargs='*', help='only these recipes')
    ap.add_argument('--out', default=str(Path.home() / 'promptlab-runs' / 'states-compare'))
    ap.add_argument('--workers', type=int, default=4)
    ap.add_argument('--force', action='store_true')
    ap.add_argument('--report', action='store_true', help='only write the report from saved runs')
    args = ap.parse_args()

    out = Path(args.out).expanduser()
    src = sources()
    names = [n for n in src if not args.only or n in args.only]
    if not args.report:
        if not os.getenv('ANTHROPIC_API_KEY'):
            sys.exit('ANTHROPIC_API_KEY is not set.')
        trees = {'old': old_tree(out, args.old), 'new': ROOT}
        jobs = []
        for side, tree in trees.items():
            (out / side).mkdir(parents=True, exist_ok=True)
            for n in names:
                dest = out / side / f'{n}.json'
                if args.force or not dest.exists():
                    jobs.append((tree, src[n], dest))
        print(f'{len(jobs)} runs ({len(names)} recipes, old and new).')
        with ThreadPoolExecutor(args.workers) as pool:
            for line in pool.map(lambda j: run(*j), jobs):
                print(line, flush=True)
    print(f'Report: {report(out, names)}')


if __name__ == '__main__':
    main()
