import os
from dotenv import load_dotenv

# Load Environment Variables Forcefully BEFORE other imports might need them
load_dotenv()
print(f"--- CONFIG DEBUG: STORAGE_BACKEND={os.getenv('STORAGE_BACKEND')} ---")
print(f"--- CONFIG DEBUG: DB_BACKEND={os.getenv('DB_BACKEND', 'local')} ---")

from flask import Flask, request, url_for
from flask_migrate import Migrate
from flask_login import LoginManager
import markdown
from database.db_connector import configure_database
# The models are re-exported here: many scripts do "from app import app, db, Recipe, ..."
from database.models import db, Ingredient, Recipe, Instruction, RecipeIngredient, RecipeMealType, RecipeDiet, User, Resource, resource_relations, Chef, UserRecipeInteraction, RecipeEvaluation, RecipeCollection, CollectionItem, UserQueue, UserLink, SocialMediaPost, TikTokSource, ConceptVisual, VisualStyleGuide
from services.storage_service import get_storage_provider
from routes._shared import get_recipe_image_url, get_image_url


app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 20 * 1024 * 1024 # 20MB limit

# Register Blueprints
from routes.studio_routes import prompts_bp
app.register_blueprint(prompts_bp)

from routes.admin_collections_routes import collections_bp
app.register_blueprint(collections_bp)

from routes.admin_ingredients_routes import ingredients_bp
app.register_blueprint(ingredients_bp)

from routes.queue_routes import queue_bp
app.register_blueprint(queue_bp)

from routes.media_hub_routes import media_hub_bp
app.register_blueprint(media_hub_bp)

from routes.admin_tiktok_routes import tiktok_bp
app.register_blueprint(tiktok_bp)

from routes.admin_concept_routes import admin_concept_bp
app.register_blueprint(admin_concept_bp)

from routes.admin_style_center import admin_style_center_bp
app.register_blueprint(admin_style_center_bp)


from utils.markdown_extensions import VideoExtension

@app.template_filter('markdown')
def parse_markdown(text):
    if not text: return ""
    return markdown.markdown(text, extensions=['tables', VideoExtension()])

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

@app.template_filter('get_protein_category')
def get_protein_category(protein_name):
    """Finds the Tier 1 category for a given protein name."""
    if not protein_name: return None
    from ai_engine import protein_data
    for category in protein_data:
        if protein_name in category['examples']:
            return category['category']
    return "Other"
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
app.add_template_global(get_image_url)

db.init_app(app)

# Initialize Storage Provider
storage_provider = get_storage_provider(app.root_path)
print(f"--- STORAGE SYSTEM ACTIVE: {storage_provider.__class__.__name__} ---")
app.extensions['storage_provider'] = storage_provider

# Inject storage provider into blueprint context
# Note: Blueprints are registered earlier, but we can attach attributes to the object
prompts_bp.storage_provider = storage_provider
media_hub_bp.storage_provider = storage_provider

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

from routes.resources_routes import resources_bp
app.register_blueprint(resources_bp)

from routes.admin_chefs_routes import admin_chefs_bp
app.register_blueprint(admin_chefs_bp)

from routes.interactions_routes import interactions_bp
app.register_blueprint(interactions_bp)

from routes.admin_image_studio_routes import image_studio_bp
app.register_blueprint(image_studio_bp)

from routes.generate_routes import generate_bp
app.register_blueprint(generate_bp)

from routes.admin_recipes_routes import admin_recipes_bp
app.register_blueprint(admin_recipes_bp)

from routes.recipes_routes import recipes_bp
app.register_blueprint(recipes_bp)

from routes.pantry_routes import pantry_bp
app.register_blueprint(pantry_bp)


if __name__ == '__main__':
    with app.app_context():
        db.create_all() # Ensure tables exist
    debug = os.environ.get('FLASK_DEBUG', '').lower() in ('1', 'true')
    app.run(host='0.0.0.0', debug=debug, port=8000)
