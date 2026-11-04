"""Ingredient questions (services/recipe_v2/pantry_fill.py): what a recipe needs that the pantry lacks and only Pål can
let in. Admin only. Adding an item draws its symbol, about 0.04 USD."""
from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import login_required

from database.models import Ingredient, db
from routes._shared import get_storage
from services.recipe_v2 import pantry_fill
from utils.decorators import admin_required

pantry_questions_bp = Blueprint('pantry_questions', __name__)


def _waiting_item(item_id):
    item = db.session.get(Ingredient, item_id) or abort(404)
    if item.status != 'pending':
        abort(409)
    return item


@pantry_questions_bp.route('/admin/pantry-questions')
@login_required
@admin_required
def questions():
    names = db.session.execute(db.select(Ingredient.name).where(Ingredient.status == 'active').order_by(Ingredient.name)).scalars().all()
    return render_template('pantry_questions.html', questions=pantry_fill.questions(), answered=pantry_fill.answered(), names=names)


@pantry_questions_bp.route('/admin/pantry-questions/<int:item_id>/add', methods=['POST'])
@login_required
@admin_required
def add(item_id):
    item = _waiting_item(item_id)
    pantry_fill.add_item(item)
    db.session.commit()
    made = pantry_fill.make_symbols([item], get_storage())  # a failure leaves it without; the ingredient page can make it
    db.session.commit()
    flash(f'{item.name} is in the pantry.' + ('' if made else ' Its symbol could not be made.'), 'success')
    return redirect(url_for('pantry_questions.questions'))


@pantry_questions_bp.route('/admin/pantry-questions/<int:item_id>/swap', methods=['POST'])
@login_required
@admin_required
def swap(item_id):
    item = _waiting_item(item_id)
    other = None
    name = (request.form.get('other') or '').strip().lower()
    if name:
        other = db.session.execute(db.select(Ingredient).where(db.func.lower(Ingredient.name) == name, Ingredient.status == 'active')).scalars().first()
        if other is None:
            flash(f'{name} is not in the pantry.', 'error')
            return redirect(url_for('pantry_questions.questions'))
    changed = pantry_fill.swap(item, other)
    db.session.commit()
    flash(f'{item.name}: swapped in {len(changed)} {"recipe" if len(changed) == 1 else "recipes"}.', 'success')
    return redirect(url_for('pantry_questions.questions'))
