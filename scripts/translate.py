"""Translate saved recipes and the pantry's names into Norwegian (services/recipe_v2/translate.py), and take a translation
away again. New recipes are not translated by themselves yet.

Without --apply nothing is called and nothing is saved: it lists what would be translated, with an estimate of the cost.
With --apply it first gives the recipes' pantry items their Norwegian names where they have none, then translates each
recipe, committed on its own; about 0.01-0.05 USD a recipe (an estimate until measured, Sonnet, the printed cost is real).
A recipe that already has a translation matching its words is left alone unless --force. The originals and the
translations go to ~/promptlab-runs/translate/<time>.json, and nothing shows to anyone who has not chosen Norwegian.

    SSL_CERT_FILE=... DB_PASS=... DB_BACKEND=cloudsql ... ANTHROPIC_API_KEY=... ./venv/bin/python -m scripts.translate --ids 374,380
    ... -m scripts.translate --ids 374,380 --apply
    ... -m scripts.translate --approved --limit 20 --apply
    ... -m scripts.translate --pantry --apply          (every active pantry item without a Norwegian name)
    ... -m scripts.translate --remove --ids 374 --apply
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
    args = ap.parse_args()
    if not (args.ids or args.approved or args.pantry):
        ap.error('give --ids, --approved or --pantry')
    if args.remove and not args.ids:
        ap.error('--remove takes --ids')

    if os.getenv('DB_BACKEND', 'local').lower() == 'cloudsql' and not os.getenv('DB_PASS'):
        os.environ['DB_PASS'] = getpass.getpass('Database password (not shown, not stored): ')
    os.environ.setdefault('GOOGLE_API_KEY', 'not-used')  # app.py wants one; nothing here calls Google
    if args.apply and not args.remove and not os.getenv('ANTHROPIC_API_KEY'):
        ap.error('--apply needs ANTHROPIC_API_KEY')

    from app import app, db
    from database.models import Ingredient, Recipe, RecipeTranslation
    from services.recipe_v2 import translate, translation

    def name_items(items):
        """Norwegian names for these pantry items. Returns the cost."""
        names, usages = translate.translate_pantry(items)
        for item in items:
            if item.id in names:
                item.name_nb = names[item.id]
        db.session.commit()
        for item in items:
            print(f'   {item.name} -> {item.name_nb or "(no answer)"}')
        return sum(u['cost_usd'] for u in usages)

    with app.app_context():
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
            items = db.session.execute(db.select(Ingredient).where(Ingredient.status == 'active', Ingredient.name_nb.is_(None))
                                       .order_by(Ingredient.id)).scalars().all()
            print(f'{len(items)} pantry items without a Norwegian name')
            if args.apply and items:
                print(f'{name_items(items):.2f} USD with Claude. Saved.')
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
                      if line.ingredient is not None and not line.ingredient.name_nb}.values())
        if not args.apply:
            guess = sum(estimate(translation.source(r)) for r in recipes)
            for r in recipes:
                print(f'#{r.id} {r.title}: {len(r.lines)} lines, {len(r.steps)} steps')
            print(f'\n{len(recipes)} recipes and {len(items)} pantry items, about {guess:.2f} USD with Claude (an estimate). '
                  'Nothing called: run again with --apply.')
            return

        cost = name_items(items) if items else 0.0
        run = Path.home() / 'promptlab-runs' / 'translate'
        run.mkdir(parents=True, exist_ok=True)
        path = run / f'{datetime.datetime.now():%Y%m%d-%H%M%S}.json'
        kept, done, failed = [], 0, 0
        for recipe in recipes:
            original = translation.source(recipe)
            words, attempts = translate.translate_recipe(recipe)
            spent = sum(a['cost_usd'] for a in attempts)
            cost += spent
            if words is None:
                failed += 1
                db.session.rollback()
                print(f'#{recipe.id} {recipe.title}: left in English after {len(attempts)} attempts, {spent:.3f} USD: {attempts[-1]["problems"][:3]}')
                continue
            translation.save(recipe, 'nb', words)
            db.session.commit()
            done += 1
            kept.append({'id': recipe.id, 'original': original, 'translated': words, 'cost_usd': spent})
            path.write_text(json.dumps(kept, ensure_ascii=False, indent=1), encoding='utf-8')
            print(f'#{recipe.id} {words["title"]}: {spent:.3f} USD, {len(attempts)} attempt(s), https://thelazychef.app/recipe/{recipe.id}?lang=no')
        print(f'\n{done} translated, {failed} left in English, {cost:.2f} USD with Claude. Saved. For reading: {path}')


if __name__ == '__main__':
    main()
