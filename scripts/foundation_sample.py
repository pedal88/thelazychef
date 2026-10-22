"""A sample of the dishes Norwegian home cooks make, to propose the foundation pantry (RECIPE_MODEL_V2.md,
"Basisvarer og grunnlager").

    python scripts/foundation_sample.py sample              # new run in ~/promptlab-runs/foundation-<time>
    python scripts/foundation_sample.py sample --run <dir>  # resume: cuisines already done are skipped
    python scripts/foundation_sample.py analyze --run <dir> # candidates.json: counts, coverage, cuisine keys

sample asks Claude, per cuisine, for the dishes made most often in Norwegian homes and the ingredients bought for
them, named as in the pantry where one fits. The cuisines and how many dishes each gets are the weights decided
22.10.2026: a cuisine counts as much as it is cooked here. analyze counts each pantry ingredient over the dishes
(weighted by how common the dish is), shows how much of all the ingredient lines the top N cover besides the
staples, and marks cuisine keys: ingredients in many of one cuisine's dishes but few others.

The pantry is read from DATABASE_URL (read only). Needs ANTHROPIC_API_KEY. Costs about USD 2-3 for sample.
The current recipes are not used: the app is still in its test phase and they are not representative.
"""
import argparse
import collections
import datetime
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

env = Environment(loader=FileSystemLoader(str(ROOT / 'data' / 'prompts')))

# cuisine: (dishes in the sample, what it covers)
CUISINES = {
    'Nordic': (40, 'Norwegian first, and the Swedish and Danish dishes common in Norway'),
    'Italian': (35, 'pasta, pizza, risotto and the rest, as cooked in Norway'),
    'Mexican & Tex-Mex': (30, 'including Norwegian Friday tacos and other Tex-Mex'),
    'American': (25, 'burgers, barbecue, comfort food, baking and breakfast'),
    'Indian': (20, 'curries, dals and breads as cooked at home'),
    'Thai': (20, 'curries, stir-fries, noodles and salads'),
    'Chinese': (20, 'stir-fries, noodles, rice dishes and dumplings'),
    'Middle Eastern': (20, 'Levantine, Turkish and Persian: hummus, falafel, shawarma, shakshuka'),
    'Japanese': (15, 'teriyaki, ramen, sushi bowls, curry and the like'),
    'French': (15, 'bistro and home dishes, sauces and baking'),
    'Greek': (10, 'everyday Greek home food'),
    'Korean': (10, 'bibimbap, bulgogi, fried chicken, kimchi dishes'),
    'Eastern European': (10, 'Polish first: pierogi, bigos, soups'),
}
KEY_SHARE = 0.3      # in at least this share of one cuisine's dishes ...
KEY_CUISINES = 2     # ... and in at most this many cuisines: a cuisine key
SCHEMA = {
    'type': 'object', 'additionalProperties': False, 'required': ['dishes'],
    'properties': {'dishes': {'type': 'array', 'items': {
        'type': 'object', 'additionalProperties': False, 'required': ['name', 'common', 'ingredients'],
        'properties': {
            'name': {'type': 'string'}, 'common': {'type': 'integer', 'enum': [1, 2, 3]},
            'ingredients': {'type': 'array', 'items': {
                'type': 'object', 'additionalProperties': False, 'required': ['pantry', 'new', 'role', 'alternatives'],
                'properties': {'pantry': {'type': 'string'}, 'new': {'type': 'boolean'},
                               'role': {'type': 'string', 'enum': ['defining', 'choice']},
                               'alternatives': {'type': 'array', 'items': {'type': 'string'}}}}}}}}},
}


def load(run, name, default):
    path = run / name
    return json.loads(path.read_text()) if path.exists() else default


def save(run, name, data):
    tmp = run / (name + '.tmp')
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    tmp.replace(run / name)


def read_pantry():
    """Active ingredients and aliases from DATABASE_URL: {lowercase name or alias: ingredient row}."""
    import sqlalchemy as sa

    engine = sa.create_engine(os.environ['DATABASE_URL'])
    with engine.connect() as conn:
        rows = [dict(r._mapping) for r in conn.execute(sa.text(
            "SELECT id, name, tier, main_category, sub_category, image_url FROM ingredient "
            "WHERE status = 'active' ORDER BY name"))]
        aliases = conn.execute(sa.text('SELECT name, ingredient_id FROM ingredient_alias')).all()
    by_id = {r['id']: r for r in rows}
    names = {r['name'].lower(): r for r in rows}
    for alias, iid in aliases:
        if iid in by_id:
            names.setdefault(alias.lower(), by_id[iid])
    return rows, names


def sample(run, call=None, workers=4):
    from services.ai_models import RECIPE_V2_EFFORT, RECIPE_V2_MODEL
    from services.recipe_v2 import claude

    rows, _ = read_pantry()
    save(run, 'pantry.json', rows)
    system = ('PANTRY (name), the ingredients The Lazy Chef knows:\n' + '\n'.join(r['name'] for r in rows))
    done = load(run, 'sample.json', {})
    todo = [c for c in CUISINES if c not in done]
    print(f'{len(todo)} of {len(CUISINES)} cuisines to sample')
    cost = []

    def work(cuisine):
        count, definition = CUISINES[cuisine]
        user = env.get_template('pantry/foundation_sample.jinja2').render(cuisine=cuisine, count=count, definition=definition)
        msg, usage = (call or claude.call)(RECIPE_V2_MODEL, RECIPE_V2_EFFORT, [{'role': 'user', 'content': user}],
                                           system=system, schema=SCHEMA)
        if msg.stop_reason in ('refusal', 'max_tokens'):
            raise RuntimeError(f'{cuisine}: stop_reason {msg.stop_reason}')
        cost.append(usage.get('cost_usd', 0))
        return cuisine, json.loads(claude.text_of(msg))['dishes']

    with ThreadPoolExecutor(max_workers=workers) as pool:
        for cuisine, dishes in pool.map(work, todo):
            done[cuisine] = dishes
            save(run, 'sample.json', done)
            print(f'  {cuisine}: {len(dishes)} dishes', flush=True)
    print(f'Cost: about USD {sum(cost):.2f}')


def analyze(run):
    """candidates.json: every ingredient in the sample with its weight, dishes, cuisines and role, ranked."""
    rows, names = read_pantry()
    data = load(run, 'sample.json', {})
    items = {}
    total = 0.0
    for cuisine, dishes in data.items():
        for dish in dishes:
            seen = set()
            for ing in dish['ingredients']:
                name = ing['pantry'].strip().lower()
                row = names.get(name)
                key = row['name'] if row else name
                if key in seen:
                    continue
                seen.add(key)
                total += dish['common']
                it = items.setdefault(key, {
                    'name': key, 'in_pantry': row is not None, 'tier': row['tier'] if row else None,
                    'category': row['main_category'] if row else None, 'image': row['image_url'] if row else None,
                    'weight': 0, 'dishes': 0, 'cuisines': collections.Counter(), 'defining': 0, 'choice': 0,
                    'alternatives': collections.Counter(), 'examples': []})
                it['weight'] += dish['common']
                it['dishes'] += 1
                it['cuisines'][cuisine] += 1
                it[ing['role']] += 1
                for alt in ing['alternatives']:
                    alt_row = names.get(alt.strip().lower())
                    it['alternatives'][alt_row['name'] if alt_row else alt.strip().lower()] += 1
                if len(it['examples']) < 6:
                    it['examples'].append(f"{dish['name']} ({cuisine})")
    sizes = {c: len(d) for c, d in data.items()}
    out = []
    for it in items.values():
        shares = {c: round(n / sizes[c], 2) for c, n in it['cuisines'].items()}
        it['key_for'] = [c for c, s in shares.items() if s >= KEY_SHARE] if len(shares) <= KEY_CUISINES else []
        it['cuisines'] = dict(it['cuisines'].most_common())
        it['shares'] = shares
        it['alternatives'] = [a for a, _ in it['alternatives'].most_common(4)]
        out.append(it)
    out.sort(key=lambda it: -it['weight'])
    staple_weight = sum(it['weight'] for it in out if it['tier'] == 'staple')
    rest = [it for it in out if it['tier'] != 'staple']
    coverage, acc = {}, staple_weight
    for n, it in enumerate(rest, 1):
        acc += it['weight']
        it['rank'] = n
        if n in (20, 40, 60, 80, 100, 120, 160, 200):
            coverage[n] = round(acc / total, 3)
    result = {'run': run.name, 'dishes': sum(sizes.values()), 'cuisines': sizes, 'lines_weight': total,
              'staples_cover': round(staple_weight / total, 3), 'coverage': coverage, 'items': out}
    save(run, 'candidates.json', result)
    print(f"{result['dishes']} dishes, {len(out)} ingredients ({sum(not it['in_pantry'] for it in out)} not in the pantry)")
    print(f"Staples cover {result['staples_cover']:.0%} of the ingredient lines; with the top N besides them:")
    for n, c in coverage.items():
        print(f'  top {n}: {c:.0%}')
    keys = [it for it in rest if it['key_for'] and it['rank'] > 60]
    print(f'{len(keys)} cuisine keys outside the top 60, e.g. ' + ', '.join(it['name'] for it in keys[:12]))
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('command', choices=('sample', 'analyze'))
    p.add_argument('--run', type=Path)
    args = p.parse_args()
    run = args.run or RUNS_DIR / f"foundation-{datetime.datetime.now():%Y%m%d-%H%M}"
    run.mkdir(parents=True, exist_ok=True)
    print(f'Run: {run}')
    if args.command == 'sample':
        sample(run)
    else:
        analyze(run)


if __name__ == '__main__':
    main()
