"""A read-only report of saved v2 recipes, to review them before they are approved (27.10.2026).

For each recipe: the chef and settings, the flags it was saved with and the chef's rules checked again now (the
planner, the pantry and the rules may have changed since: Recalculate would give these), the time and hands-on
time from the planner of now, carbs a serving, the lines with their pantry match and state, and the steps with
their equipment. Nothing is written: on Postgres the transaction is read only and rolled back.

    DB_BACKEND=cloudsql INSTANCE_CONNECTION_NAME=... DB_USER=... DB_NAME=... ./venv/bin/python -m scripts.review_recipes --search "air fryer"
    ... -m scripts.review_recipes --ids 340,341,342

The report goes outside the repo (it holds recipe content): ~/promptlab-runs/recipe-review/report.md.
"""
import argparse
import getpass
import os
from pathlib import Path


def fmt_line(line):
    from services.recipe_v2 import states

    amount = '' if line.amount is None else (f'{line.amount:g}' + (f' {line.unit}' if line.unit and line.unit != 'piece' else ''))
    state = ' '.join(x for x in (states.word(line.state, line.grade, 'en'), f'[{line.variety}]' if line.variety else '') if x)
    pantry = f'{line.ingredient.name} ({line.ingredient.food_id})' if line.ingredient else '**MISSING in the pantry**'
    return f"| {line.name} | {amount or 'to taste'} | {state} | {line.prep_style or ''} | {pantry} |"


def review(recipe):
    """The section for one recipe. Recalculates in the session (not saved) to see the flags of now."""
    from database.models import db
    from services.recipe_v2 import generate, nutrition, persona
    from services.recipe_v2.planner import plan_v2
    from services.recipe_v2.store import to_v2

    saved = [e for e in recipe.validation_errors or []]
    with db.session.no_autoflush:
        generate.recalculate(recipe)  # in memory only: the transaction is rolled back
        now = [e for e in recipe.validation_errors or []]
        p = persona.spec_for(recipe)
        rules = (p or {}).get('constraints') or {}
        v2 = to_v2(recipe)
        sch = plan_v2(v2) if v2['steps'] else {'T': 0, 'A': 0}
        per = nutrition.per_serving(recipe)
    md = [f"## {recipe.title} (#{recipe.id}, {recipe.status})", '',
          f"- Chef: {(p or {}).get('name') or recipe.chef_id or '-'}; settings: {', '.join(recipe.settings or []) or '-'}; "
          f"language: {recipe.language}; cuisine: {recipe.cuisine or '-'}; meal types: {', '.join(recipe.meal_types_list) or '-'}",
          f"- Time now: {sch['T']} min total, {sch['A']} min hands-on (saved: {recipe.prep_time_mins} min); "
          f"chef allows {rules.get('max_total_minutes') or '-'} total, {rules.get('max_active_minutes') or '-'} hands-on",
          f"- Carbs a serving: {per['carbs'] if per else 'no nutrition'} g (low carb allows 20); kcal {per['kcal'] if per else '-'}",
          f"- Flags saved: {'; '.join(e.get('message', '') for e in saved) or 'none'}",
          f"- Flags now: {'; '.join(e.get('message', '') for e in now) or 'none'}", '',
          '| Line | Amount | State | Note | Pantry |', '|---|---|---|---|---|']
    md += [fmt_line(line) for line in recipe.lines]
    md += ['', '| # | Phase | Step | Method | Equipment | Temp | Active + standing |', '|---|---|---|---|---|---|---|']
    for n, s in enumerate(recipe.steps, 1):
        md.append(f"| {n} | {s.phase} | {s.short} | {s.method} | {', '.join(s.equipment or [])} | {s.temp_c or ''} | "
                  f"{s.active_minutes} + {s.passive_minutes} |")
    return md + ['']


def main():
    ap = argparse.ArgumentParser(description='A read-only report of saved v2 recipes.')
    ap.add_argument('--search', help='recipes whose idea (source_input) or title contains this')
    ap.add_argument('--ids', help='comma-separated recipe ids')
    ap.add_argument('--out', default=str(Path.home() / 'promptlab-runs' / 'recipe-review' / 'report.md'))
    args = ap.parse_args()
    if not args.search and not args.ids:
        ap.error('give --search or --ids')

    if os.getenv('DB_BACKEND', 'local').lower() == 'cloudsql' and not os.getenv('DB_PASS'):
        os.environ['DB_PASS'] = getpass.getpass('Database password (not shown, not stored): ')
    os.environ.setdefault('GOOGLE_API_KEY', 'not-used')  # app.py wants one; nothing here calls Google

    from sqlalchemy import or_, text
    from app import app, db
    from database.models import Recipe

    with app.app_context():
        conn = db.session.connection()
        if conn.dialect.name == 'postgresql':
            conn.execute(text('SET TRANSACTION READ ONLY'))
        stmt = db.select(Recipe).where(Recipe.schema_version == 2).order_by(Recipe.id)
        if args.ids:
            stmt = stmt.where(Recipe.id.in_([int(x) for x in args.ids.split(',') if x.strip()]))
        if args.search:
            stmt = stmt.where(or_(Recipe.source_input.ilike(f'%{args.search}%'), Recipe.title.ilike(f'%{args.search}%')))
        recipes = db.session.execute(stmt).scalars().all()
        ids = [r.id for r in recipes]
        md = [f'# Recipe review: {len(recipes)} recipes', '']
        for r in recipes:
            md += review(r)
        db.session.rollback()  # nothing to keep, and nothing was written

    out = Path(args.out).expanduser()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text('\n'.join(md))
    print(f'{len(ids)} recipes: {", ".join(map(str, ids))}\nReport: {out}')


if __name__ == '__main__':
    main()
