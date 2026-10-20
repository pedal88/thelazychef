"""The chef personas, public: who they are and the recipes they made.

Recipes do not show their chef; these pages are where the personas live
(services/recipe_v2/persona.py), and what SoMe content can link to.
"""
from flask import Blueprint, abort, render_template

from database.models import Chef, Recipe, db
from services.chef_service import chef_to_dict
from services.recipe_v2.persona import badges

chefs_bp = Blueprint('chefs', __name__)


def _published(chef_id=None):
    stmt = db.select(Recipe).where(Recipe.status == 'approved', Recipe.chef_id.is_not(None))
    if chef_id:
        stmt = stmt.where(Recipe.chef_id == chef_id)
    return db.session.execute(stmt.order_by(Recipe.id.desc())).scalars().all()


@chefs_bp.route('/chefs')
def index():
    counts = {}
    for r in _published():
        counts[r.chef_id] = counts.get(r.chef_id, 0) + 1
    # Only chefs with a description are personas; bare rows made by old scripts are left out
    chefs = [chef_to_dict(c) for c in db.session.execute(db.select(Chef).order_by(Chef.name)).scalars() if c.description]
    return render_template('chef_personas.html', chefs=[dict(c, badges=badges(c)) for c in chefs], counts=counts)


@chefs_bp.route('/chefs/<chef_id>')
def detail(chef_id):
    chef = db.session.get(Chef, chef_id) or abort(404)
    p = chef_to_dict(chef)
    return render_template('chef_persona.html', chef=dict(p, badges=badges(p)), recipes=_published(chef_id))
