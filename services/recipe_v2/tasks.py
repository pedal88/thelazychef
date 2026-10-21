"""Make v2 recipes in the background with Cloud Tasks (docs/RECIPE_MODEL_V2.md, section 7).

New Recipe saves a placeholder recipe (status "generating") and puts one task
in the queue. Cloud Tasks calls /internal/tasks/recipe-v2/<id> on the app with
an OIDC token from its own service account, and the request runs both rounds.
Cloud Tasks waits up to 10 minutes and retries failed requests; the queue
limits how many run at once.

Configuration (deploy.yaml): TASKS_QUEUE, TASKS_LOCATION, TASKS_SERVICE_ACCOUNT
and APP_BASE_URL. Without TASKS_QUEUE (running locally) the job runs straight
away in the request.
"""
import base64
import json
import logging
import os

from database.models import Recipe, db
from utils.ai_errors import friendly_ai_error

log = logging.getLogger(__name__)
PROJECT = os.getenv('GOOGLE_CLOUD_PROJECT', 'thelazychefai-prod')
MAX_ATTEMPTS = 3  # same as the queue's --max-attempts
TASK_PATH = '/internal/tasks/recipe-v2/{id}'


def configured():
    return bool(os.getenv('TASKS_QUEUE'))


def enqueue(recipe_id, kind, source, language=None):
    """Queue the job, or run it now when no queue is configured. language None: as the idea or source is written."""
    if not configured():
        run(recipe_id, kind, source, attempt=MAX_ATTEMPTS - 1, language=language)
        return
    import google.auth
    from google.auth.transport.requests import AuthorizedSession

    base = os.environ['APP_BASE_URL'].rstrip('/')
    url = base + TASK_PATH.format(id=recipe_id)
    queue = f"projects/{PROJECT}/locations/{os.getenv('TASKS_LOCATION', 'europe-west1')}/queues/{os.environ['TASKS_QUEUE']}"
    body = base64.b64encode(json.dumps({'kind': kind, 'source': source, 'language': language}).encode()).decode()
    task = {'task': {
        'dispatchDeadline': '600s',
        'httpRequest': {
            'httpMethod': 'POST', 'url': url, 'headers': {'Content-Type': 'application/json'}, 'body': body,
            'oidcToken': {'serviceAccountEmail': os.environ['TASKS_SERVICE_ACCOUNT'], 'audience': base},
        },
    }}
    credentials, _ = google.auth.default(scopes=['https://www.googleapis.com/auth/cloud-platform'])
    res = AuthorizedSession(credentials).post(f'https://cloudtasks.googleapis.com/v2/{queue}/tasks', json=task, timeout=20)
    res.raise_for_status()


def verified(auth_header):
    """True when the request carries an OIDC token from the queue's service account, for this app."""
    if not configured() or not auth_header or not auth_header.startswith('Bearer '):
        return False
    from google.auth.transport.requests import Request
    from google.oauth2 import id_token

    try:
        claims = id_token.verify_oauth2_token(auth_header[7:], Request(), audience=os.environ['APP_BASE_URL'].rstrip('/'))
    except ValueError:
        return False
    return claims.get('email') == os.environ.get('TASKS_SERVICE_ACCOUNT') and claims.get('email_verified', False)


def run(recipe_id, kind, source, attempt=0, language=None):
    """Make the recipe into the placeholder. Returns True when done (also when the recipe ends up flagged).

    Errors raise, so Cloud Tasks tries again, except on the last attempt: then the
    placeholder becomes a flagged draft with the error, so it never stays "generating"."""
    from services.recipe_v2.generate import create_recipe

    recipe = db.session.get(Recipe, recipe_id)
    if recipe is None or recipe.status != 'generating':
        return True  # deleted, or already done by an earlier attempt
    from services.recipe_v2.sources import SourceError

    try:
        create_recipe(kind, source, chef_id=recipe.chef_id, recipe=recipe, language=language)
        return True
    except SourceError as e:
        # The link cannot be read (blocked, gone, no recipe). Trying again does not help.
        db.session.rollback()
        recipe = db.session.get(Recipe, recipe_id)
        recipe.status, recipe.is_flagged_for_review = 'draft', True
        recipe.validation_errors = [{'rule': 'source', 'message': str(e)}]
        db.session.commit()
        return True
    except Exception as e:
        db.session.rollback()
        log.exception('Recipe %s: generation failed on attempt %s', recipe_id, attempt + 1)
        if attempt + 1 < MAX_ATTEMPTS:
            raise
        recipe = db.session.get(Recipe, recipe_id)
        recipe.status, recipe.is_flagged_for_review = 'draft', True
        recipe.validation_errors = [{'rule': 'error', 'message': friendly_ai_error(e)}]  # the raw error is logged above
        db.session.commit()
        return True
