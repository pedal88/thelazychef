"""New recipes in model v2: one input field, a status page, and the task endpoint Cloud Tasks calls.

Admin only, next to today's New Recipe until the old generation goes in step 8.
"""
from flask import Blueprint, abort, jsonify, redirect, render_template, request, url_for
from flask_login import login_required

from database.models import Recipe, db
from services.chef_service import get_chefs
from services.recipe_v2 import tasks
from services.recipe_v2.sources import is_link, is_video
from utils.ai_errors import friendly_ai_error
from utils.decorators import admin_required

recipe_v2_bp = Blueprint('recipe_v2', __name__)

IDEA_MAX = 200  # longer input, or input over several lines, is a pasted recipe


def kind_of(source):
    if is_link(source):
        return 'web'
    return 'text' if len(source) > IDEA_MAX or '\n' in source.strip() else 'idea'


@recipe_v2_bp.route('/new-recipe/v2', methods=['GET', 'POST'])
@login_required
@admin_required
def new_recipe():
    chefs = get_chefs()
    if request.method == 'GET':
        return render_template('recipe_v2_new.html', error=None, source='', chefs=chefs, chef_id='')
    source = (request.form.get('source') or '').strip()
    chef_id = request.form.get('chef_id') or None
    if chef_id not in {c['id'] for c in chefs}:
        chef_id = None
    if not source:
        return render_template('recipe_v2_new.html', error='Write an idea or paste a recipe.', source=source,
                               chefs=chefs, chef_id=chef_id or ''), 400
    kind = kind_of(source)
    if kind == 'web' and is_video(source):
        return render_template('recipe_v2_new.html', source=source, chefs=chefs, chef_id=chef_id or '',
                               error='Video links are not supported here yet. Use the old importer, or paste the recipe text.'), 400
    recipe = Recipe(title=source.splitlines()[0][:120], cuisine='', difficulty='', status='generating', schema_version=2, chef_id=chef_id,
                    source_type={'idea': 'description', 'text': 'text', 'web': 'web'}[kind], source_input=source[:500])
    db.session.add(recipe)
    db.session.commit()
    try:
        tasks.enqueue(recipe.id, kind, source)
    except Exception as e:
        recipe.status, recipe.is_flagged_for_review = 'draft', True
        recipe.validation_errors = [{'rule': 'error', 'message': friendly_ai_error(e, 'Could not start making the recipe.')}]
        db.session.commit()
    return redirect(url_for('recipe_v2.generating', recipe_id=recipe.id))


@recipe_v2_bp.route('/new-recipe/v2/<int:recipe_id>')
@login_required
@admin_required
def generating(recipe_id):
    recipe = db.session.get(Recipe, recipe_id) or abort(404)
    if recipe.status != 'generating':
        return redirect(url_for('recipe_detail', recipe_id=recipe_id))
    return render_template('recipe_v2_generating.html', recipe=recipe)


@recipe_v2_bp.route('/new-recipe/v2/<int:recipe_id>/status')
@login_required
@admin_required
def status(recipe_id):
    recipe = db.session.get(Recipe, recipe_id) or abort(404)
    return jsonify({'status': recipe.status, 'url': url_for('recipe_detail', recipe_id=recipe_id)})


@recipe_v2_bp.route(tasks.TASK_PATH.replace('{id}', '<int:recipe_id>'), methods=['POST'])
def run_task(recipe_id):
    """Called by Cloud Tasks with an OIDC token from the queue's service account, not by users.

    A 5xx answer makes Cloud Tasks try again; run() turns the last failure into a flagged draft."""
    if not tasks.verified(request.headers.get('Authorization')):
        return jsonify({'error': 'unauthorized'}), 401
    data = request.get_json(silent=True) or {}
    if data.get('kind') not in ('idea', 'text', 'web') or not data.get('source'):
        return jsonify({'error': 'bad task'}), 400
    attempt = request.headers.get('X-CloudTasks-TaskRetryCount', type=int) or 0
    tasks.run(recipe_id, data['kind'], data['source'], attempt=attempt)
    return jsonify({'done': True})
