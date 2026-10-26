"""Step 4 of the state catalog (26.10.2026): give the saved v2 recipes their states.

Two steps, run from the repo root against production:

1. Plan (read only). Reads every v2 recipe, runs services/recipe_v2/states.fill() on a copy and writes the plan:
   for each line that would change, what it is now and what it becomes, where the state comes from (the note, the
   old cut, or the prep step) and a flag where a person should look. On Postgres the transaction is set to read only
   and rolled back; nothing is written to the database.

       DB_BACKEND=cloudsql INSTANCE_CONNECTION_NAME=... DB_USER=... DB_NAME=... ./venv/bin/python -m scripts.convert_states

   The plan goes outside the repo (it holds recipe content): ~/promptlab-runs/state-conversion/plan.json, and a
   report to read, report.md. Edit plan.json to change a line ("after") or drop it before applying.

2. Apply (writes). Only with --apply and the reviewed plan. Each line is written only if it still is what the plan
   says it was ("before"); the rest are skipped and listed. state, grade, variety and prep_style are the only
   columns written; cut is left as it is. One transaction: all or nothing.

       ... ./venv/bin/python -m scripts.convert_states --apply ~/promptlab-runs/state-conversion/plan.json
"""
import argparse
import copy
import getpass
import json
import os
from pathlib import Path

FIELDS = ('state', 'grade', 'variety', 'prep_style')
# Words in a note that name the kind of an ingredient, not a state: they become its variety
VARIETY_WORDS = ('melne', 'kokefaste', 'modne', 'floury', 'waxy', 'ripe', 'firm', 'fast', 'søte', 'sure')


def line_fields(line):
    return {k: line.get(k) for k in FIELDS}


def plan_recipe(v2, db_ids):
    """The lines of one recipe that fill() changes, with where the state comes from and what to look at."""
    from services.recipe_v2 import states

    after = copy.deepcopy(v2)
    states.fill(after)
    step_of = {u: s for s in v2['steps'] for u in s.get('uses') or []}
    rows = []
    for old, new in zip(v2['ingredients'], after['ingredients']):
        if old.get('variety') is None and old.get('prep_style'):  # a note that names the kind: make it the variety
            rest = new.get('prep_style') or ''
            hit = next((w for w in VARIETY_WORDS if w in rest.lower().replace(',', ' ').split()), None)
            if hit:
                new['variety'] = hit
                rest = ' '.join(x for x in rest.replace(',', ' ').split() if x.lower() != hit).strip()
                if rest:
                    new['prep_style'] = rest
                else:
                    new.pop('prep_style', None)
        before, now = line_fields(old), line_fields(new)
        if before == now:
            continue
        step = step_of.get(old['local_id']) or {}
        others = [u for u in step.get('uses') or [] if u != old['local_id']]
        if old.get('cut'):
            source = 'cut'
        elif states.from_text(old.get('prep_style'))[0] == now['state'] and now['state']:
            source = 'note'
        elif now['state']:
            source = 'step'
        else:
            source = 'note'  # only the note changed (a variety)
        flags = []
        if source == 'step' and step.get('phase') == 'prep' and others:
            flags.append('mixed_step')  # the step uses other lines too: does it change this one?
        if now.get('prep_style') and now['prep_style'] not in (states.catalog()['notes']['en'] + states.catalog()['notes']['nb']):
            flags.append('note_left')  # what is left of the note is not one the catalog knows
        if now.get('variety'):
            flags.append('variety')
        rows.append({'line_id': db_ids[old['local_id']], 'local_id': old['local_id'], 'name': old['name'],
                     'unit': old.get('unit'), 'step': step.get('short'), 'step_method': step.get('method'),
                     'before': before, 'after': now, 'source': source, 'flags': flags})
    return rows


def make_plan(out):
    from sqlalchemy import text
    from app import app, db
    from database.models import Recipe
    from services.recipe_v2.store import to_v2

    plan = []
    with app.app_context():
        conn = db.session.connection()
        if conn.dialect.name == 'postgresql':
            conn.execute(text('SET TRANSACTION READ ONLY'))
        recipes = db.session.execute(db.select(Recipe).where(Recipe.schema_version == 2).order_by(Recipe.id)).scalars().all()
        for r in recipes:
            v2 = to_v2(r)
            by_local = {line.local_id: line for line in r.lines}
            for i in v2['ingredients']:  # the columns as they are, so the plan's "before" is what the database holds
                line = by_local[i['local_id']]
                for k in FIELDS + ('cut',):
                    if getattr(line, k) is None:
                        i.pop(k, None)
                    else:
                        i[k] = getattr(line, k)
            rows = plan_recipe(v2, {local_id: line.id for local_id, line in by_local.items()})
            if rows:
                plan.append({'recipe_id': r.id, 'title': r.title, 'language': r.language, 'lines': rows})
        total = len(recipes)
        db.session.rollback()  # nothing to keep, and nothing was written

    out.mkdir(parents=True, exist_ok=True)
    (out / 'plan.json').write_text(json.dumps(plan, ensure_ascii=False, indent=1))
    (out / 'report.md').write_text(report(plan, total))
    lines = [x for p in plan for x in p['lines']]
    print(f'v2 recipes: {total}, with changes: {len(plan)}, lines to change: {len(lines)}')
    for source in ('note', 'cut', 'step'):
        print(f"  from the {source}: {sum(1 for x in lines if x['source'] == source)}")
    for flag in ('mixed_step', 'note_left', 'variety'):
        print(f"  flagged {flag}: {sum(1 for x in lines if flag in x['flags'])}")
    print(f"Plan: {out / 'plan.json'}\nReport: {out / 'report.md'}")


def said(f):
    bits = [' '.join(x for x in (f.get('state'), f.get('grade')) if x) or '·']
    if f.get('variety'):
        bits.append(f"[{f['variety']}]")
    if f.get('prep_style'):
        bits.append(f"«{f['prep_style']}»")
    return ' '.join(bits)


def report(plan, total):
    lines = [x for p in plan for x in p['lines']]
    md = ['# Konvertering av tilstander: plan', '',
          f'{total} v2-oppskrifter, {len(plan)} med endringer, {len(lines)} linjer. Ingenting er skrevet.', '',
          'Kilde: note = lest fra prep_style, cut = det gamle feltet, step = metoden i forberedelsessteget. '
          'Flagg: mixed_step = steget bruker flere linjer, note_left = det som er igjen av notatet, variety = ny variant.', '']
    for p in plan:
        md += [f"## {p['title']} (#{p['recipe_id']})", '', '| Linje | Nå | Blir | Kilde | Steg | Flagg |', '|---|---|---|---|---|---|']
        for x in p['lines']:
            md.append(f"| {x['name']} | {said(x['before'])} | {said(x['after'])} | {x['source']} | "
                      f"{x['step'] or ''} ({x['step_method'] or ''}) | {', '.join(x['flags'])} |")
        md.append('')
    return '\n'.join(md)


def apply_plan(path):
    from app import app, db
    from database.models import RecipeLine

    plan = json.loads(Path(path).expanduser().read_text())
    rows = [x for p in plan for x in p['lines']]
    written, skipped = 0, []
    with app.app_context():
        for x in rows:
            line = db.session.get(RecipeLine, x['line_id'])
            if line is None or line.local_id != x['local_id'] or {k: getattr(line, k) for k in FIELDS} != x['before']:
                skipped.append(x)
                continue
            for k in FIELDS:
                setattr(line, k, x['after'].get(k))
            written += 1
        db.session.commit()
    print(f'Written: {written} lines. Skipped (changed since the plan): {len(skipped)}')
    for x in skipped:
        print(f"  {x['line_id']} {x['name']}")


def main():
    ap = argparse.ArgumentParser(description='Give the saved v2 recipes their states: plan (read only), then apply.')
    ap.add_argument('--out', default=str(Path.home() / 'promptlab-runs' / 'state-conversion'))
    ap.add_argument('--apply', metavar='PLAN', help='write the reviewed plan to the database')
    args = ap.parse_args()

    if os.getenv('DB_BACKEND', 'local').lower() == 'cloudsql' and not os.getenv('DB_PASS'):
        os.environ['DB_PASS'] = getpass.getpass('Database password (not shown, not stored): ')
    os.environ.setdefault('GOOGLE_API_KEY', 'not-used')  # app.py wants one; nothing here calls Google

    if args.apply:
        apply_plan(args.apply)
    else:
        make_plan(Path(args.out).expanduser())


if __name__ == '__main__':
    main()
