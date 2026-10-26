"""A read-only report on how ingredient states, verbs and methods are written today, and how the pantry is
organised, as input for the state catalog (decided 26.10.2026: state with groups and a fineness modifier,
variety on the recipe line, prep_style narrowed to a note).

It only reads: on Postgres the transaction is set to read only before the first query, and it is rolled back at
the end. Nothing is written to the database.

Run against production from the repo root. The password is asked for when DB_PASS is not set; it is not shown,
printed or stored:

    DB_BACKEND=cloudsql INSTANCE_CONNECTION_NAME=thelazychefai-prod:europe-north2:lazy-chef-db-eu \\
    DB_USER=<user> DB_NAME=<name> ./venv/bin/python -m scripts.report_ingredient_states

The report is written outside the repo (the repo is public, the report holds recipe content), by default to
~/promptlab-runs/ingredient_states_report.json, and a short summary is printed. --pantry-out also writes the active
pantry as [food_id, name] pairs, for scripts/compare_states.py --pantry.
"""
import argparse
import collections
import getpass
import json
import os
import re
from pathlib import Path

# Words that say how a product is sold rather than what is done to it in the recipe
FORM_WORDS = ('canned', 'tinned', 'frozen', 'fresh', 'dried', 'ground', 'smoked', 'powder', 'juice', 'sliced', 'whole',
              'hermetisk', 'frossen', 'frosne', 'fersk', 'tørket', 'malt', 'røkt', 'pulver')
SPLIT = re.compile(r'\s*(?:,|;|/|\(|\)|\bog\b|\band\b|\beller\b|\bor\b)\s*')


def norm(s):
    return re.sub(r'\s+', ' ', (s or '').strip().lower())


def top(counter, n, examples=None):
    out = []
    for key, count in counter.most_common(n):
        row = {'value': key, 'count': count}
        if examples is not None:
            row['examples'] = sorted(examples.get(key, []))[:4]
        out.append(row)
    return out


def main():
    ap = argparse.ArgumentParser(description='Read-only report on ingredient states, verbs, methods and the pantry.')
    ap.add_argument('--out', default=str(Path.home() / 'promptlab-runs' / 'ingredient_states_report.json'))
    ap.add_argument('--top', type=int, default=300, help='how many of each list to keep')
    ap.add_argument('--pantry-out', help='also write the active pantry here, as [food_id, name] pairs')
    args = ap.parse_args()

    if os.getenv('DB_BACKEND', 'local').lower() == 'cloudsql' and not os.getenv('DB_PASS'):
        os.environ['DB_PASS'] = getpass.getpass('Database password (not shown, not stored): ')
    os.environ.setdefault('GOOGLE_API_KEY', 'not-used')  # app.py wants one; nothing here calls Google

    from sqlalchemy import text
    from app import app, db

    with app.app_context():
        conn = db.session.connection()
        if conn.dialect.name == 'postgresql':
            conn.execute(text('SET TRANSACTION READ ONLY'))

        def q(sql):
            return [dict(r) for r in conn.execute(text(sql)).mappings().all()]

        recipes = q("""SELECT coalesce(schema_version, 1) AS version, coalesce(language, '?') AS language, status,
                              coalesce(cuisine, '') AS cuisine, count(*) AS n
                       FROM recipe GROUP BY 1, 2, 3, 4""")
        lines = q("""SELECT l.name, l.prep_style, l.cut, coalesce(r.language, '?') AS language,
                            i.name AS pantry_name, i.main_category, i.sub_category
                     FROM recipe_line l JOIN recipe r ON r.id = l.recipe_id
                     LEFT JOIN ingredient i ON i.id = l.ingredient_id""")
        steps = q("""SELECT s.method, s.verb, s.short, s.phase, coalesce(r.language, '?') AS language
                     FROM recipe_step s JOIN recipe r ON r.id = s.recipe_id""")
        v1_lines = q("""SELECT ri.prep_style, i.name AS pantry_name, i.main_category
                        FROM recipe_ingredient ri JOIN ingredient i ON i.id = ri.ingredient_id
                        JOIN recipe r ON r.id = ri.recipe_id WHERE coalesce(r.schema_version, 1) = 1""")
        pantry = q("""SELECT id, food_id, name, main_category, sub_category, tier, base_ingredient_id, status FROM ingredient""")
        db.session.rollback()  # nothing to keep, and nothing was written

    report = {'recipes': {}, 'v2_lines': {}, 'v2_steps': {}, 'v1_lines': {}, 'pantry': {}}

    # The recipes: how many of each version and language, and the cuisines (how representative the data is)
    by_version, cuisines = collections.Counter(), collections.Counter()
    for r in recipes:
        by_version[f"v{r['version']} {r['language']} {r['status']}"] += r['n']
        cuisines[f"v{r['version']} {r['cuisine'] or '?'}"] += r['n']
    report['recipes'] = {'by_version_language_status': top(by_version, 100), 'by_cuisine': top(cuisines, 100)}

    # v2 lines: prep_style and cut, alone, together, and the words prep_style is made of
    prep, prep_ex, cut, pairs, words, prep_no_cut = (collections.Counter(), collections.defaultdict(set), collections.Counter(),
                                                     collections.Counter(), collections.Counter(), collections.Counter())
    for line in lines:
        p, c = norm(line['prep_style']), line['cut'] or ''
        cut[c or '(none)'] += 1
        if p:
            prep[p] += 1
            prep_ex[p].add(line['pantry_name'] or line['name'])
            for w in filter(None, SPLIT.split(p)):
                words[w] += 1
            if not c:
                prep_no_cut[p] += 1
        if p or c:
            pairs[f'{c or "-"} | {p or "-"}'] += 1
    report['v2_lines'] = {
        'total': len(lines), 'with_prep_style': sum(prep.values()), 'with_cut': sum(v for k, v in cut.items() if k != '(none)'),
        'cut': top(cut, 50), 'prep_style': top(prep, args.top, prep_ex), 'prep_style_words': top(words, args.top),
        'prep_style_without_cut': top(prep_no_cut, args.top), 'cut_and_prep_style': top(pairs, args.top),
    }

    # v2 steps: the methods, and the verbs written for each
    methods, verbs, verbs_by_method = collections.Counter(), collections.Counter(), collections.defaultdict(collections.Counter)
    for s in steps:
        m, v = s['method'] or '(none)', norm(s['verb'])
        methods[m] += 1
        if v:
            verbs[f"{s['language']} {v}"] += 1
            verbs_by_method[m][v] += 1
    report['v2_steps'] = {
        'total': len(steps), 'method': top(methods, 100), 'verb': top(verbs, args.top),
        'verbs_by_method': {m: top(c, 12) for m, c in sorted(verbs_by_method.items())},
    }

    # v1 lines: prep_style only, but from the older and larger set of recipes
    v1, v1_ex = collections.Counter(), collections.defaultdict(set)
    for line in v1_lines:
        p = norm(line['prep_style'])
        if p:
            v1[p] += 1
            v1_ex[p].add(line['pantry_name'])
    report['v1_lines'] = {'total': len(v1_lines), 'with_prep_style': sum(v1.values()), 'prep_style': top(v1, args.top, v1_ex)}

    # The pantry: size, categories, tiers, variants, product forms and names that look like the same thing
    cats, tiers, forms, form_ex, dupes = (collections.Counter(), collections.Counter(), collections.Counter(),
                                          collections.defaultdict(list), collections.defaultdict(list))
    for i in pantry:
        cats[f"{i['main_category'] or '?'} / {i['sub_category'] or '?'}"] += 1
        tiers[i['tier'] or '(not reviewed)'] += 1
        low = norm(i['name'])
        for w in FORM_WORDS:
            if re.search(rf'\b{w}\b', low):
                forms[w] += 1
                form_ex[w].append(i['name'])
        key = ' '.join(sorted(re.sub(r'[^a-zæøå ]', ' ', re.sub(r'\(.*?\)', ' ', low)).split()))
        dupes[key].append(i['name'])
    report['pantry'] = {
        'total': len(pantry), 'active': sum(1 for i in pantry if (i['status'] or 'active') == 'active'),
        'with_base_ingredient': sum(1 for i in pantry if i['base_ingredient_id']),
        'tier': top(tiers, 20), 'category': top(cats, 200),
        'product_form_words': [{'value': w, 'count': n, 'examples': form_ex[w][:8]} for w, n in forms.most_common()],
        'possible_duplicates': [names for names in dupes.values() if len(names) > 1][:200],
    }

    if args.pantry_out:
        active = sorted([i['food_id'], i['name']] for i in pantry if (i['status'] or 'active') == 'active' and i['food_id'])
        Path(args.pantry_out).expanduser().write_text(json.dumps(active, ensure_ascii=False))
        print(f'Pantry: {len(active)} active ingredients to {args.pantry_out}')

    out = Path(args.out).expanduser()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2))

    print(f'Recipes: {sum(by_version.values())}  v2 lines: {len(lines)}  v2 steps: {len(steps)}  '
          f'v1 lines: {len(v1_lines)}  pantry: {len(pantry)}')
    print(f"v2 lines with prep_style: {report['v2_lines']['with_prep_style']}, with cut: {report['v2_lines']['with_cut']}")
    print('Most common prep_style (v2):', ', '.join(f"{r['value']} ({r['count']})" for r in report['v2_lines']['prep_style'][:15]))
    print('Most common prep_style (v1):', ', '.join(f"{r['value']} ({r['count']})" for r in report['v1_lines']['prep_style'][:15]))
    print(f"Possible duplicates in the pantry: {len(report['pantry']['possible_duplicates'])}")
    print(f'Report: {out}')


if __name__ == '__main__':
    main()
