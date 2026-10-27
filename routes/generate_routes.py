"""The New Recipe page: an idea, a video, a web page or pasted text. Every form posts to /new-recipe/v2
(routes/recipe_v2_routes.py), which makes a v2 recipe."""
from flask import render_template
from flask_login import login_required

from routes._flat import FlatBlueprint
from services.chef_service import get_chefs
from utils.decorators import admin_required

generate_bp = FlatBlueprint("generate", __name__)


@generate_bp.route('/new-recipe')
@login_required
@admin_required
def new_recipe():
    # The idea form makes a v2 recipe, which only takes the chefs that are offered now
    return render_template('index.html', chefs=get_chefs(), idea_helper=_idea_helper())


def _idea_helper():
    """The prompt behind "Copy a prompt for your AI": it turns a dish, an idea or a recipe into the best one-line idea."""
    import os

    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'prompts', 'recipe_v2', 'idea_helper.txt')
    with open(path, encoding='utf-8') as f:
        return f.read().rstrip() + '\n'
