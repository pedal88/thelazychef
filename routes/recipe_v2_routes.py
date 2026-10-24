"""New recipes in model v2: one input field, a status page, and the task endpoint Cloud Tasks calls.

Admin only, next to today's New Recipe until the old generation goes in step 8.
"""
from flask import Blueprint, abort, flash, jsonify, redirect, render_template, request, url_for
from flask_login import login_required

from database.models import Recipe, db
from services.chef_service import get_chefs
from services.recipe_v2 import batch, generate, tasks
from services.recipe_v2.persona import SETTINGS, age_stages
from services.recipe_v2.language import DEFAULT as DEFAULT_LANGUAGE, LANGUAGES, code_of
from services.recipe_v2.sources import is_link, is_video
from services.recipe_v2.view import as_text
from utils.ai_errors import friendly_ai_error
from utils.decorators import admin_required

recipe_v2_bp = Blueprint('recipe_v2', __name__)

IDEA_MAX = 200  # longer input, or input over several lines, is a pasted recipe


def kind_of(source):
    if is_link(source):
        return 'web'
    return 'text' if len(source) > IDEA_MAX or '\n' in source.strip() else 'idea'


def start(source, kind, chef_id, chosen, age, language):
    """Save the placeholder recipe (status "generating") and queue the job that writes it. Settings and the baby's
    age go with an idea only; a pasted recipe or a link is kept as it is. Returns the recipe."""
    recipe = Recipe(title=source.splitlines()[0][:120], cuisine='', difficulty='', status='generating', schema_version=2, chef_id=chef_id, language=language,
                    source_type={'idea': 'description', 'text': 'text', 'web': 'web'}[kind], source_input=source[:500],
                    settings=(chosen or None) if kind == 'idea' else None, age_from_months=age if kind == 'idea' else None)
    db.session.add(recipe)
    db.session.commit()
    try:
        tasks.enqueue(recipe.id, kind, source, language)
    except Exception as e:
        recipe.status, recipe.is_flagged_for_review = 'draft', True
        recipe.validation_errors = [{'rule': 'error', 'message': friendly_ai_error(e, 'Could not start making the recipe.')}]
        db.session.commit()
    return recipe


@recipe_v2_bp.route('/new-recipe/v2', methods=['GET', 'POST'])
@login_required
@admin_required
def new_recipe():
    chefs = get_chefs()
    if request.method == 'GET':
        return render_template('recipe_v2_new.html', error=None, source='', chefs=chefs, chef_id='', languages=LANGUAGES,
                               language=DEFAULT_LANGUAGE, settings=SETTINGS, chosen=[], stages=age_stages()['stages'], age=None)
    source = (request.form.get('source') or '').strip()
    chef_id = request.form.get('chef_id') or None
    if chef_id not in {c['id'] for c in chefs}:
        chef_id = None
    language = code_of(request.form.get('language')) or DEFAULT_LANGUAGE
    chosen = [k for k in request.form.getlist('settings') if k in SETTINGS]
    ages = {s['from_months'] for s in age_stages()['stages']}
    age = request.form.get('age_from_months', type=int)
    age = (age if age in ages else min(ages)) if 'baby' in chosen else None
    if not source:
        return render_template('recipe_v2_new.html', error='Write an idea or paste a recipe.', source=source,
                               chefs=chefs, chef_id=chef_id or '', languages=LANGUAGES, language=language,
                               settings=SETTINGS, chosen=chosen, stages=age_stages()['stages'], age=age), 400
    kind = kind_of(source)
    if kind == 'web' and is_video(source):
        return render_template('recipe_v2_new.html', source=source, chefs=chefs, chef_id=chef_id or '', languages=LANGUAGES,
                               language=language, settings=SETTINGS, chosen=chosen, stages=age_stages()['stages'], age=age,
                               error='Video links are not supported here yet. Use the old importer, or paste the recipe text.'), 400
    recipe = start(source, kind, chef_id, chosen, age, language)
    return redirect(url_for('recipe_v2.generating', recipe_id=recipe.id))


@recipe_v2_bp.route('/new-recipe/v2/batch', methods=['GET', 'POST'])
@login_required
@admin_required
def batch_new():
    """Many recipes at once: one line per recipe (services/recipe_v2/batch.py). "Check" shows what each line becomes
    and what it costs; "Make" starts them, each as New Recipe would, and goes to the status page."""
    chefs = get_chefs()
    form = request.form
    text = form.get('lines') or ''
    default_chef = next((c for c in chefs if c['id'] == form.get('chef_id')), None)
    default_settings = [k for k in form.getlist('settings') if k in SETTINGS]
    ages = {s['from_months'] for s in age_stages()['stages']}
    default_age = form.get('age_from_months', type=int)
    default_age = (default_age if default_age in ages else min(ages)) if 'baby' in default_settings else None
    language = code_of(form.get('language')) or DEFAULT_LANGUAGE
    page = dict(text=text, chefs=chefs, chef_id=default_chef['id'] if default_chef else '', settings=SETTINGS,
                chosen=default_settings, stages=age_stages()['stages'], age=default_age, languages=LANGUAGES,
                language=language, again=bool(form.get('again')), max_lines=batch.MAX_LINES, idea_max=batch.IDEA_MAX)
    if request.method == 'GET':
        return render_template('recipe_v2_batch.html', rows=None, **page)

    # Lines already made before: the same idea or link
    lowered = {line.split('|')[0].strip().lower() for line in text.splitlines() if line.strip()}
    existing = {}
    if lowered:
        for rid, src in db.session.execute(db.select(Recipe.id, Recipe.source_input).where(
                Recipe.schema_version == 2, db.func.lower(Recipe.source_input).in_(lowered))).all():
            existing.setdefault(src.lower(), rid)
    rows, over = batch.parse(text, chefs, default_chef, default_settings, default_age, existing)
    todo = [r for r in rows if not r['error'] and (page['again'] or not r['made'])]
    low, high = batch.COST_EACH
    page.update(rows=rows, over=over, todo=len(todo), cost=(round(low * len(todo), 2), round(high * len(todo), 2)))
    if form.get('action') != 'make' or not todo:
        return render_template('recipe_v2_batch.html', **page)
    ids = [start(r['source'], r['kind'], r['chef']['id'] if r['chef'] else None, r['settings'], r['age'], language).id
           for r in todo]
    return redirect(url_for('recipe_v2.batch_status', ids=','.join(map(str, ids))))


@recipe_v2_bp.route('/new-recipe/v2/batch/status')
@login_required
@admin_required
def batch_status():
    """How the recipes of a batch are getting on; the page reloads itself while any is still being made."""
    ids = [int(x) for x in (request.args.get('ids') or '').split(',') if x.strip().isdigit()][:batch.MAX_LINES]
    recipes = {r.id: r for r in db.session.execute(db.select(Recipe).where(Recipe.id.in_(ids))).scalars()} if ids else {}
    rows = [recipes[i] for i in ids if i in recipes]
    return render_template('recipe_v2_batch_status.html', recipes=rows,
                           working=sum(r.status == 'generating' for r in rows), settings=SETTINGS)


@recipe_v2_bp.route('/new-recipe/v2/version/<int:recipe_id>', methods=['POST'])
@login_required
@admin_required
def new_version(recipe_id):
    """The same dish made by a chef persona. The version links to the base dish (the root, never another version)."""
    base = db.session.get(Recipe, recipe_id) or abort(404)
    chef = next((c for c in get_chefs() if c['id'] == request.form.get('chef_id')), None)
    if base.schema_version != 2 or not base.steps or chef is None:
        flash('Choose a chef, and make versions only of finished recipes in the new model.', 'error')
        return redirect(url_for('recipe_detail', recipe_id=recipe_id))
    recipe = Recipe(title=base.title[:120], cuisine='', difficulty='', status='generating', schema_version=2,
                    chef_id=chef['id'], base_recipe_id=base.base_recipe_id or base.id, source_type='version', language=base.language,
                    settings=base.settings, age_from_months=base.age_from_months,
                    source_input=f"Version of recipe {base.id} by {chef['name']}")
    db.session.add(recipe)
    db.session.commit()
    try:
        tasks.enqueue(recipe.id, 'version', as_text(base))
    except Exception as e:
        recipe.status, recipe.is_flagged_for_review = 'draft', True
        recipe.validation_errors = [{'rule': 'error', 'message': friendly_ai_error(e, 'Could not start making the version.')}]
        db.session.commit()
    return redirect(url_for('recipe_v2.generating', recipe_id=recipe.id))


@recipe_v2_bp.route('/new-recipe/v2/recalculate/<int:recipe_id>', methods=['POST'])
@login_required
@admin_required
def recalculate(recipe_id):
    """Metadata, nutrition and the chef's rules again from the saved recipe, after the pantry or the rules changed."""
    recipe = db.session.get(Recipe, recipe_id) or abort(404)
    if recipe.schema_version != 2 or not recipe.steps:
        abort(400)
    generate.recalculate(recipe)
    db.session.commit()
    flash('Recalculated: metadata, nutrition and the chef\'s rules.', 'success')
    return redirect(url_for('recipe_detail', recipe_id=recipe_id))


@recipe_v2_bp.route('/new-recipe/v2/images/<int:recipe_id>', methods=['POST'])
@login_required
@admin_required
def make_images(recipe_id):
    """The dish image and the part images, each checked by a vision model (services/recipe_v2/images.py).
    Takes a minute or two; admin only for now."""
    from routes._shared import get_storage
    from services.recipe_v2 import images

    recipe = db.session.get(Recipe, recipe_id) or abort(404)
    if recipe.schema_version != 2 or not recipe.steps:
        abort(400)
    style = request.form.get('style')
    if style is not None and style not in images.STYLES:
        abort(400)
    try:
        report = images.make_images(recipe, get_storage(), style=style)
    except Exception as e:
        db.session.rollback()
        flash(friendly_ai_error(e, 'Could not make the images.'), 'error')
        return redirect(url_for('recipe_detail', recipe_id=recipe_id))
    db.session.commit()
    parts = f" and {report['parts']} part{'s' if report['parts'] != 1 else ''}" if report['parts'] else ''
    checked = ' The check found something to look at, see below.' if report['notes'] else ''
    kind = f" in the style {report['style']} (trial)" if report['trial'] else ''
    flash(f"Made the dish image{parts}{kind} (about {report['cost_usd']:.2f} USD).{checked}", 'success')
    back = request.form.get('next') or ''
    if not back.startswith('/') or back.startswith('//'):  # only back to a page of this site
        back = url_for('recipe_detail', recipe_id=recipe_id)
    return redirect(back)


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
    if data.get('kind') not in generate.SOURCE_TYPES or not data.get('source'):
        return jsonify({'error': 'bad task'}), 400
    attempt = request.headers.get('X-CloudTasks-TaskRetryCount', type=int) or 0
    tasks.run(recipe_id, data['kind'], data['source'], attempt=attempt, language=code_of(data.get('language')))
    return jsonify({'done': True})
