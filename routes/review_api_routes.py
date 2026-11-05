"""The review API: what Claude Code uses to check recipes and the pantry in production without Pål running a script
(docs/OPERATIONS.md, "The review API"). It needs the key in REVIEW_API_KEY as a bearer token; without that variable it
answers 401 to everything. The key is its own, so it opens nothing else, and CONTENT_API_KEY does not open this.

It only reads: every route is a GET, and on Postgres the transaction is read only. It answers with recipes and the
pantry and nothing about people: each answer is built field by field here, never from a whole row, and Recipe.notes
(an admin's notes, with who wrote them) stays out."""
import hmac
import os

from flask import Blueprint, jsonify, request
from sqlalchemy import or_, text
from sqlalchemy.orm import selectinload

from database.models import Ingredient, IngredientAlias, Recipe, RecipeLine, db
from services.recipe_v2 import nutrition, pantry_fill, pantry_links
from services.recipe_v2.planner import plan_v2
from services.recipe_v2.store import to_v2

review_api_bp = Blueprint('review_api', __name__, url_prefix='/api/review')
PANTRY_MAX = 50  # items an answer holds
ANSWERED_MAX = 100


@review_api_bp.before_request
def guard():
    """For the whole blueprint, so a new route cannot forget it: the request carries REVIEW_API_KEY as
    "Authorization: Bearer <key>", and what it does after that cannot write."""
    key = os.environ.get('REVIEW_API_KEY', '')
    sent = request.headers.get('Authorization', '')
    if not key or not sent.startswith('Bearer ') or not hmac.compare_digest(sent[7:].encode(), key.encode()):
        return jsonify({'error': 'unauthorized'}), 401
    conn = db.session.connection()
    if conn.dialect.name == 'postgresql':
        conn.execute(text('SET TRANSACTION READ ONLY'))  # ends with the request's transaction, as the session is removed
    return None


def _item(item):
    return {'food_id': item.food_id, 'name': item.name, 'status': item.status, 'tier': item.tier,
            'main_category': item.main_category, 'sub_category': item.sub_category, 'default_unit': item.default_unit,
            'data_source': item.data_source, 'aliases': item.aliases}


def _line(line):
    return {'local_id': line.local_id, 'component': line.component.local_id, 'step': line.step.local_id,
            'name': line.name, 'amount': line.amount, 'unit': line.unit, 'gram_weight': line.gram_weight,
            'state': line.state, 'grade': line.grade, 'variety': line.variety, 'prep_style': line.prep_style,
            'pantry': _item(line.ingredient) if line.ingredient else None}


def _step(step):
    return {'local_id': step.local_id, 'component': step.component.local_id, 'phase': step.phase, 'short': step.short,
            'verb': step.verb, 'text': step.text, 'method': step.method, 'equipment': step.equipment or [],
            'temp_c': step.temp_c, 'mode': step.mode, 'setup': step.setup, 'done_when': step.done_when,
            'active_minutes': step.active_minutes, 'passive_minutes': step.passive_minutes,
            'holds_minutes': step.holds_minutes, 'after': [s.local_id for s in step.after]}


def _times(recipe):
    """The time saved on the recipe and what the planner says now. Steps that form a cycle have no plan."""
    times = {'saved_minutes': recipe.prep_time_mins, 'planned_minutes': None, 'planned_hands_on_minutes': None}
    if recipe.steps:
        try:
            plan = plan_v2(to_v2(recipe))
            times.update(planned_minutes=plan['T'], planned_hands_on_minutes=plan['A'])
        except ValueError:
            pass
    return times


@review_api_bp.route('/recipes/<int:recipe_id>')
def recipe(recipe_id):
    """One recipe in any status, drafts included."""
    found = db.session.get(Recipe, recipe_id)
    if found is None:
        return jsonify({'error': f'no recipe {recipe_id}'}), 404
    return jsonify({
        'id': found.id, 'title': found.title, 'status': found.status, 'flagged': found.is_flagged_for_review,
        'schema_version': found.schema_version, 'revision': found.revision,
        'revised_at': found.revised_at.isoformat(timespec='seconds') if found.revised_at else None,
        'source_type': found.source_type, 'source_input': found.source_input, 'source_text': found.source_text,
        'chef_id': found.chef_id, 'base_recipe_id': found.base_recipe_id, 'settings': found.settings or [],
        'language': found.language, 'cuisine': found.cuisine, 'meal_types': found.meal_types_list,
        'servings': found.base_servings, 'yield_text': found.yield_text, 'chef_note': found.chef_note,
        'validation_errors': found.validation_errors or [], 'times': _times(found),
        'per_serving': nutrition.per_serving(found),
        'components': [{'local_id': c.local_id, 'name': c.name} for c in found.components],
        'lines': [_line(line) for line in found.lines], 'steps': [_step(step) for step in found.steps]})


@review_api_bp.route('/pantry')
def pantry():
    """Pantry items in any status whose name or an alias contains ?q=."""
    q = (request.args.get('q') or '').strip()
    if not q:
        return jsonify({'error': 'give a name to search for as ?q='}), 400
    named = db.select(IngredientAlias.ingredient_id).where(IngredientAlias.name.icontains(q, autoescape=True))
    found = db.session.execute(
        db.select(Ingredient).options(selectinload(Ingredient.alias_entries))
        .where(or_(Ingredient.name.icontains(q, autoescape=True), Ingredient.id.in_(named)))
        .order_by(Ingredient.name).limit(PANTRY_MAX + 1)).scalars().all()
    return jsonify({'items': [_item(i) for i in found[:PANTRY_MAX]], 'more': len(found) > PANTRY_MAX})


def _waiting_on(row):
    swap_item = row['swap_item']
    return {'recipe_id': row['recipe'].id, 'title': row['recipe'].title, 'status': row['recipe'].status,
            'lines': sorted({line.name for line in row['lines']}), 'reason': row['reason'], 'swap': row['swap'], 'odds': row['odds'],
            'swap_item': {'food_id': swap_item.food_id, 'name': swap_item.name} if swap_item else None}


@review_api_bp.route('/questions')
def questions():
    """What /admin/pantry-questions shows: the open questions, and the latest answers (?limit=, 20)."""
    limit = min(max(request.args.get('limit', 20, type=int), 0), ANSWERED_MAX)
    answer_fields = ('recipe_id', 'title', 'line', 'answer', 'reason', 'at')
    return jsonify({
        'questions': [{'item': _item(q['item']), 'can_swap': q['can_swap'], 'recipes': [_waiting_on(r) for r in q['rows']]}
                      for q in pantry_fill.questions()],
        'answered': [{f: a.get(f) for f in answer_fields} for a in pantry_fill.answered(limit)]})


@review_api_bp.route('/pantry-report')
def pantry_report():
    """The report of scripts/pantry_links.py, as its lines of text. Every line of every recipe goes through the matcher,
    so it takes a while. No AI."""
    recipes = db.session.execute(
        db.select(Recipe).where(Recipe.schema_version == 2).order_by(Recipe.id)
        .options(selectinload(Recipe.lines).selectinload(RecipeLine.ingredient))).scalars().all()
    aliases = db.session.execute(db.select(IngredientAlias).options(selectinload(IngredientAlias.ingredient))).scalars().all()
    return jsonify({'report': pantry_links.report(recipes, aliases)})
