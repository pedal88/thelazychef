"""A read-only report on the measures in the saved recipes' free text (a step's text, short and done_when, the
chef's note and the yield): how many the US view converts (services/measures.localize_text), and which it cannot:
written in US units ("2 cups", "350°F") or as degrees with no scale ("200°"), or metric but not as number, space,
unit ("et par dl", "en halv liter"), which a US reader would see as written.

It only reads: on Postgres the transaction is set to read only before the first query, and it is rolled back at
the end. Nothing is written to the database, and nothing costs money.

Run against production from the repo root. The password is asked for when DB_PASS is not set; it is not shown,
printed or stored:

    DB_BACKEND=cloudsql INSTANCE_CONNECTION_NAME=thelazychefai-prod:europe-north2:lazy-chef-db-eu \\
    DB_USER=<user> DB_NAME=<name> ./venv/bin/python -m scripts.units_report

The texts that cannot be converted are written outside the repo (the repo is public, they are recipe content), by
default to ~/promptlab-runs/units_report.json. The printed summary has only ids, fields and the measures found, so it
can be pasted back. A recipe in the list is fixed by editing the text, or by making it again.
"""
import argparse
import collections
import getpass
import json
import os
from pathlib import Path


def main():
    ap = argparse.ArgumentParser(description='Read-only report on measures in the recipes\' free text.')
    ap.add_argument('--out', default=str(Path.home() / 'promptlab-runs' / 'units_report.json'))
    args = ap.parse_args()

    if os.getenv('DB_BACKEND', 'local').lower() == 'cloudsql' and not os.getenv('DB_PASS'):
        os.environ['DB_PASS'] = getpass.getpass('Database password (not shown, not stored): ')
    os.environ.setdefault('GOOGLE_API_KEY', 'not-used')  # app.py wants one; nothing here calls Google

    from sqlalchemy import text
    from app import app, db
    from services.measures import AMOUNT, LENGTH, TEMP, missed, unconverted

    with app.app_context():
        conn = db.session.connection()
        if conn.dialect.name == 'postgresql':
            conn.execute(text('SET TRANSACTION READ ONLY'))

        def q(sql):
            return [dict(r) for r in conn.execute(text(sql)).mappings().all()]

        recipes = q("""SELECT id, status, chef_note, yield_text FROM recipe WHERE schema_version = 2""")
        steps = q("""SELECT s.recipe_id, s.local_id, s.text, s.short, s.done_when
                     FROM recipe_step s JOIN recipe r ON r.id = s.recipe_id WHERE r.schema_version = 2""")
        db.session.rollback()  # nothing to keep, and nothing was written

    texts = [(r['id'], r['status'], key, r[key]) for r in recipes for key in ('chef_note', 'yield_text')]
    status = {r['id']: r['status'] for r in recipes}
    texts += [(s['recipe_id'], status.get(s['recipe_id']), f"{s['local_id']}.{key}", s[key])
              for s in steps for key in ('text', 'short', 'done_when')]

    converted = collections.Counter()
    problems = []
    for rid, st, field, value in texts:
        if not value:
            continue
        for kind, pattern in (('temperature', TEMP), ('length', LENGTH), ('amount', AMOUNT)):
            converted[kind] += len(pattern.findall(value))
        found = unconverted(value) + missed(value)
        if found:
            problems.append({'recipe_id': rid, 'status': st, 'field': field, 'found': found, 'text': value})

    out = Path(args.out).expanduser()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({'recipes': len(recipes), 'texts': len(texts), 'converted': converted,
                               'unconverted': problems}, ensure_ascii=False, indent=1), encoding='utf-8')

    print(f'{len(recipes)} v2 recipes, {len(texts)} free-text fields')
    print('Converted for US readers: ' + ', '.join(f'{n} {k}s' for k, n in converted.items()))
    print(f'{len(problems)} fields with measures the app cannot convert, '
          f'in {len({p["recipe_id"] for p in problems})} recipes:')
    for p in problems:
        print(f"  recipe {p['recipe_id']} ({p['status']}) {p['field']}: {', '.join(p['found'])}")
    print(f'The texts: {out}')


if __name__ == '__main__':
    main()
