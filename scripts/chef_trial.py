"""The same dishes by each chef, to see whether the philosophies differ enough (RECIPE_MODEL_V2.md, "Kokker og innstillinger").

    DATABASE_URL=<local database> python scripts/chef_trial.py [--run <dir>] [--language nb]

Makes every dish in DISHES with every chef in CHEFS, plus the settings in EXTRA, as v2 drafts in the database
DATABASE_URL points to, which should be a local one. Read them side by side without the chef's name: if you
cannot tell which chef made which, the philosophies are too vague. The recipe ids and costs go to
~/promptlab-runs/chefs-<time>/trial.json; resumable with --run.

Needs ANTHROPIC_API_KEY. About USD 0.4 a recipe.
"""
import argparse
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
os.environ.setdefault('DB_BACKEND', 'local')
os.environ.setdefault('GOOGLE_API_KEY', 'not-used')
os.environ.setdefault('SECRET_KEY', 'chef-trial')

from promptlab.run import RUNS_DIR  # noqa: E402

DISHES = ['Lasagne for fire', 'Kylling tikka masala for fire', 'Laks med poteter og grønnsaker for fire']
CHEFS = ['the_classicist', 'the_smart_cook', 'the_minimalist']
EXTRA = [('Lasagne for fire', 'the_minimalist', ['vegetarian']),
         ('Kylling tikka masala for fire', 'the_smart_cook', ['low_carb', 'kid_friendly'])]


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--run', type=Path)
    p.add_argument('--language', default='nb')
    p.add_argument('--workers', type=int, default=3)
    args = p.parse_args()
    run = args.run or RUNS_DIR / f"chefs-{datetime.datetime.now():%Y%m%d-%H%M}"
    run.mkdir(parents=True, exist_ok=True)
    print(f'Run: {run}')
    path = run / 'trial.json'
    done = json.loads(path.read_text()) if path.exists() else []
    jobs = [(d, c, []) for d in DISHES for c in CHEFS] + EXTRA
    todo = [j for j in jobs if not any((r['dish'], r['chef'], r['settings']) == (j[0], j[1], j[2]) for r in done)]
    print(f'{len(todo)} of {len(jobs)} recipes to make')

    from app import app
    from services.recipe_v2.generate import create_recipe

    def work(job):
        dish, chef, settings = job
        with app.app_context():
            recipe, report = create_recipe('idea', dish, chef_id=chef, language=args.language, settings=settings)
            return {'dish': dish, 'chef': chef, 'settings': settings, 'recipe_id': recipe.id,
                    'cost_usd': report['cost_usd'], 'notes': report['persona_notes'], 'valid': report['valid']}

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        for result in pool.map(work, todo):
            done.append(result)
            path.write_text(json.dumps(done, indent=2, ensure_ascii=False))
            print(f"  {result['dish']} · {result['chef']} {'+'.join(result['settings'])}: recipe {result['recipe_id']}, "
                  f"USD {result['cost_usd']:.2f}{', ' + str(len(result['notes'])) + ' broken rules' if result['notes'] else ''}", flush=True)
    print(f"Cost: about USD {sum(r['cost_usd'] for r in done):.2f}")


if __name__ == '__main__':
    main()
