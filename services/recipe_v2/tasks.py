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
IMAGES_PATH = '/internal/tasks/recipe-v2-images/{id}'  # the dish and part images of a recipe already made
PANTRY_PATH = '/internal/tasks/recipe-v2-pantry/{id}'  # the pantry items for its unlinked lines (pantry_fill.py)


def configured():
    return bool(os.getenv('TASKS_QUEUE'))


def enqueue(recipe_id, kind, source, language=None, images=True):
    """Queue the job, or run it now when no queue is configured.

    language is a code (services/recipe_v2/language.py); None: as the idea or source is written.
    images: queue the image job when the recipe is made (see run)."""
    if not configured():
        run(recipe_id, kind, source, attempt=MAX_ATTEMPTS - 1, language=language, images=images)
        return
    _queue(TASK_PATH.format(id=recipe_id), {'kind': kind, 'source': source, 'language': language, 'images': images})


def enqueue_pantry(recipe_id, images=True):
    """Queue the job that fills the pantry for a recipe's unlinked lines; it queues the images after."""
    _queue(PANTRY_PATH.format(id=recipe_id), {'images': images})


def enqueue_images(recipe_id):
    """Queue the job that makes a recipe's images (services/recipe_v2/images.py), or run it now without a queue."""
    if not configured():
        run_images(recipe_id, attempt=MAX_ATTEMPTS - 1)
        return
    _queue(IMAGES_PATH.format(id=recipe_id), {})


def _queue(path, payload):
    import google.auth
    from google.auth.transport.requests import AuthorizedSession

    base = os.environ['APP_BASE_URL'].rstrip('/')
    queue = f"projects/{PROJECT}/locations/{os.getenv('TASKS_LOCATION', 'europe-west1')}/queues/{os.environ['TASKS_QUEUE']}"
    body = base64.b64encode(json.dumps(payload).encode()).decode()
    task = {'task': {
        'dispatchDeadline': '600s',
        'httpRequest': {
            'httpMethod': 'POST', 'url': base + path, 'headers': {'Content-Type': 'application/json'}, 'body': body,
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


def run(recipe_id, kind, source, attempt=0, language=None, images=True):
    """Make the recipe into the placeholder. Returns True when done (also when the recipe ends up flagged).

    Errors raise, so Cloud Tasks tries again, except on the last attempt: then the
    placeholder becomes a flagged draft with the error, so it never stays "generating".
    A recipe that was made then gets its follow-up jobs: the pantry job when some lines are not in the pantry
    (run_pantry), and with images the image job, so it is seen complete when it is reviewed. The pantry job queues
    the images itself, so the two never change the recipe at once. Only with a queue: locally, both are done from
    the recipe page, the images page and scripts/fill_pantry.py."""
    from services.recipe_v2.generate import create_recipe

    recipe = db.session.get(Recipe, recipe_id)
    if recipe is None or recipe.status != 'generating':
        return True  # deleted, or already done by an earlier attempt
    from services.recipe_v2.sources import SourceError

    try:
        create_recipe(kind, source, chef_id=recipe.chef_id, recipe=recipe, language=language)
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
    if configured():
        from services.recipe_v2.pantry_fill import needs_filling

        try:
            if needs_filling(recipe_id):
                enqueue_pantry(recipe_id, images)
            elif images:
                enqueue_images(recipe_id)
        except Exception:
            # The recipe is made; the rest can still be done from the images page and scripts/fill_pantry.py
            log.exception('Recipe %s: could not queue the follow-up jobs', recipe_id)
    return True


def run_pantry(recipe_id, images=True, attempt=0):
    """Fill the pantry for the recipe's unlinked lines and recalculate it (pantry_fill.fill), then queue its images.
    Errors raise, so Cloud Tasks tries again, except on the last attempt: then the error is noted on the recipe
    (rule "pantry") and the images are queued anyway."""
    from services.recipe_v2 import pantry_fill

    recipe = db.session.get(Recipe, recipe_id)
    if recipe is None or recipe.schema_version != 2 or not recipe.steps:
        return True
    try:
        pantry_fill.fill(recipe)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        log.exception('Recipe %s: pantry failed on attempt %s', recipe_id, attempt + 1)
        if attempt + 1 < MAX_ATTEMPTS:
            raise
        recipe = db.session.get(Recipe, recipe_id)
        kept = [x for x in recipe.validation_errors or [] if x.get('rule') != pantry_fill.RULE]
        recipe.validation_errors = kept + [{'rule': pantry_fill.RULE,
                                            'message': friendly_ai_error(e, 'Could not fill the pantry.')}]
        db.session.commit()
    if images and configured():
        try:
            enqueue_images(recipe_id)
        except Exception:
            log.exception('Recipe %s: could not queue the images', recipe_id)
    return True


def run_images(recipe_id, attempt=0):
    """Make the recipe's own images. Errors raise, so Cloud Tasks tries again, except on the last attempt: then the
    error is noted on the recipe (rule "image"), where the admin chip shows it."""
    from routes._shared import get_storage
    from services.recipe_v2 import images

    recipe = db.session.get(Recipe, recipe_id)
    if recipe is None or recipe.schema_version != 2 or not recipe.steps:
        return True
    try:
        images.make_images(recipe, get_storage())
        db.session.commit()
        return True
    except Exception as e:
        db.session.rollback()
        log.exception('Recipe %s: images failed on attempt %s', recipe_id, attempt + 1)
        if attempt + 1 < MAX_ATTEMPTS:
            raise
        recipe = db.session.get(Recipe, recipe_id)
        kept = [x for x in recipe.validation_errors or [] if x.get('rule') != 'image']
        recipe.validation_errors = kept + [{'rule': 'image', 'message': friendly_ai_error(e, 'Could not make the images.')}]
        db.session.commit()
        return True
