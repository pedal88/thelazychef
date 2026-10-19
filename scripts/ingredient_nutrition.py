"""Nutrition for active ingredients that have none, as a data migration.

    python scripts/ingredient_nutrition.py export                    # ingredients without nutrition, from production (read only)
    python scripts/ingredient_nutrition.py estimate --input <csv>    # new run in ~/promptlab-runs/nutrition-<time>
    python scripts/ingredient_nutrition.py apply --run <dir>         # writes the migration

estimate asks Claude for values per 100 g, from USDA FoodData Central where the
food is there, and checks that the energy fits the macros. Look through
check.txt before apply. The migration only fills ingredients that still have
no nutrition, marks them data_source 'ai_estimate', and downgrade restores the
old data_source and empties the values again.

estimate needs ANTHROPIC_API_KEY and costs a few cents. export needs gcloud logged in.
"""
import argparse
import csv
import datetime
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv()

from promptlab.run import RUNS_DIR  # noqa: E402

PROJECT, INSTANCE, DATABASE = 'thelazychefai-prod', 'lazy-chef-db-eu', 'lazy-chef-db'
EXPORT_BUCKET = 'gs://thelazychef-ops-exports'
COLUMNS = ['id', 'food_id', 'name', 'main_category', 'sub_category', 'default_unit', 'data_source']
CHUNK = 25
NUTRIENTS = ['calories', 'protein', 'fat', 'fat_saturated', 'carbs', 'sugar', 'fiber',
             'sodium_mg', 'cholesterol_mg', 'calcium_mg', 'potassium_mg']
# nutrient: ingredient column
FIELDS = {'calories': 'calories_per_100g', 'protein': 'protein_per_100g', 'fat': 'fat_per_100g',
          'fat_saturated': 'fat_saturated_per_100g', 'carbs': 'carbs_per_100g', 'sugar': 'sugar_per_100g',
          'fiber': 'fiber_per_100g', 'sodium_mg': 'sodium_mg_per_100g', 'cholesterol_mg': 'cholesterol_mg_per_100g',
          'calcium_mg': 'calcium_mg_per_100g', 'potassium_mg': 'potassium_mg_per_100g'}

SYSTEM = """You give nutrition data for pantry ingredients in a recipe app, as sold and used in recipes.
For each ingredient:
- Values per 100 g of the ingredient as sold (dry rice, dry lentils, the paste, the liquid stock as used, not a cube or powder unless the name says so).
- Use USDA FoodData Central values where the food is there, and say which entry in "basis". Otherwise a careful estimate from similar products, and say so in "basis".
- unit: "ml" for liquids usually measured by volume (stock, wine, sauces poured by the spoon), otherwise "g". grams_per_ml is the density for ml (1.0 for water-like liquids), and 1 for g.
- calories in kcal; protein, fat, fat_saturated, carbs, sugar and fiber in g; sodium, cholesterol, calcium and potassium in mg. Never null: use 0 where there is none.
- alcohol_g: grams of alcohol per 100 g (0 for most foods), so the energy can be checked."""

SCHEMA = {
    'type': 'object', 'additionalProperties': False, 'required': ['items'],
    'properties': {'items': {'type': 'array', 'items': {
        'type': 'object', 'additionalProperties': False,
        'required': ['food_id', 'unit', 'grams_per_ml', 'alcohol_g', 'basis'] + NUTRIENTS,
        'properties': dict({'food_id': {'type': 'string'}, 'unit': {'type': 'string', 'enum': ['g', 'ml']},
                            'grams_per_ml': {'type': 'number'}, 'alcohol_g': {'type': 'number'},
                            'basis': {'type': 'string'}}, **{n: {'type': 'number'} for n in NUTRIENTS})}}},
}


def export(out):
    """Active ingredients without nutrition, via a Cloud SQL CSV export (no DB password)."""
    stamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
    remote = f'{EXPORT_BUCKET}/nutrition-{stamp}.csv'
    query = (f"SELECT {', '.join(COLUMNS)} FROM ingredient "
             "WHERE status = 'active' AND calories_per_100g IS NULL ORDER BY id")
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


def read_csv(path):
    with open(path, newline='', encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        for k, v in r.items():
            if v in ('', '\\N'):
                r[k] = None
    return rows


def problems(item):
    """What looks wrong: energy that does not fit the macros, parts larger than the whole."""
    out = []
    expected = 4 * item['protein'] + 4 * item['carbs'] + 9 * item['fat'] + 7 * item['alcohol_g']
    if max(item['calories'], expected) > 20 and abs(item['calories'] - expected) > 0.2 * max(item['calories'], expected):
        out.append(f"energy {item['calories']:.0f} kcal, macros give {expected:.0f}")
    if item['protein'] + item['fat'] + item['carbs'] + item['alcohol_g'] > 102:
        out.append('macros over 100 g')
    if item['fat_saturated'] > item['fat'] + 0.1 or item['sugar'] > item['carbs'] + 0.1:
        out.append('a part is larger than its whole')
    if any(item[n] < 0 for n in NUTRIENTS):
        out.append('negative value')
    return out


def estimate(run, rows, call=None):
    from services.ai_models import RECIPE_V2_EFFORT, RECIPE_V2_MODEL
    from services.recipe_v2 import claude

    call = call or claude.call
    path = run / 'nutrition.json'
    done = json.loads(path.read_text()) if path.exists() else {}
    cost = 0
    for i in range(0, len(rows), CHUNK):
        chunk = [r for r in rows[i:i + CHUNK] if r['food_id'] not in done]
        if not chunk:
            continue
        user = 'Ingredients (food_id | name | category / sub category):\n' + '\n'.join(
            f"{r['food_id']} | {r['name']} | {r.get('main_category') or ''} / {r.get('sub_category') or ''}" for r in chunk)
        msg, usage = call(RECIPE_V2_MODEL, RECIPE_V2_EFFORT, [{'role': 'user', 'content': user}], system=SYSTEM, schema=SCHEMA)
        if msg.stop_reason in ('refusal', 'max_tokens'):
            raise RuntimeError(f'stop_reason {msg.stop_reason}')
        cost += usage.get('cost_usd', 0)
        asked = {r['food_id'] for r in chunk}
        for item in json.loads(claude.text_of(msg))['items']:
            if item['food_id'] in asked:
                done[item['food_id']] = item
        path.write_text(json.dumps(done, indent=2, ensure_ascii=False))
        print(f'  {len(done)} of {len(rows)}', flush=True)
    names = {r['food_id']: r['name'] for r in rows}
    lines = []
    for fid, item in sorted(done.items()):
        warn = problems(item)
        lines.append(f"{'!! ' if warn else '   '}{names.get(fid, fid):28} {item['unit']:2} {item['calories']:6.0f} kcal  "
                     f"P {item['protein']:5.1f}  F {item['fat']:5.1f}  C {item['carbs']:5.1f}  Na {item['sodium_mg']:6.0f} mg  "
                     f"{item['basis']}" + (f"\n      {'; '.join(warn)}" if warn else ''))
    (run / 'check.txt').write_text('\n'.join(lines) + '\n')
    missing = [r['name'] for r in rows if r['food_id'] not in done]
    print('\n'.join(lines))
    if missing:
        print(f'Missing: {", ".join(missing)}. Run estimate --run again.')
    print(f'Cost: about USD {cost:.2f}')
    return done


MIGRATION = '''"""ingredient nutrition {run}

Nutrition per 100 g for {n} active ingredients that had none, estimated by
Claude from USDA FoodData Central where the food is there (run {run}).
Only ingredients that still have no nutrition are filled. They get
data_source 'ai_estimate', and default_unit and average_g_per_unit (grams per
ml for liquids, 1 for g).

Downgrade empties the values again and restores default_unit and data_source.

Made by scripts/ingredient_nutrition.py apply.

Revision ID: {revision}
Revises: {down}
Create Date: {date}

"""
from alembic import op
import sqlalchemy as sa


revision = '{revision}'
down_revision = '{down}'
branch_labels = None
depends_on = None

FIELDS = {fields}
# food_id: (default_unit, average_g_per_unit, {{nutrient: value}}, (old default_unit, old data_source))
VALUES = {values}


def upgrade():
    conn = op.get_bind()
    sets = ', '.join(f'{{column}} = :{{column}}' for column in FIELDS.values())
    for fid, (unit, grams, values, _) in VALUES.items():
        params = {{FIELDS[k]: v for k, v in values.items()}}
        conn.execute(sa.text(f"UPDATE ingredient SET {{sets}}, default_unit = :unit, average_g_per_unit = :grams, "
                             "data_source = 'ai_estimate' WHERE food_id = :fid AND calories_per_100g IS NULL"),
                     dict(params, unit=unit, grams=grams, fid=fid))


def downgrade():
    conn = op.get_bind()
    sets = ', '.join(f'{{column}} = NULL' for column in FIELDS.values())
    for fid, (_, _, _, (unit, source)) in VALUES.items():
        conn.execute(sa.text(f"UPDATE ingredient SET {{sets}}, average_g_per_unit = NULL, default_unit = :unit, "
                             "data_source = :source WHERE food_id = :fid AND data_source = 'ai_estimate'"),
                     dict(unit=unit, source=source, fid=fid))
'''


def apply(run, rows, versions=ROOT / 'migrations' / 'versions', down_revision=None):
    import pprint
    import uuid

    sys.path.insert(0, str(ROOT / 'scripts'))
    from pantry_review import head_revision

    done = json.loads((run / 'nutrition.json').read_text())
    values = {}
    for r in rows:
        item = done.get(r['food_id'])
        if not item:
            continue
        grams = round(item['grams_per_ml'], 3) if item['unit'] == 'ml' else 1.0
        values[r['food_id']] = (item['unit'], grams, {n: round(item[n], 2) for n in NUTRIENTS},
                                (r.get('default_unit') or 'g', r.get('data_source') or 'placeholder'))
    revision = uuid.uuid4().hex[:12]
    text = MIGRATION.format(run=run.name, n=len(values), revision=revision, down=down_revision or head_revision(),
                            date=datetime.date.today().isoformat(),
                            fields=pprint.pformat(FIELDS, width=110), values=pprint.pformat(values, width=110))
    path = versions / f'{revision}_ingredient_nutrition_{run.name.replace("-", "_")}.py'
    path.write_text(text)
    return path


def main(argv=None):
    ap = argparse.ArgumentParser(prog='python scripts/ingredient_nutrition.py')
    sub = ap.add_subparsers(dest='command', required=True)
    p = sub.add_parser('export', help='active ingredients without nutrition, from production')
    p.add_argument('--out', type=Path, default=RUNS_DIR / f"nutrition-missing-{datetime.date.today()}.csv")
    p = sub.add_parser('estimate', help='estimate nutrition (new run with --input, continue with --run)')
    p.add_argument('--input', type=Path)
    p.add_argument('--run', type=Path)
    p = sub.add_parser('apply', help='write the data migration')
    p.add_argument('--run', type=Path, required=True)
    args = ap.parse_args(argv)

    if args.command == 'export':
        print(export(args.out))
    elif args.command == 'estimate':
        if not args.input and not args.run:
            raise SystemExit('Give --input (a CSV from export) or --run')
        run = args.run or RUNS_DIR / f"nutrition-{datetime.datetime.now():%Y%m%d-%H%M}"
        run.mkdir(parents=True, exist_ok=True)
        if args.input:
            (run / 'ingredients.csv').write_bytes(args.input.read_bytes())
        estimate(run, read_csv(run / 'ingredients.csv'))
        print(f'Check {run}/check.txt, then: python scripts/ingredient_nutrition.py apply --run {run}')
    else:
        print(apply(args.run, read_csv(args.run / 'ingredients.csv')))


if __name__ == '__main__':
    main()
