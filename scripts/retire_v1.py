"""Retire the v1 recipes (27.10.2026): export them as lines for the batch page, then archive them.

Three steps, run from the repo root against production:

1. Export (read only). Every recipe with schema_version 1 becomes a line in the batch format of /new-recipe/v2/batch
   (services/recipe_v2/batch.py): the idea, the chef and the settings. A recipe made from a link (TikTok, a web
   page) is its link, with its title as a note above it, so making it again starts from the same source. Approved
   recipes first; drafts and rejected ones follow as notes (#), to make again only if wanted. The transaction is
   read only on Postgres and rolled back; nothing is written.

       DB_BACKEND=cloudsql INSTANCE_CONNECTION_NAME=... DB_USER=... DB_NAME=... ./venv/bin/python -m scripts.retire_v1

   Out (outside the repo): ~/promptlab-runs/v1-retire/v1-recipes.md, the lines, and plan.json, each recipe's id,
   title and status, which the next two steps read.

2. Archive (writes). status becomes 'archived' for the recipes in the plan, if they are still v1 and still have the
   status the plan says; the rest are skipped and listed. One transaction. Nothing is deleted: the lines, steps,
   images, saves and collections stay, and archived recipes are shown nowhere.

       ... ./venv/bin/python -m scripts.retire_v1 --archive ~/promptlab-runs/v1-retire/plan.json

3. Restore, if needed: each archived recipe in the plan gets its old status back.

       ... ./venv/bin/python -m scripts.retire_v1 --restore ~/promptlab-runs/v1-retire/plan.json
"""
import argparse
import getpass
import json
import os
from pathlib import Path

# The chefs the batch page knows (data/agents/chefs.json with v2 rules), and what the old ones become
CHEFS = {'the_classicist': 'classicist', 'the_smart_cook': 'smart', 'the_minimalist': 'minimalist',
         'french_classic': 'classicist', 'family_cook': 'smart', 'low_carb_chef': 'smart', 'the_green_chef': 'smart',
         'speezy_gonzales': 'minimalist'}
# The old chefs whose point was a setting
CHEF_SETTINGS = {'family_cook': ['kid'], 'low_carb_chef': ['low carb'], 'the_green_chef': ['vegetarian']}
DIET_SETTINGS = {'vegetarian': 'vegetarian', 'vegan': 'vegetarian', 'keto': 'low carb'}
IDEA_MAX = 200


def is_link(text):
    return (text or '').strip().lower().startswith(('http://', 'https://'))


def line_of(r):
    """The batch line for one v1 recipe, and a note above it when the line is a link. r: a dict from the database."""
    settings = list(CHEF_SETTINGS.get(r['chef_id'] or '', []))
    for d in r['diets']:
        s = DIET_SETTINGS.get(d)
        if s and s not in settings:
            settings.append(s)
    if is_link(r['source']):
        note, idea = f"# {r['title']}", r['source'].strip()
    else:
        note = None
        idea = r['title'].strip()
        if r['cuisine'] and r['cuisine'].lower() not in idea.lower() and r['cuisine'].lower() != 'other':
            idea += f", {r['cuisine']}"
        idea += f", serves {r['servings'] or 4}"
        idea = idea[:IDEA_MAX]
    parts = [idea, CHEFS.get(r['chef_id'] or '', '')]
    if settings:
        parts.append(', '.join(settings))
    line = ' | '.join(parts).rstrip(' |')
    return note, line


def markdown(rows):
    """The md file: approved recipes as lines to paste, the others as notes."""
    approved = [r for r in rows if r['status'] == 'approved']
    others = [r for r in rows if r['status'] != 'approved']
    md = ['# The Lazy Chef: v1 recipes, retired 27.10.2026', '',
          f'{len(rows)} recipes in the old model ({len(approved)} approved), archived and no longer shown. To make one '
          'again in model v2, paste its line on /new-recipe/v2/batch (Admin, New Recipe, Batch). Choose the language '
          'on the page. A line is the idea, the chef and the settings; a recipe made from a link is its link. Lines '
          'starting with # are skipped, so the drafts below are only made if you remove the #.', '',
          '## Approved', '', '```']
    for r in approved:
        note, line = line_of(r)
        if note:
            md.append(note)
        md.append(line)
    md += ['```', '', '## Drafts and rejected', '', '```']
    for r in others:
        note, line = line_of(r)
        md.append(f"# [{r['status']}] {line}" + (f"  ({note[2:]})" if note else ''))
    md += ['```', '']
    return '\n'.join(md)


def export(out):
    from sqlalchemy import text
    from app import app, db
    from database.models import Recipe

    with app.app_context():
        conn = db.session.connection()
        if conn.dialect.name == 'postgresql':
            conn.execute(text('SET TRANSACTION READ ONLY'))
        recipes = db.session.execute(db.select(Recipe).where(Recipe.schema_version != 2).order_by(Recipe.id)).scalars().all()
        rows = [{'id': r.id, 'title': r.title, 'status': r.status, 'cuisine': r.cuisine, 'chef_id': r.chef_id,
                 'servings': r.base_servings, 'source': r.source_input, 'diets': r.diets_list} for r in recipes]
        db.session.rollback()

    out.mkdir(parents=True, exist_ok=True)
    (out / 'v1-recipes.md').write_text(markdown(rows))
    (out / 'plan.json').write_text(json.dumps([{k: r[k] for k in ('id', 'title', 'status')} for r in rows], ensure_ascii=False, indent=1))
    by_status = {}
    for r in rows:
        by_status[r['status']] = by_status.get(r['status'], 0) + 1
    print(f'v1 recipes: {len(rows)} ' + ', '.join(f'{k} {v}' for k, v in sorted(by_status.items())))
    print(f"  from a link: {sum(1 for r in rows if is_link(r['source']))}")
    print(f"Lines: {out / 'v1-recipes.md'}\nPlan: {out / 'plan.json'}")


def change(path, restore=False):
    from app import app, db
    from database.models import Recipe

    plan = json.loads(Path(path).expanduser().read_text())
    done, skipped = 0, []
    with app.app_context():
        for p in plan:
            r = db.session.get(Recipe, p['id'])
            now, then = ('archived', p['status']) if restore else (p['status'], 'archived')
            if r is None or r.schema_version == 2 or r.status != now:
                skipped.append(p)
                continue
            r.status = then
            done += 1
        db.session.commit()
    print(f"{'Restored' if restore else 'Archived'}: {done} recipes. Skipped (changed since the plan): {len(skipped)}")
    for p in skipped:
        print(f"  {p['id']} {p['title']}")


def main():
    ap = argparse.ArgumentParser(description='Retire the v1 recipes: export (read only), archive, restore.')
    ap.add_argument('--out', default=str(Path.home() / 'promptlab-runs' / 'v1-retire'))
    ap.add_argument('--archive', metavar='PLAN', help='archive the recipes in the plan')
    ap.add_argument('--restore', metavar='PLAN', help='give the archived recipes in the plan their old status back')
    args = ap.parse_args()

    if os.getenv('DB_BACKEND', 'local').lower() == 'cloudsql' and not os.getenv('DB_PASS'):
        os.environ['DB_PASS'] = getpass.getpass('Database password (not shown, not stored): ')
    os.environ.setdefault('GOOGLE_API_KEY', 'not-used')  # app.py wants one; nothing here calls Google

    if args.archive:
        change(args.archive)
    elif args.restore:
        change(args.restore, restore=True)
    else:
        export(Path(args.out).expanduser())


if __name__ == '__main__':
    main()
