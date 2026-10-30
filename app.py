import os
from dotenv import load_dotenv

# Load Environment Variables Forcefully BEFORE other imports might need them
load_dotenv()
print(f"--- CONFIG DEBUG: STORAGE_BACKEND={os.getenv('STORAGE_BACKEND')} ---")
print(f"--- CONFIG DEBUG: DB_BACKEND={os.getenv('DB_BACKEND', 'local')} ---")

from flask import Flask, request, url_for
from flask_migrate import Migrate
from flask_login import LoginManager
from database.db_connector import configure_database
# The models are re-exported here: many scripts do "from app import app, db, Recipe, ..."
from database.models import db, Ingredient, Recipe, RecipeMealType, RecipeDiet, User, Chef, UserRecipeInteraction, UserQueue, UserLink, ConceptVisual, VisualStyleGuide
from services.storage_service import get_storage_provider
from services.measures import SYSTEMS
from services.recipe_v2 import states
from routes._shared import DIFFICULTY_LABELS, LOOK_FONTS, SITE_LOOK, absolute_url, EQUIPMENT_STYLES, OVERVIEW_LAYOUTS, chosen_overview, IMAGE_STYLES, chosen_equipment_style, dish_images, equipment_image, get_recipe_image_url, get_image_url, icon, notes_text, site_menu, unit_chosen, unit_system


app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 20 * 1024 * 1024 # 20MB limit

# Register Blueprints

from routes.admin_ingredients_routes import ingredients_bp
app.register_blueprint(ingredients_bp)

from routes.queue_routes import queue_bp
app.register_blueprint(queue_bp)

@app.template_filter('parse_chef_dna')
def parse_chef_dna(prompt):
    """Extracts sections from the system prompt for display."""
    sections = {}
    
    if not prompt: return sections
    
    # Normalize newlines
    prompt = str(prompt).replace('\\n', '\n')
    parts = prompt.split('\n')
    
    current_key = "General"
    sections[current_key] = []
    
    for line in parts:
        line = line.strip()
        if not line: continue
        
        lower_line = line.lower()
        if lower_line.startswith("role:"):
            current_key = "Role"
            sections[current_key] = [line[5:].strip()]
        elif lower_line.startswith("philosophy:"):
            current_key = "Philosophy"
            sections[current_key] = [line[11:].strip()]
        elif lower_line.startswith("tone:"):
            current_key = "Tone"
            sections[current_key] = [line[5:].strip()]
        elif lower_line.startswith("rules:"):
            current_key = "Rules"
            sections[current_key] = []
        elif current_key == "Rules" and (line[0].isdigit() or line.startswith('-')):
            sections["Rules"].append(line)
        else:
             # Append to current section
             if current_key in sections:
                sections[current_key].append(line)
             else:
                sections[current_key] = [line]
    return sections
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
if not app.config['SECRET_KEY']:
    if os.environ.get('K_SERVICE'):
        # Running on Cloud Run: never fall back to a guessable key
        raise RuntimeError("SECRET_KEY environment variable must be set in production")
    print("WARNING: SECRET_KEY not set, using a random key (sessions reset on restart)")
    app.config['SECRET_KEY'] = os.urandom(32).hex()
# Database Configuration (Local vs Cloud SQL)
configure_database(app)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize Flask-Migrate
migrate = Migrate(app, db)

@app.template_filter('difficulty_label')
def difficulty_label(level):
    """Stored difficulty (data/constraints/difficulty.json) as shown to readers."""
    return DIFFICULTY_LABELS.get(level, level or '')


@app.context_processor
def utility_processor():
    def update_query_params(**kwargs):
        args = request.args.copy()
        for key, value in kwargs.items():
            args[key] = value
        return url_for(request.endpoint, **args)
    
    return dict(update_query_params=update_query_params)

# Also imported from app by services/evaluation_service.py
app.add_template_global(get_recipe_image_url)
app.add_template_global(absolute_url)
app.add_template_global(get_image_url)
app.add_template_global(icon)
app.add_template_global(site_menu)
app.add_template_global(unit_system)  # the reader's measuring system, for the switch in the menu
app.add_template_global(unit_chosen)
app.add_template_global(SYSTEMS, 'UNIT_SYSTEMS')
app.add_template_global(dish_images)
app.add_template_global(IMAGE_STYLES, 'IMAGE_STYLES')
app.add_template_global(LOOK_FONTS, 'LOOK_FONTS')
app.add_template_global(SITE_LOOK, 'SITE_LOOK')
app.add_template_global(EQUIPMENT_STYLES, 'EQUIPMENT_STYLES')
app.add_template_global(OVERVIEW_LAYOUTS, 'OVERVIEW_LAYOUTS')
app.add_template_global(states.key, 'state_key')  # the signs for what is done to an ingredient (states.json)
app.add_template_global(chosen_overview)
app.add_template_global(chosen_equipment_style)
app.add_template_global(equipment_image)
app.add_template_global(notes_text)

db.init_app(app)

# Initialize Storage Provider
storage_provider = get_storage_provider(app.root_path)
print(f"--- STORAGE SYSTEM ACTIVE: {storage_provider.__class__.__name__} ---")
app.extensions['storage_provider'] = storage_provider

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# Routes moved out of app.py. FlatBlueprint keeps their original endpoint names.
from routes.auth_routes import auth_bp
app.register_blueprint(auth_bp)

from routes.mirror_routes import mirror_bp
app.register_blueprint(mirror_bp)

from routes.explore_routes import explore_bp
app.register_blueprint(explore_bp)

from routes.admin_chefs_routes import admin_chefs_bp
app.register_blueprint(admin_chefs_bp)

from routes.interactions_routes import interactions_bp
app.register_blueprint(interactions_bp)


from routes.generate_routes import generate_bp
app.register_blueprint(generate_bp)

from routes.admin_recipes_routes import admin_recipes_bp
app.register_blueprint(admin_recipes_bp)

from routes.recipes_routes import recipes_bp
app.register_blueprint(recipes_bp)

from routes.pantry_routes import pantry_bp
from routes.recipe_v2_routes import recipe_v2_bp
app.register_blueprint(pantry_bp)
app.register_blueprint(recipe_v2_bp)

from routes.chefs_routes import chefs_bp
app.register_blueprint(chefs_bp)

from routes.recipe_notes_routes import notes_bp
app.register_blueprint(notes_bp)

from routes.content_routes import content_bp
app.register_blueprint(content_bp)

from routes.content_api_routes import content_api_bp
app.register_blueprint(content_api_bp)

from routes.funnel_routes import funnel_bp
app.register_blueprint(funnel_bp)

from routes.social_routes import social_bp
app.register_blueprint(social_bp)


if __name__ == '__main__':
    with app.app_context():
        db.create_all() # Ensure tables exist
    debug = os.environ.get('FLASK_DEBUG', '').lower() in ('1', 'true')
    app.run(host='0.0.0.0', debug=debug, port=8000)
