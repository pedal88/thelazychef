"""Make one v2 recipe from the command line, into the database the app is configured for.

    python scripts/generate_v2.py --idea "Spaghetti carbonara for four"
    python scripts/generate_v2.py --text recipe.txt
    python scripts/generate_v2.py --show 123          # the saved recipe as v2 JSON

Runs both rounds with Claude (ANTHROPIC_API_KEY) and saves the result as a
draft. Point DATABASE_URL at a local database: this writes a recipe. Costs
about USD 0.15 per recipe.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv  # noqa: E402

load_dotenv()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument('--idea', help='a short description of the dish')
    src.add_argument('--text', help='a file with a recipe as text')
    src.add_argument('--show', type=int, help='print a saved recipe as v2 JSON')
    ap.add_argument('--language', default='English', help='language for recipes made from an idea')
    args = ap.parse_args(argv)

    from app import app
    from database.models import Recipe, db
    from services.recipe_v2.store import to_v2

    with app.app_context():
        if args.show:
            print(json.dumps(to_v2(db.session.get(Recipe, args.show)), ensure_ascii=False, indent=2))
            return
        from services.recipe_v2.generate import create_recipe

        if args.idea:
            recipe, report = create_recipe('idea', args.idea, language=args.language)
        else:
            with open(args.text, encoding='utf-8') as f:
                recipe, report = create_recipe('text', f.read())
        print(json.dumps(report, ensure_ascii=False, indent=2))
        print(f'Recipe {recipe.id}: {recipe.title} ({"valid" if report["valid"] else "invalid, flagged"})')


if __name__ == '__main__':
    main()
