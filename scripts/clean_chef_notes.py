"""Take what the model decided out of saved recipes' public chef's notes, and keep it as `estimate` notes for the admin
chip. New recipes do not need this (rules 23b and 23c of the structuring prompt). Costs nothing: no model is called.

The file, kept outside the repo in ~/promptlab-runs/chef-notes/, says for each recipe id the note as it stands ("old"),
what it becomes ("new", empty for none) and the sentences that move ("moved"). A recipe whose note is no longer "old" is
left alone, so a second run changes nothing. A translated recipe shows English after this until it is translated again.

Without --apply nothing is saved: it prints each change.

    SSL_CERT_FILE=... DB_PASS=... DB_BACKEND=cloudsql ... ./venv/bin/python -m scripts.clean_chef_notes --from-file ~/promptlab-runs/chef-notes/<file>.json
    ... -m scripts.clean_chef_notes --from-file ~/promptlab-runs/chef-notes/<file>.json --apply
"""
import argparse
import getpass
import json
import os
from pathlib import Path


def main():
    ap = argparse.ArgumentParser(description="Take what the model decided out of saved chef's notes.")
    ap.add_argument('--from-file', required=True, help='the changes, by recipe id')
    ap.add_argument('--apply', action='store_true', help='save; without it only a list')
    args = ap.parse_args()
    if os.getenv('DB_BACKEND', 'local').lower() == 'cloudsql' and not os.getenv('DB_PASS'):
        os.environ['DB_PASS'] = getpass.getpass('Database password (not shown, not stored): ')
    os.environ.setdefault('GOOGLE_API_KEY', 'not-used')  # app.py wants one; nothing here calls Google

    from app import app, db
    from database.models import Recipe
    from services.recipe_v2.generate import ESTIMATE

    changes = json.loads(Path(args.from_file).expanduser().read_text(encoding='utf-8'))
    with app.app_context():
        done, skipped = 0, 0
        for recipe_id, change in changes.items():
            recipe = db.session.get(Recipe, int(recipe_id))
            if recipe is None or recipe.chef_note != change['old']:
                skipped += 1
                print(f'#{recipe_id}: the note is not what the file says, left alone')
                continue
            print(f'#{recipe.id} {recipe.title}\n   now: {change["old"]}\n   new: {change["new"] or "(none)"}')
            if args.apply:
                recipe.chef_note = change['new'] or None
                recipe.validation_errors = [*(recipe.validation_errors or []), *({'rule': ESTIMATE, 'message': m} for m in change['moved'])]
            done += 1
        db.session.commit()
        print(f'{done} notes ' + ('saved' if args.apply else 'would change: run again with --apply') + f', {skipped} left alone.')


if __name__ == '__main__':
    main()
