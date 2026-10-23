"""Admin notes on a recipe: feedback written on the recipe pages (the Notes part of the floating admin chip,
templates/components/recipe_notes.html), kept in recipe_note and copied out as text. /admin/notes lists them all."""
from flask import Blueprint, abort, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from database.models import Recipe, RecipeNote, db
from services.recipe_notes import when
from utils.decorators import admin_required

notes_bp = Blueprint('notes', __name__)

TEXT_MAX = 4000


def _answer(recipe):
    """The chip's notes part again for the page's script, or back to the page without it."""
    if request.headers.get('X-Requested-With') == 'fetch':
        return render_template('components/recipe_notes_part.html', recipe=recipe, page=request.form.get('page') or '')
    back = request.form.get('next') or ''
    if not back.startswith('/') or back.startswith('//'):  # only back to a page on this site
        back = url_for('recipe_detail', recipe_id=recipe.id)
    return redirect(back)


@notes_bp.route('/recipe/<int:recipe_id>/notes', methods=['POST'])
@login_required
@admin_required
def add(recipe_id):
    recipe = db.session.get(Recipe, recipe_id) or abort(404)
    text = (request.form.get('text') or '').strip()[:TEXT_MAX]
    if text:
        place = (request.form.get('place') or '').strip()[:80] or None
        db.session.add(RecipeNote(recipe_id=recipe.id, user_id=current_user.id, place=place, text=text))
        db.session.commit()
    return _answer(recipe)


@notes_bp.route('/recipe/notes/<int:note_id>/done', methods=['POST'])
@login_required
@admin_required
def done(note_id):
    """Done, or open again."""
    note = db.session.get(RecipeNote, note_id) or abort(404)
    note.done = not note.done
    db.session.commit()
    return _answer(note.recipe)


@notes_bp.route('/admin/notes')
@login_required
@admin_required
def overview():
    """Every recipe with notes, newest note first; the open notes only, unless ?all=1."""
    show_all = request.args.get('all') == '1'
    q = db.select(RecipeNote).order_by(RecipeNote.id.desc())
    if not show_all:
        q = q.where(RecipeNote.done.is_(False))
    groups = {}
    for note in db.session.execute(q).scalars():
        groups.setdefault(note.recipe, []).append(note)
    rows = [(recipe, sorted(notes, key=lambda n: n.id)) for recipe, notes in groups.items()]
    return render_template('admin/recipe_notes.html', rows=rows, show_all=show_all, note_time=when)
