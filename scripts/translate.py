"""Translate saved recipes and the pantry's names into Norwegian (services/recipe_v2/translate.py), and take a translation
away again. A recipe is translated by itself when it is approved (tasks.run_translation); this is for the rest.

Without --apply nothing is called and nothing is saved: it lists what would be translated, with an estimate of the cost.
With --apply it first gives the recipes' pantry items their Norwegian names where they have none, then translates each
recipe, committed on its own; about 0.06 USD a recipe on Opus (measured on five, 04.11.2026), about half that on Sonnet.
A recipe that already has a translation matching its words is left alone unless --force, which also names its pantry
items again. The originals and the translations go to ~/promptlab-runs/translate/<time>-<model>.json, and nothing shows
to anyone who has not chosen Norwegian.

--try calls Claude and writes the file but saves nothing, to compare models or read first; --from-file saves such a file
later without paying again, if the recipes' words have not changed.

    SSL_CERT_FILE=... DB_PASS=... DB_BACKEND=cloudsql ... ANTHROPIC_API_KEY=... ./venv/bin/python -m scripts.translate --ids 374,380
    ... -m scripts.translate --ids 374,380 --apply
    ... -m scripts.translate --approved --limit 20 --apply
    ... -m scripts.translate --pantry --apply          (every active pantry item without a Norwegian name)
    ... -m scripts.translate --remove --ids 374 --apply
    ... -m scripts.translate --ids 374,380 --force --try --model sonnet
    ... -m scripts.translate --from-file ~/promptlab-runs/translate/<file>.json --apply
"""
import argparse
import datetime
import getpass
import json
import os
from pathlib import Path

from scripts.fill_pantry import parse_ids

CHARS_PER_TOKEN = 3.5


def estimate(words):
    """USD for one recipe: its words in, about the same out, and the cached prompt. An estimate, printed as one."""
    from services.ai_models import TRANSLATE_MODEL
    from services.recipe_v2.claude import PRICES

    tokens = len(json.dumps(words, ensure_ascii=False)) / CHARS_PER_TOKEN
    price_in, price_out = PRICES[TRANSLATE_MODEL]
    return (tokens * price_in + tokens * 1.3 * price_out) / 1e6


def main():
    ap = argparse.ArgumentParser(description='Translate saved recipes and the pantry into Norwegian.')
    ap.add_argument('--ids', help='recipe ids: 337-360 or 337,340')
    ap.add_argument('--approved', action='store_true', help='the approved recipes without a translation, oldest first')
    ap.add_argument('--limit', type=int, help='at most this many recipes')
    ap.add_argument('--pantry', action='store_true', help='every active pantry item without a Norwegian name')
    ap.add_argument('--force', action='store_true', help='translate again what already has a translation')
    ap.add_argument('--remove', action='store_true', help='take away the translation of --ids')
    ap.add_argument('--apply', action='store_true', help='call Claude and save; without it only a list and an estimate')
    ap.add_argument('--try', dest='attempt', action='store_true', help='call Claude and write the file, save nothing')
    ap.add_argument('--model', choices=('sonnet', 'opus'), help='instead of TRANSLATE_MODEL')
    ap.add_argument('--from-file', help='save the translations in this file; calls nothing')
    args = ap.parse_args()
    if not (args.ids or args.approved or args.pantry or args.from_file):
        ap.error('give --ids, --approved, --pantry or --from-file')
    if args.attempt and args.apply:
        ap.error('--try saves nothing, so not with --apply')
    if args.remove and not args.ids:
        ap.error('--remove takes --ids')

    if os.getenv('DB_BACKEND', 'local').lower() == 'cloudsql' and not os.getenv('DB_PASS'):
        os.environ['DB_PASS'] = getpass.getpass('Database password (not shown, not stored): ')
    os.environ.setdefault('GOOGLE_API_KEY', 'not-used')  # app.py wants one; nothing here calls Google
    calls = (args.apply or args.attempt) and not args.remove and not args.from_file
    if calls and not os.getenv('ANTHROPIC_API_KEY'):
        ap.error('--apply and --try need ANTHROPIC_API_KEY')

    from app import app, db
    from database.models import Ingredient, Recipe, RecipeTranslation
    from services.ai_models import CLAUDE_OPUS, CLAUDE_SONNET, TRANSLATE_MODEL
    from services.recipe_v2 import translate, translation

    model = {'sonnet': CLAUDE_SONNET, 'opus': CLAUDE_OPUS}.get(args.model, TRANSLATE_MODEL)

    def name_items(items):
        """Norwegian names for these pantry items, committed unless --try. Returns the cost and the names."""
        names, usages = translate.translate_pantry(items, model=model)
        named = {}
        for item in items:
            if item.id in names:
                item.name_nb = names[item.id]
                named[item.food_id] = item.name_nb
        if not args.attempt:
            db.session.commit()
        for item in items:
            print(f'   {item.name} -> {item.name_nb or "(no answer)"}')
        return sum(u['cost_usd'] for u in usages), named

    with app.app_context():
        if args.from_file:
            saved = json.loads(Path(args.from_file).expanduser().read_text(encoding='utf-8'))
            items = db.session.execute(db.select(Ingredient).where(Ingredient.food_id.in_(saved['pantry']))).scalars().all()
            for item in items:
                print(f'   {item.name} -> {saved["pantry"][item.food_id]}')
                if args.apply:
                    item.name_nb = saved['pantry'][item.food_id]
            done = 0
            for entry in saved['recipes']:
                recipe = db.session.get(Recipe, entry['id'])
                if translation.source(recipe) != entry['original']:
                    print(f'#{recipe.id} {recipe.title}: its words have changed since, left out')
                    continue
                print(f'#{recipe.id} {entry["translated"]["title"]}')
                if args.apply:
                    translation.save(recipe, 'nb', entry['translated'])
                done += 1
            db.session.commit()
            print(f'{len(items)} pantry names and {done} translations from {saved["model"]} ' + ('saved.' if args.apply else 'would be saved: run again with --apply.'))
            return

        if args.remove:
            rows = db.session.execute(db.select(RecipeTranslation).where(RecipeTranslation.language == 'nb',
                                                                         RecipeTranslation.recipe_id.in_(parse_ids(args.ids)))).scalars().all()
            for row in rows:
                print(f'#{row.recipe_id} {row.title}')
                if args.apply:
                    db.session.delete(row)
            db.session.commit()
            print(f'{len(rows)} translations ' + ('taken away.' if args.apply else 'would be taken away: run again with --apply.'))
            return

        if args.pantry:
            stmt = db.select(Ingredient).where(Ingredient.status == 'active').order_by(Ingredient.id)
            items = db.session.execute(stmt if args.force else stmt.where(Ingredient.name_nb.is_(None))).scalars().all()
            print(f'{len(items)} pantry items' + ('' if args.force else ' without a Norwegian name'))
            if args.apply and items:
                print(f'{name_items(items)[0]:.2f} USD with Claude. Saved.')
            elif items:
                print('Nothing called: run again with --apply.')
            return

        stmt = db.select(Recipe).where(Recipe.schema_version == 2).order_by(Recipe.id)
        stmt = stmt.where(Recipe.id.in_(parse_ids(args.ids))) if args.ids else stmt.where(Recipe.status == 'approved')
        recipes = []
        for recipe in db.session.execute(stmt).scalars():
            if args.limit and len(recipes) >= args.limit:
                break
            if not recipe.steps or (recipe.language or 'en') != 'en':
                print(f'#{recipe.id} {recipe.title}: left out, no steps or not written in English')
            elif not args.force and translation.of(recipe, 'nb'):
                print(f'#{recipe.id} {recipe.title}: already translated')
            else:
                recipes.append(recipe)

        items = list({line.ingredient.id: line.ingredient for r in recipes for line in r.lines
                      if line.ingredient is not None and (args.force or not line.ingredient.name_nb)}.values())
        if not (args.apply or args.attempt):
            guess = sum(estimate(translation.source(r)) for r in recipes)
            for r in recipes:
                print(f'#{r.id} {r.title}: {len(r.lines)} lines, {len(r.steps)} steps')
            print(f'\n{len(recipes)} recipes and {len(items)} pantry items, about {guess:.2f} USD with Claude (an estimate). '
                  'Nothing called: run again with --apply.')
            return

        cost, named = name_items(items) if items else (0.0, {})
        run = Path.home() / 'promptlab-runs' / 'translate'
        run.mkdir(parents=True, exist_ok=True)
        path = run / f'{datetime.datetime.now():%Y%m%d-%H%M%S}-{model}.json'
        kept = {'model': model, 'pantry': named, 'recipes': []}
        done, failed = 0, 0
        for recipe in recipes:
            original = translation.source(recipe)
            words, attempts = translate.translate_recipe(recipe, model=model)
            spent = sum(a['cost_usd'] for a in attempts)
            cost += spent
            for attempt in attempts:
                if attempt['problems']:
                    print(f'#{recipe.id} attempt {attempt["attempt"]} sent back: {attempt["problems"][:5]}')
            if words is None:
                failed += 1
                print(f'#{recipe.id} {recipe.title}: left in English after {len(attempts)} attempts, {spent:.3f} USD')
                continue
            if not args.attempt:
                translation.save(recipe, 'nb', words)
                db.session.commit()
            done += 1
            kept['recipes'].append({'id': recipe.id, 'original': original, 'translated': words, 'cost_usd': spent})
            path.write_text(json.dumps(kept, ensure_ascii=False, indent=1), encoding='utf-8')
            print(f'#{recipe.id} {words["title"]}: {spent:.3f} USD, {len(attempts)} attempt(s), https://thelazychef.app/recipe/{recipe.id}?lang=no')
        if args.attempt:
            db.session.rollback()
        print(f'\n{done} translated, {failed} left in English, {cost:.2f} USD with {model}. '
              + ('Nothing saved.' if args.attempt else 'Saved.') + f' For reading: {path}')


if __name__ == '__main__':
    main()
