import os
from dotenv import load_dotenv
import io

# Load Environment Variables Forcefully BEFORE other imports might need them
load_dotenv()
print(f"--- CONFIG DEBUG: STORAGE_BACKEND={os.getenv('STORAGE_BACKEND')} ---")
print(f"--- CONFIG DEBUG: DB_BACKEND={os.getenv('DB_BACKEND', 'local')} ---")

import uuid
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, abort
from slugify import slugify
from flask_migrate import Migrate
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
import markdown
from database.db_connector import configure_database
from database.models import db, Ingredient, Recipe, Instruction, RecipeIngredient, RecipeMealType, RecipeDiet, User, Resource, resource_relations, Chef, UserRecipeInteraction, RecipeEvaluation, RecipeCollection, CollectionItem, UserQueue
from utils.decorators import admin_required
from sqlalchemy import or_, func
from sqlalchemy.orm import joinedload
from sqlalchemy.orm.attributes import flag_modified
from services.pantry_service import get_slim_pantry_context
from ai_engine import generate_recipe_ai, get_pantry_id, get_top_pantry_suggestions, chefs_data, generate_recipe_from_web_text, analyze_ingredient_ai, extract_nutrients_from_text, load_controlled_vocabularies
from services.recipe_service import process_recipe_workflow, STATUS_SUCCESS, STATUS_MISSING
from services.photographer_service import generate_visual_prompt, generate_actual_image, generate_visual_prompt_from_image, load_photographer_config, generate_image_variation, process_external_image
from services.vertex_image_service import VertexImageGenerator
from services.web_scraper_service import WebScraper
from services.storage_service import get_storage_provider, GoogleCloudStorageProvider
from utils.image_helpers import generate_ingredient_placeholder
import base64
from io import BytesIO
from urllib.parse import urlencode
import shutil
import datetime
from sqlalchemy import func
from utils.prompt_manager import load_prompt

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
app.config['SECRET_KEY'] = 'dev-key-secret'
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

@app.template_global()
def get_recipe_image_url(recipe):
    """Generates the correct URL for a recipe image based on storage backend."""
    if not recipe or not recipe.image_filename:
        return None
    
    # If using GCS, return the public URL directly
    # We construct it manually or use storage_provider if it had a get_url method
    # But for now, we know the pattern or can assume public access for simplicity
    # The storage provider saves as "recipes/<filename>" or just "<filename>" in recipes folder?
    # Let's check storage provider usage.
    
    # Access global storage_provider
    is_gcs = isinstance(storage_provider, GoogleCloudStorageProvider)
    
    if is_gcs:
        # GCS Public URL Convention: https://storage.googleapis.com/<bucket>/<blob_path>
        # The app saves/moves items to "recipes" folder.
        return f"https://storage.googleapis.com/{storage_provider.bucket_name}/recipes/{recipe.image_filename}"
    else:
        # Local Flask Static
        return url_for('static', filename='recipes/' + recipe.image_filename)

@app.template_global()
def get_image_url(filename):
    """Translates a raw filename to its full public URL based on the active storage backend."""
    if not filename:
        return ""
    
    is_gcs = isinstance(storage_provider, GoogleCloudStorageProvider)
    if is_gcs:
        return f"https://storage.googleapis.com/{storage_provider.bucket_name}/recipes/{filename}"
    else:
        return url_for('static', filename='recipes/' + filename)

db.init_app(app)

# Initialize Storage Provider
storage_provider = get_storage_provider(app.root_path)
print(f"--- STORAGE SYSTEM ACTIVE: {storage_provider.__class__.__name__} ---")

# Inject storage provider into blueprint context
# Note: Blueprints are registered earlier, but we can attach attributes to the object
prompts_bp.storage_provider = storage_provider

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# AUTH ROUTES
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
         return redirect(url_for('studio_view') if current_user.is_admin else url_for('recipes_list'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = db.session.execute(db.select(User).where(User.email == email)).scalar()
        
        if user and user.check_password(password):
            login_user(user)
            next_page = request.args.get('next')
            # Intelligent Redirect based on Role
            if not next_page:
                next_page = url_for('studio_view') if user.is_admin else url_for('recipes_list')
            return redirect(next_page)
        
        flash('Invalid email or password', 'error')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
         return redirect(url_for('recipes_list'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        # Validation
        existing_user = db.session.execute(db.select(User).where(User.email == email)).scalar()
        if existing_user:
            flash('Email already registered', 'error')
            return redirect(url_for('register'))
            
        # Create User
        new_user = User(email=email, is_admin=False)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        
        # Auto Login
        login_user(new_user)
        flash('Account created successfully!', 'success')
        return redirect(url_for('recipes_list'))
        
    return render_template('register.html')

@app.route('/logout')
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('discover'))

@app.route('/api/me/favorites', methods=['GET'])
@login_required
def get_user_favorites():
    """Returns a list of recipe IDs favorited by the current user."""
    # Efficiently fetch only the IDs
    # Using the relationship:
    fav_ids = [i.recipe_id for i in current_user.interactions if i.status == 'favorite']
    return jsonify({'favorite_ids': fav_ids})

@app.route('/api/recipes/<int:recipe_id>/favorite', methods=['POST'])
@login_required
def toggle_favorite_recipe(recipe_id):
    """Toggles the favorite status of a recipe for the current user."""
    # Updated to use UserRecipeInteraction
    stmt = db.select(UserRecipeInteraction).where(
        UserRecipeInteraction.user_id == current_user.id,
        UserRecipeInteraction.recipe_id == recipe_id
    )
    interaction = db.session.execute(stmt).scalar()

    if interaction:
        if interaction.status == 'favorite':
            # Toggle OFF: Remove the favorite status (delete interaction to allow re-discovery or set to pass?)
            # For now, deleting the interaction is safest for toggle behavior on list view
            db.session.delete(interaction)
            status = 'removed'
        else:
            # Update to favorite
            interaction.status = 'favorite'
            interaction.timestamp = datetime.datetime.utcnow()
            status = 'added'
    else:
        # Create new favorite
        interaction = UserRecipeInteraction(
            user_id=current_user.id,
            recipe_id=recipe_id,
            status='favorite'
        )
        db.session.add(interaction)
        status = 'added'
        
    db.session.commit()
    return jsonify({'status': status, 'recipe_id': recipe_id})

@app.route('/api/feed/recipes', methods=['GET'])
def get_feed_recipes():
    """Returns a list of random recipes for the feed (Tinder-style)."""
    limit = 10
    
    if current_user.is_authenticated:
        # Priority 1: Exclude recipes user has interacted with (new ones only)
        subq_all = db.select(UserRecipeInteraction.recipe_id).where(UserRecipeInteraction.user_id == current_user.id)
        stmt = (
            db.select(Recipe)
            .where(Recipe.status == 'approved')  # Public guard
            .where(Recipe.id.not_in(subq_all))
            .order_by(func.random())
            .limit(limit)
        )
        recipes = db.session.execute(stmt).scalars().all()
        
        # Priority 2: If we've seen everything, shuffle through the "no" stack
        if not recipes:
            subq_pass = db.select(UserRecipeInteraction.recipe_id).where(
                UserRecipeInteraction.user_id == current_user.id,
                UserRecipeInteraction.status == 'pass'
            )
            stmt = (
                db.select(Recipe)
                .where(Recipe.status == 'approved')
                .where(Recipe.id.in_(subq_pass))
                .order_by(func.random())
                .limit(limit)
            )
            recipes = db.session.execute(stmt).scalars().all()
    else:
        # Anonymous: Random selection of approved only
        stmt = db.select(Recipe).where(Recipe.status == 'approved').order_by(func.random()).limit(limit)
        recipes = db.session.execute(stmt).scalars().all()
    
    data = []
    for r in recipes:
        data.append({
            'id': r.id,
            'title': r.title,
            'image_url': get_recipe_image_url(r),
            'cuisine': r.cuisine,
            'time_estimate': r.prep_time_mins or 30, # Default if missing
            'difficulty': r.difficulty
        })
        
    return jsonify({'recipes': data, 'has_more': len(data) == limit})

@app.route('/api/interactions/recipe/<int:recipe_id>', methods=['POST'])
@login_required
def handle_interaction(recipe_id):
    """Handle Tinder-style interactions: pass, like, super_like."""
    data = request.get_json()
    action = data.get('action') 
    
    if action not in ['pass', 'like', 'super_like']:
        return jsonify({'error': 'Invalid action'}), 400
        
    # Map action to data model
    if action == 'pass':
        status = 'pass'
        is_super = False
    elif action == 'like':
        status = 'favorite'
        is_super = False
    elif action == 'super_like':
        status = 'favorite'
        is_super = True
        
    # Upsert Interaction
    interaction = db.session.get(UserRecipeInteraction, (current_user.id, recipe_id))
    if interaction:
        interaction.status = status
        interaction.is_super_like = is_super
        interaction.timestamp = datetime.datetime.utcnow()
    else:
        interaction = UserRecipeInteraction(
            user_id=current_user.id, 
            recipe_id=recipe_id, 
            status=status, 
            is_super_like=is_super
        )
        db.session.add(interaction)
        
    db.session.commit()
    return jsonify({'success': True})


@app.route('/api/interactions/recipe/<int:recipe_id>/made', methods=['PATCH'])
@login_required
def toggle_made(recipe_id):
    """Toggle the is_made flag on an existing interaction (must already be a favorite)."""
    interaction = db.session.get(UserRecipeInteraction, (current_user.id, recipe_id))
    if not interaction:
        # Create a minimal interaction so we can track made status
        interaction = UserRecipeInteraction(
            user_id=current_user.id,
            recipe_id=recipe_id,
            status='pass',  # Not a favorite, just cooked
            is_super_like=False
        )
        db.session.add(interaction)

    interaction.is_made = not interaction.is_made
    db.session.commit()
    return jsonify({'success': True, 'is_made': interaction.is_made})


@app.route('/api/interactions/recipe/<int:recipe_id>/feedback', methods=['POST'])
@login_required
def save_feedback(recipe_id):
    """Save user feedback: star rating, comment, and optional photo uploads.

    Accepts JPG, PNG, GIF, WEBP, and HEIC/HEIF (Apple iPhone format).
    HEIC files are converted to JPEG before storage because browsers
    cannot natively render HEIC.
    """
    # Register HEIF/HEIC support into Pillow (idempotent; safe to call each request)
    import pillow_heif
    pillow_heif.register_heif_opener()
    from PIL import Image as PilImage

    # Get or create interaction
    interaction = db.session.get(UserRecipeInteraction, (current_user.id, recipe_id))
    if not interaction:
        interaction = UserRecipeInteraction(
            user_id=current_user.id,
            recipe_id=recipe_id,
            status='pass',
            is_super_like=False
        )
        db.session.add(interaction)

    # Update feedback fields
    rating_raw = request.form.get('rating')
    if rating_raw and rating_raw.isdigit():
        rating_int = int(rating_raw)
        if 1 <= rating_int <= 5:
            interaction.rating = rating_int

    comment_raw = request.form.get('comment', '').strip()
    if comment_raw:
        interaction.comment = comment_raw

    # Handle photo uploads
    ALLOWED_EXTS = {'jpg', 'jpeg', 'png', 'gif', 'webp', 'heic', 'heif'}
    HEIC_EXTS    = {'heic', 'heif'}

    # `keep_photos` is a JSON list of previously saved URLs the user chose to keep.
    # If the client sends it, use it as the base. This allows photo deletion:
    # the frontend simply omits the deleted URL from keep_photos.
    # If not sent (e.g. old clients), fall back to the full existing list.
    import json as _json
    keep_raw = request.form.get('keep_photos')
    if keep_raw is not None:
        try:
            base_urls: list[str] = _json.loads(keep_raw)
            # Sanity-check: only keep URLs that were actually in the stored list
            stored = set(interaction.user_photos or [])
            base_urls = [u for u in base_urls if u in stored]
        except (ValueError, TypeError):
            base_urls = list(interaction.user_photos or [])
    else:
        base_urls = list(interaction.user_photos or [])

    new_urls: list[str] = base_urls
    photos = request.files.getlist('photos')

    for photo in photos[:5]:  # Cap at 5 new uploads per submission
        if not photo or not photo.filename:
            continue
        ext = photo.filename.rsplit('.', 1)[-1].lower()
        if ext not in ALLOWED_EXTS:
            continue

        file_bytes = photo.read()

        # Convert HEIC/HEIF → JPEG so browsers can display the result
        if ext in HEIC_EXTS:
            try:
                img = PilImage.open(io.BytesIO(file_bytes))
                buf = io.BytesIO()
                img.convert('RGB').save(buf, format='JPEG', quality=90)
                file_bytes = buf.getvalue()
                ext = 'jpg'
            except Exception as e:
                print(f"HEIC conversion error for {photo.filename}: {e}")
                continue

        filename = f"user_{current_user.id}_recipe_{recipe_id}_{uuid.uuid4().hex[:8]}.{ext}"
        try:
            url = storage_provider.save(file_bytes, filename, 'user_uploads')
            new_urls.append(url)
        except Exception as e:
            print(f"Photo upload error: {e}")

    interaction.user_photos = new_urls
    flag_modified(interaction, 'user_photos')  # Force SQLAlchemy to dirty-track JSON column
    db.session.commit()
    return jsonify({'success': True})


@app.route('/api/interactions/recipe/<int:recipe_id>', methods=['GET'])
@login_required
def get_interaction(recipe_id):
    """Returns stored interaction data for the current user + recipe.
    
    Used by the feedback drawer to pre-populate rating, comment, and photos.
    """
    interaction = db.session.get(UserRecipeInteraction, (current_user.id, recipe_id))
    if not interaction:
        return jsonify({
            'exists': False,
            'rating': None,
            'comment': None,
            'user_photos': [],
            'is_made': False,
        })
    return jsonify({
        'exists': True,
        'rating': interaction.rating,
        'comment': interaction.comment or '',
        'user_photos': interaction.user_photos or [],
        'is_made': interaction.is_made,
        'is_super_like': interaction.is_super_like,
    })


@app.route('/saved-recipes')
@login_required
def saved_recipes_view():
    """Legacy route: Redirects to the unified library view."""
    return redirect(url_for('recipes_list', view='saved'))
    


# PHOTOGRAPHER ROUTES

@app.route('/admin/studio', methods=['GET', 'POST'])
@login_required
@admin_required
def studio_view():
    prompt = None
    recipe_text = ""
    recipe_id = None
    ingredients_list = ""
    
    config = load_photographer_config()
    
    # Check if we were sent here from a recipe page
    if request.args.get('recipe_text'):
        recipe_text = request.args.get('recipe_text')
    
    if request.args.get('recipe_id'):
        recipe_id = request.args.get('recipe_id')

    if request.args.get('ingredients_list'):
        ingredients_list = request.args.get('ingredients_list')
    
    if request.method == 'POST':
        recipe_text = request.form.get('recipe_text')
        recipe_id = request.form.get('recipe_id')
        ingredients_list = request.form.get('ingredients_list')
        
        # Check for Image Upload (Option 1B)
        if 'reference_image' in request.files and request.files['reference_image'].filename != '':
            file = request.files['reference_image']
            image_bytes = file.read()
            prompt = generate_visual_prompt_from_image(image_bytes)
            
        # Fallback to Text (Option 1A)
        elif recipe_text:
            prompt = generate_visual_prompt(recipe_text, ingredients_list)
            
            
    return render_template('studio.html', 
                         config=config, 
                         prompt=prompt, 
                         recipe_text=recipe_text,
                         recipe_id=recipe_id,
                         ingredients_list=ingredients_list)

@app.route('/admin/studio/snap', methods=['POST'])
@login_required
@admin_required
def studio_snap():
    prompt = request.form.get('visual_prompt')
    recipe_text = request.form.get('recipe_text') # Retrieve context
    recipe_id = request.form.get('recipe_id')
    ingredients_list = request.form.get('ingredients_list')
    config = load_photographer_config()

    if not prompt:
        return redirect(url_for('studio_view'))
        
    try:
        # Generate the Image
        img = generate_actual_image(prompt)
        
        # Save to Temp via Storage Provider
        filename = f"temp_{uuid.uuid4().hex}.png"
        
        # Convert PIL to Bytes
        img_byte_arr = BytesIO()
        img.save(img_byte_arr, format='PNG')
        img_bytes = img_byte_arr.getvalue()
        
        public_url = storage_provider.save(img_bytes, filename, "temp")
        
        # Render template with the image filename/URL AND context
        # Note: 'temp_image' variable now expects just the filename for some logic 
        # OR the URL? The template uses `url_for('static', filename='temp/'+temp_image)` usually.
        # If we return a URL from GCS, we can't wrap it in `url_for('static')`.
        # We need to pass the FULL URL.
        # But let's check studio.html usage later. unique filename is safer for now if local.
        # If local, storage.save returns "/static/temp/filename.png"
        # If GCS, it returns "https://..."
        
        # Let's pass the full URL to the template as 'temp_image_url' and update template?
        # OR keep 'temp_image' as filename, and 'temp_image_full_url' as the public url.
        
        return render_template('studio.html', 
                             config=config, 
                             prompt=prompt, 
                             recipe_text=recipe_text,
                             recipe_id=recipe_id,
                             ingredients_list=ingredients_list,
                             temp_image=filename,
                             temp_image_url=public_url) # New variable
                             
    except Exception as e:
        flash(f"Error generating image: {str(e)}", "error")
        # Log the full error
        print(f"Error generating image: {e}")
        return render_template('studio.html', 
                             config=config, 
                             prompt=prompt, 
                             recipe_text=recipe_text,
                             recipe_id=recipe_id,
                             ingredients_list=ingredients_list)

@app.route('/admin/studio/save', methods=['POST'])
@login_required
@admin_required
def save_recipe_image():
    filename = request.form.get('filename')
    recipe_id = request.form.get('recipe_id')
    
    if not filename or not recipe_id:
        flash("Missing data to save image", "error")
        return redirect(url_for('discover'))
        
    try:
        # Move file from temp to recipes
        # Use simple storage abstraction
        new_filename = f"recipe_{recipe_id}_{uuid.uuid4().hex[:8]}.png"
        
        # Move: Temp -> Recipes
        storage_provider.move(filename, "temp", new_filename, "recipes")
        
        # Update DB
        recipe = db.session.get(Recipe, int(recipe_id))
        if recipe:
            recipe.image_filename = new_filename
            db.session.commit()
            flash("Image saved to recipe!", "success")
            return redirect(url_for('recipe_detail', recipe_id=recipe_id))
        else:
             flash("Recipe not found", "error")
             return redirect(url_for('discover'))

    except Exception as e:
        print(f"DEBUG SAVE ERROR: {e}")
        flash(f"Error saving image: {str(e)}", "error")
        return redirect(url_for('discover')) 


@app.route('/admin/studio/analyze', methods=['POST'])
@login_required
@admin_required
def studio_analyze():
    try:
        # A1: Text Input -> Generate Prompt
        text_a1 = request.form.get('text_a1', '')
        prompt_b1 = ""
        if text_a1:
            prompt_b1 = generate_visual_prompt(text_a1)
        
        # A2: Image Input (for Image-to-Prompt)
        prompt_a2 = ""
        if 'image_a2' in request.files and request.files['image_a2'].filename != '':
            file = request.files['image_a2']
            image_bytes = file.read()
            prompt_a2 = generate_visual_prompt_from_image(image_bytes)
            
        # A3: Image Input (for Remix) - We just confirm it's valid/received, 
        # but the prompt is fixed.
        # Maybe we could do a quick check? 
        
        # Get Fixed Prompt from Config
        config = load_photographer_config()
        # Create a specific "Enhancer" prompt or just use the system prompt
        # User requested: "Cookbook Style" with Template
        prompt_b3 = load_prompt('recipe_image/style_remix.jinja2', ingredient_name='[Ingredient Name]')

        return jsonify({
            'success': True,
            'row1': prompt_b1, 
            'row2': prompt_a2,
            'row3': prompt_b3
        })

    except Exception as e:
        print(f"Analyze Error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/admin/studio/generate', methods=['POST'])
@login_required
@admin_required
def studio_generate():
    try:
        # B1: Text-to-Image
        prompt_b1 = request.form.get('prompt_b1')
        img_c1_url = None
        if prompt_b1:
            img = generate_actual_image(prompt_b1)[0]
            filename = f"studio_a_{uuid.uuid4().hex}.png"
            
            # Save via Storage
            img_byte_arr = BytesIO()
            img.save(img_byte_arr, format='PNG')
            img_c1_url = storage_provider.save(img_byte_arr.getvalue(), filename, "temp")

        # B2: Image-to-Prompt-to-Image
        prompt_b2 = request.form.get('prompt_b2')
        img_c2_url = None
        if prompt_b2:
            img = generate_actual_image(prompt_b2)[0]
            filename = f"studio_b_{uuid.uuid4().hex}.png"
            
            # Save via Storage
            img_byte_arr = BytesIO()
            img.save(img_byte_arr, format='PNG')
            img_c2_url = storage_provider.save(img_byte_arr.getvalue(), filename, "temp")
            
        # B3: Mix (Image + Fixed Prompt)
        prompt_b3 = request.form.get('prompt_b3')
        img_c3_url = None
        
        # We need the image from A3 again. 
        # NOTE: Ideally we would have saved it to a temp path in /analyze and passed the path.
        # But for this stateless implementation, we expect the frontend to re-send the file 
        # OR we rely on the file being present in request.files if the user selected it.
        if 'image_a3' in request.files and request.files['image_a3'].filename != '' and prompt_b3:
            file = request.files['image_a3']
            image_bytes = file.read()
            # Variation Generation
            img = generate_image_variation(image_bytes, prompt_b3)[0]
            filename = f"studio_c_{uuid.uuid4().hex}.png"
            
            # Save via Storage
            img_byte_arr = BytesIO()
            img.save(img_byte_arr, format='PNG')
            img_c3_url = storage_provider.save(img_byte_arr.getvalue(), filename, "temp")

        return jsonify({
            'success': True,
            'image_c1': img_c1_url,
            'image_c2': img_c2_url,
            'image_c3': img_c3_url
        })

    except Exception as e:
        print(f"Generate Error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# RECIPE IMAGE GENERATION FLOW
@app.route('/recipe-image-generation')
@login_required
@admin_required
def recipe_image_generation_view():
    recipe_id = request.args.get('recipe_id')
    if not recipe_id:
        flash("Recipe ID required", "error")
        return redirect(url_for('discover'))
    
    recipe = db.session.get(Recipe, int(recipe_id))
    if not recipe:
        flash("Recipe not found", "error")
        return redirect(url_for('discover'))
        
    return render_template('recipe_photographer.html', recipe=recipe)

@app.route('/recipe-image-generation/prompt', methods=['POST'])
@login_required
@admin_required
def recipe_image_generation_prompt():
    try:
        data = request.get_json()
        recipe_id = data.get('recipe_id')
        recipe = db.session.get(Recipe, int(recipe_id))
        
        if not recipe:
            return jsonify({'success': False, 'error': 'Recipe not found'})
            
        # Reconstruct Context for AI
        ingredients_list = ", ".join([ri.ingredient.name for ri in recipe.ingredients])
        
        recipe_text = f"Title: {recipe.title}\n"
        recipe_text += f"Cuisine: {recipe.cuisine}\n"
        recipe_text += f"Diets: {', '.join(recipe.diets_list)}\n"
        
        # Generate Prompt
        prompt = generate_visual_prompt(recipe_text, ingredients_list)
        
        return jsonify({'success': True, 'prompt': prompt})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/recipe-image-generation/generate', methods=['POST'])
@login_required
@admin_required
def recipe_image_generation_create():
    try:
        data = request.get_json()
        prompt = data.get('prompt')
        
        if not prompt:
            return jsonify({'success': False, 'error': 'Prompt required'})
            
        # Generate Image
        try:
            # Check if using Vertex or Photographer Service
            # For now, assuming generate_actual_image returns a list of PIL images
            images = generate_actual_image(prompt)
            if not images:
                 return jsonify({'success': False, 'error': 'No image generated'})
            img = images[0]
        except Exception as e:
             print(f"Error calling AI generation: {e}")
             return jsonify({'success': False, 'error': f"Generation failed: {str(e)}"})
             
        # Save to Temp
        filename = f"temp_{uuid.uuid4().hex}.png"
        
        # Save via Storage
        img_byte_arr = BytesIO()
        img.save(img_byte_arr, format='PNG')
        file_url = storage_provider.save(img_byte_arr.getvalue(), filename, "temp")
        
        return jsonify({'success': True, 'filename': filename, 'url': file_url})
        
    except Exception as e:
        print(f"Gen Error: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/recipe-image-generation/save', methods=['POST'])
@login_required
@admin_required
def recipe_image_generation_save():
    try:
        data = request.get_json()
        filename = data.get('filename')
        recipe_id = data.get('recipe_id')
        
        if not filename or not recipe_id:
            return jsonify({'success': False, 'error': 'Missing data'})
            
        # Move file using Storage Provider (Abstracts Local vs Cloud)
        new_filename = f"recipe_{recipe_id}_{uuid.uuid4().hex[:8]}.png"
        
        try:
            # Move from 'temp' to 'recipes'
            storage_provider.move(filename, "temp", new_filename, "recipes")
            
            # Update DB
            recipe = db.session.get(Recipe, int(recipe_id))
            recipe.image_filename = new_filename
            db.session.commit()
            
            return jsonify({'success': True})
            
        except FileNotFoundError:
             return jsonify({'success': False, 'error': 'Temp file not found or expired'})
            
    except Exception as e:
        print(f"Save Logic Error: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/new-recipe', methods=['GET', 'POST'])
def new_recipe():
    if request.method == 'POST':
        query = request.form.get('query')
        chef_id = request.form.get('chef_id', 'gourmet')
        if query:
            return redirect(url_for('generate', query=query, chef_id=chef_id))
    
    # Get recent recipes (approved only for public display)
    recent_recipes = db.session.execute(db.select(Recipe).where(Recipe.status == 'approved').order_by(Recipe.id.desc()).limit(10)).scalars().all()
    return render_template('index.html', recipes=recent_recipes, chefs=chefs_data)

@app.route('/')
def discover():
    # Load Recent Recipes (approved only)
    recent_recipes = db.session.execute(db.select(Recipe).where(Recipe.status == 'approved').order_by(Recipe.id.desc()).limit(8)).scalars().all()
    
    # Load Resources
    resources = load_resources()
    
    return render_template('landing.html', recipes=recent_recipes, resources=resources)

def load_resources():
    try:
        data_dir = os.path.join(app.root_path, 'data')
        with open(os.path.join(data_dir, 'resources.json'), 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading resources: {e}")
        return []

@app.route('/become-a-chef')
def resources_list():
    resources = db.session.execute(db.select(Resource).where(Resource.status == 'published').order_by(Resource.created_at.desc())).scalars().all()
    return render_template('resources.html', resources=resources)

@app.route('/become-a-chef/<slug>')
def resource_detail(slug):
    # Try fetching by slug first
    resource = db.session.execute(db.select(Resource).where(Resource.slug == slug)).scalar_one_or_none()
    
    # Fallback to ID if not found (for legacy support if needed, though slug is preferred)
    if not resource:
         try:
             r_id = int(slug)
             resource = db.session.get(Resource, r_id)
         except ValueError:
             pass

    if not resource:
        flash("Article not found", "error")
        return redirect(url_for('resources_list'))
    
    # Related resources are already available via relationship
    # But for template compatibility if it expects a list, resource.related_resources is a dynamic loader
    # so we need to iterate or convert to list. The template iterates.
    # We might need to pass related_resources explicitly if template expects it separate from resource object
    # The existing template uses `related_resources` variable passed to it.
    
    # Convert dynamic relationship query to list
    related = resource.related_resources.all()
        
    return render_template('resource_detail.html', resource=resource, related_resources=related)

import json

def load_json_option(filename, key):
    data_dir = os.path.join(app.root_path, 'data')
    try:
        with open(os.path.join(data_dir, filename), 'r') as f:
            return json.load(f).get(key, [])
    except:
        return []

@app.route('/admin/chefs')
@login_required
@admin_required
def chefs_list():
    diets_data = load_json_option('diets_tag.json', 'diets')
    
    # Load Cooking Methods (Grouped)
    methods_data_raw = load_json_option('cooking_methods.json', 'cooking_methods')
    grouped_methods = {}
    for m in methods_data_raw:
        cat = m['category']
        if cat not in grouped_methods:
            grouped_methods[cat] = []
        grouped_methods[cat].append(m['method'])
    
    # Sort keys
    grouped_methods = dict(sorted(grouped_methods.items()))
    
    return render_template('chefs.html', chefs=chefs_data, diets_list=diets_data, grouped_methods=grouped_methods)

@app.route('/admin/chefs/save', methods=['POST'])
@login_required
@admin_required
def save_chefs_json():
    try:
        data = request.get_json()
        if not data or 'chefs' not in data:
            return jsonify({'success': False, 'error': 'Invalid JSON structure'}), 400
        
        new_chefs = data['chefs']
        
        # Validate/Persist
        json_path = os.path.join(os.path.dirname(__file__), "data", "chefs.json")
        
        # We replace the entire list with the new data from UI
        # But we should preserve structure wrappers if any
        full_data = {"chefs": new_chefs}
        
        with open(json_path, 'w') as f:
            json.dump(full_data, f, indent=2)
            
        # Update in-memory reference
        global chefs_data
        chefs_data = new_chefs
        
        # Also need to update cache in ai_engine if it's imported there
        # Since ai_engine loads on import, we might need a reload mechanism 
        # or just let the app restart handle it. 
        # For this dev server, a restart is often best, but let's try to update the reference if shared.
        import ai_engine
        ai_engine.chefs_data = new_chefs
        ai_engine.chef_map = {c['id']: c for c in new_chefs}

        return jsonify({'success': True})
        
    except Exception as e:
        print(f"Error saving chefs: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/recipes')
def recipes_list():
    # 1. Load Filter Data Options
    # Use global load_json_option helper

    cuisine_options = load_json_option('post_processing/cuisines.json', 'cuisines')
    diet_options = load_json_option('constraints/diets.json', 'diets')
    difficulty_options = load_json_option('constraints/difficulty.json', 'difficulty')
    
    # Protein Types (List of Dicts -> List of Strings)
    pt_data = load_json_option('constraints/main_protein.json', 'protein_types')
    protein_options = []
    for p in pt_data:
        if 'examples' in p:
            protein_options.extend(p['examples'])
    protein_options = sorted(list(set(protein_options)))
    
    # Meal Types (Dict of Lists -> Flattened List)
    mt_data = load_json_option('constraints/meal_types.json', 'meal_classification')
    meal_type_options = []
    if isinstance(mt_data, dict):
        for category_list in mt_data.values():
            if isinstance(category_list, list):
                meal_type_options.extend(category_list)
    meal_type_options = sorted(list(set(meal_type_options)))

    # 2. Handle Query Params (multi-select)
    # Default to ALL options if not specified (First load behavior)
    selected_cuisines = request.args.getlist('cuisine')
    if not selected_cuisines and 'cuisine' not in request.args:
        selected_cuisines = cuisine_options
        
    selected_diets = request.args.getlist('diet')
    if not selected_diets and 'diet' not in request.args:
        selected_diets = diet_options

    selected_meal_types = request.args.getlist('meal_type')
    if not selected_meal_types and 'meal_type' not in request.args:
        selected_meal_types = meal_type_options
    
    selected_difficulties = request.args.getlist('difficulty')
    selected_proteins = request.args.getlist('protein_type')

    # 3. Handle View Mode & Base Query
    view_mode = request.args.get('view', 'discover')
    
    # Session Persistence for View Style
    if 'style' in request.args:
        from flask import session
        session['view_style'] = request.args.get('style')
        
    # Get current style from session or default to grid
    from flask import session
    view_style = session.get('view_style', 'grid')

    if view_mode == 'saved' and current_user.is_authenticated:
        # Base query for Saved Recipes
        stmt = (
            db.select(Recipe, UserRecipeInteraction)
            .join(UserRecipeInteraction)
            .where(
                UserRecipeInteraction.user_id == current_user.id,
                UserRecipeInteraction.status == 'favorite',
                Recipe.status == 'approved'
            )
            .order_by(
                UserRecipeInteraction.is_super_like.desc(),
                UserRecipeInteraction.timestamp.desc()
            )
        )
    elif view_mode == 'next' and current_user.is_authenticated:
        # Base query for Queue
        from database.models import UserQueue
        stmt = (
            db.select(Recipe, UserQueue)
            .join(UserQueue)
            .where(
                UserQueue.user_id == current_user.id,
                Recipe.status == 'approved'
            )
            .order_by(UserQueue.position.asc())
        )
    else:
        # Default Discover query
        view_mode = 'discover'
        stmt = db.select(Recipe).where(Recipe.status == 'approved').order_by(Recipe.id.desc())

    # 4. Apply Filters — only when the user has chosen a STRICT SUBSET of the available options.
    # The default "select all" state should not restrict results at all.
    # Using .any() with a full option list would exclude recipes that have NO tags,
    # which is incorrect for newly added recipes that lack meal_types or diets.
    if selected_cuisines and len(selected_cuisines) < len(cuisine_options):
        stmt = stmt.where(Recipe.cuisine.in_(selected_cuisines))

    if selected_diets and len(selected_diets) < len(diet_options):
        stmt = stmt.where(Recipe.diets.any(RecipeDiet.diet.in_(selected_diets)))

    if selected_difficulties:
        stmt = stmt.where(Recipe.difficulty.in_(selected_difficulties))

    if selected_proteins:
        clauses = []
        for p in selected_proteins:
            clauses.append(Recipe.ingredients.any(
                RecipeIngredient.ingredient.has(Ingredient.name.ilike(f'%{p}%'))
            ))
        if clauses:
             stmt = stmt.where(or_(*clauses))

    if selected_meal_types and len(selected_meal_types) < len(meal_type_options):
        stmt = stmt.where(Recipe.meal_types.any(RecipeMealType.meal_type.in_(selected_meal_types)))

    # Fetch results
    results = db.session.execute(stmt).all()
    
    recipes = []
    if view_mode in ['saved', 'next']:
        for item in results:
            r = item[0]
            # Attach interaction data to recipe object for template
            if view_mode == 'saved':
                interaction = item[1]
                r.is_super_liked = interaction.is_super_like
                r.interaction = interaction
            elif view_mode == 'next':
                queue_item = item[1]
                r.queue_position = queue_item.position
            recipes.append(r)
    else:
        recipes = [item[0] for item in results]

    return render_template('recipes_list.html', 
                         recipes=recipes,
                         current_view=view_mode,
                         view_style=view_style,
                         cuisine_options=sorted(cuisine_options),
                         diet_options=sorted(diet_options),
                         difficulty_options=difficulty_options,
                         protein_options=sorted(protein_options),
                         meal_type_options=meal_type_options,
                         # Selected State
                         selected_cuisines=selected_cuisines,
                         selected_diets=selected_diets,
                         selected_meal_types=selected_meal_types,
                         selected_difficulties=selected_difficulties,
                         selected_proteins=selected_proteins)

@app.route('/admin/recipes-management')
@login_required
@admin_required
def admin_recipes_management():
    # Sorting & pagination parameters
    sort_col = request.args.get('sort', 'id')
    sort_dir = request.args.get('dir', 'desc')
    page = request.args.get('page', 1, type=int)
    search_term = request.args.get('search', '').lower().strip()
    per_page = 50

    # Filter parameters
    selected_cuisines = request.args.getlist('cuisine')
    selected_diets = request.args.getlist('diet')
    selected_meal_types = request.args.getlist('meal_type')
    selected_proteins = request.args.getlist('protein')
    selected_difficulties = request.args.getlist('difficulty')
    selected_statuses = request.args.getlist('status')

    # Load Vocabs for filters
    vocab = load_controlled_vocabularies()
    cuisine_options = vocab.get('cuisines', [])
    diet_options = vocab.get('diets', [])
    meal_type_options = vocab.get('meal_types', [])
    protein_options = vocab.get('proteins', [])
    difficulty_options = vocab.get('difficulties', [])
    status_options = ['draft', 'approved', 'rejected']

    # Base query — LEFT JOIN so recipes with no evaluation still appear
    # Ensure optimal DB queries for diets and evaluations
    stmt = db.select(Recipe).outerjoin(Recipe.evaluation).options(
        joinedload(Recipe.diets),
        joinedload(Recipe.evaluation),
        joinedload(Recipe.meal_types)
    )

    if search_term:
        stmt = stmt.where(
            or_(
                func.lower(Recipe.title).contains(search_term),
                func.lower(Recipe.cuisine).contains(search_term)
            )
        )

    # Apply Filters
    if selected_cuisines:
        stmt = stmt.where(Recipe.cuisine.in_(selected_cuisines))
    if selected_proteins:
        stmt = stmt.where(Recipe.protein_type.in_(selected_proteins))
    if selected_difficulties:
        stmt = stmt.where(Recipe.difficulty.in_(selected_difficulties))
    if selected_statuses:
        stmt = stmt.where(Recipe.status.in_(selected_statuses))
    if selected_diets:
        stmt = stmt.where(Recipe.diets.any(RecipeDiet.diet.in_(selected_diets)))
    if selected_meal_types:
        stmt = stmt.where(Recipe.meal_types.any(RecipeMealType.meal_type.in_(selected_meal_types)))

    # Apply sorting
    valid_cols = {
        'id': Recipe.id,
        'title': Recipe.title,
        'cuisine': Recipe.cuisine,
        'difficulty': Recipe.difficulty,
        'total_score': RecipeEvaluation.total_score,
        'score_name': RecipeEvaluation.score_name,
        'score_ingredients': RecipeEvaluation.score_ingredients,
        'score_components': RecipeEvaluation.score_components,
        'score_amounts': RecipeEvaluation.score_amounts,
        'score_steps': RecipeEvaluation.score_steps,
        'score_image': RecipeEvaluation.score_image,
        'total_calories': Recipe.total_calories,
        'total_protein': Recipe.total_protein,
        'total_fat': Recipe.total_fat,
        'total_carbs': Recipe.total_carbs
    }
    sort_attr = valid_cols.get(sort_col, Recipe.id)
    stmt = stmt.order_by(sort_attr.asc() if sort_dir == 'asc' else sort_attr.desc())

    # Paginate — fetches only `per_page` rows from DB per request
    pagination = db.paginate(stmt, page=page, per_page=per_page, error_out=False)

    return render_template(
        'admin/recipes_management.html',
        recipes=pagination.items,
        pagination=pagination,
        current_sort=sort_col,
        current_dir=sort_dir,
        current_search=search_term,
        cuisine_options=cuisine_options,
        diet_options=diet_options,
        meal_type_options=meal_type_options,
        protein_options=protein_options,
        difficulty_options=difficulty_options,
        status_options=status_options,
        selected_cuisines=selected_cuisines,
        selected_diets=selected_diets,
        selected_meal_types=selected_meal_types,
        selected_proteins=selected_proteins,
        selected_difficulties=selected_difficulties,
        selected_statuses=selected_statuses,
        urlencode=lambda args: urlencode(args, doseq=True)
    )

@app.route('/admin/recipes/<int:recipe_id>/evaluate', methods=['POST'])
@login_required
@admin_required
def evaluate_recipe_api(recipe_id):
    from services.evaluation_service import evaluate_recipe
    try:
        result = evaluate_recipe(recipe_id)
        return jsonify(result)
    except Exception as e:
        print(f"Error evaluating recipe: {e}")
        return jsonify({'status': 'error', 'error': str(e)}), 500


@app.route('/admin/recipes/<int:recipe_id>/status', methods=['POST'])
@login_required
@admin_required
def update_recipe_status(recipe_id: int):
    """Async endpoint to update a recipe's publishing status."""
    VALID_STATUSES = {'draft', 'approved', 'rejected'}
    try:
        data = request.get_json()
        new_status = data.get('status', '').strip().lower()
        if new_status not in VALID_STATUSES:
            return jsonify({'success': False, 'error': f'Invalid status. Must be one of: {VALID_STATUSES}'}), 400

        recipe = db.session.get(Recipe, recipe_id)
        if not recipe:
            return jsonify({'success': False, 'error': 'Recipe not found'}), 404

        recipe.status = new_status
        db.session.commit()
        print(f"Status update: Recipe #{recipe_id} -> '{new_status}'")
        return jsonify({'success': True, 'new_status': recipe.status})

    except Exception as e:
        db.session.rollback()
        print(f"Status update error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/admin/api/recipes/<int:recipe_id>/clone', methods=['POST'])
@login_required
@admin_required
def clone_recipe_api(recipe_id: int):
    """Admin endpoint to deep-clone a recipe with ingredient overrides."""
    from services.recipe_service import clone_recipe
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No JSON payload provided'}), 400
            
        new_title = data.get('new_title')
        if not new_title:
            return jsonify({'success': False, 'error': 'new_title is required'}), 400
            
        ingredient_overrides = data.get('ingredient_overrides', {})
        
        # Perform the deep clone using our new Python utility
        new_recipe_id = clone_recipe(recipe_id, new_title, ingredient_overrides, db.session)
        
        return jsonify({
            'success': True, 
            'new_recipe_id': new_recipe_id,
            'message': 'Recipe cloned successfully!'
        })

    except Exception as e:
        db.session.rollback()
        print(f"Error cloning recipe: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
@app.route('/ingredients')
def pantry_management():
    # Fetch all ingredients sorted by Category then Name
    ingredients = db.session.execute(db.select(Ingredient).order_by(Ingredient.main_category, Ingredient.name)).scalars().all()
    
    # Load constraints for dependent filtering
    data_dir = os.path.join(app.root_path, 'data', 'constraints')
    sub_categories_map = {}
    try:
        with open(os.path.join(data_dir, 'categories.json'), 'r') as f:
            data = json.load(f)
            sub_categories_map = data.get('sub_categories', {})
    except Exception as e:
        print(f"Error loading categories: {e}")

    return render_template('pantry_management.html', ingredients=ingredients, sub_categories_map=sub_categories_map)

@app.route('/api/ingredient/<int:id>/toggle_basic', methods=['POST'])
def toggle_basic_ingredient(id):
    ing = db.session.get(Ingredient, id)
    if not ing:
        return jsonify({'success': False, 'error': 'Ingredient not found'}), 404
    
    # Toggle
    ing.is_staple = not ing.is_staple
    db.session.commit()
    
    return jsonify({
        'success': True, 
        'new_status': ing.is_basic_ingredient,
        'id': ing.id,
        'name': ing.name
    })

# --- New Ingredient Workflow ---

@app.route('/new-ingredient', methods=['GET'])
@app.route('/new-ingredient', methods=['GET'])
def new_ingredient_view():
    # Load categories for the dropdown in the template (manually or via API)
    # We can pass them to the template
    data_dir = os.path.join(app.root_path, 'data', 'constraints')
    with open(os.path.join(data_dir, 'categories.json'), 'r') as f:
        category_data = json.load(f)
        
    return render_template('new_ingredient.html', 
                         main_categories=category_data.get('main_categories', []),
                         sub_categories_map=category_data.get('sub_categories', {}))

@app.route('/api/search-ingredients', methods=['POST'])
def search_ingredients_api():
    try:
        data = request.get_json()
        query = data.get('query', '').strip()
        
        if not query or len(query) < 2:
            return jsonify({'success': True, 'results': []})
            
        # Search for name matches (ILIKE)
        results = db.session.execute(
            db.select(Ingredient)
            .where(Ingredient.name.ilike(f"%{query}%"))
            .order_by(Ingredient.name)
            .limit(10)
        ).scalars().all()
        
        # Serialize results
        items = []
        for i in results:
            img = None
            if i.image_url:
                if i.image_url.startswith('http'):
                    img = i.image_url
                else:
                    img = url_for('static', filename=i.image_url)
            items.append({
                'id': i.id,
                'name': i.name, 
                'category': i.main_category,
                'food_id': i.food_id,
                'image_url': img
            })
        
        return jsonify({'success': True, 'results': items})
        
    except Exception as e:
        print(f"Search API Error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/relink-ingredient', methods=['POST'])
@login_required
def relink_ingredient_api():
    """Swap the ingredient linked to a RecipeIngredient row. Admin only."""
    if not current_user.is_admin:
        return jsonify({'success': False, 'error': 'Admin access required'}), 403
    
    try:
        data = request.get_json()
        ri_id = data.get('recipe_ingredient_id')
        new_ing_id = data.get('new_ingredient_id')
        
        if not ri_id or not new_ing_id:
            return jsonify({'success': False, 'error': 'Missing parameters'}), 400
        
        # Fetch the RecipeIngredient row
        ri = db.session.get(RecipeIngredient, ri_id)
        if not ri:
            return jsonify({'success': False, 'error': 'Recipe ingredient link not found'}), 404
        
        # Verify the target ingredient exists
        new_ingredient = db.session.get(Ingredient, new_ing_id)
        if not new_ingredient:
            return jsonify({'success': False, 'error': 'Target ingredient not found'}), 404
        
        old_name = ri.ingredient.name
        ri.ingredient_id = new_ingredient.id
        db.session.commit()
        
        print(f"🔗 Relinked: '{old_name}' → '{new_ingredient.name}' (recipe_ingredient #{ri_id})")
        return jsonify({'success': True, 'old_name': old_name, 'new_name': new_ingredient.name})
        
    except Exception as e:
        db.session.rollback()
        print(f"Relink API Error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/suggest-substitutes', methods=['POST'])
def suggest_substitutes_api():
    """Return top 3 pantry substitutes for a missing ingredient name."""
    try:
        data = request.get_json()
        name = data.get('name', '').strip()
        
        if not name:
            return jsonify({'success': True, 'suggestions': []})
        
        # Ensure pantry_map includes DB items (not just pantry.json)
        from ai_engine import set_pantry_memory
        slim_context = get_slim_pantry_context()
        set_pantry_memory(slim_context)
        
        
        # Get fuzzy suggestions (extra to account for filtered imports)
        suggestions = get_top_pantry_suggestions(name, top_n=6)
        
        # Enrich with DB data (image, full name casing, category)
        
        enriched = []
        for sug in suggestions:
            if len(enriched) >= 3:
                break
                
            ingredient = db.session.execute(
                db.select(Ingredient).where(Ingredient.food_id == sug['food_id'])
            ).scalars().first()
            
            if not ingredient:
                continue
            # Skip IMP-imported ingredients only (not all non-original)
            if (ingredient.main_category or '').lower() == 'imported':
                continue
            if ingredient.food_id.startswith('IMP-'):
                continue
            
            img = None
            if ingredient.image_url:
                if ingredient.image_url.startswith('http'):
                    img = ingredient.image_url
                else:
                    img = url_for('static', filename=ingredient.image_url)
            
            enriched.append({
                'id': ingredient.id,
                'name': ingredient.name,
                'food_id': ingredient.food_id,
                'category': ingredient.main_category or 'Uncategorized',
                'image_url': img,
                'score': sug['score']
            })
        
        return jsonify({'success': True, 'suggestions': enriched})
        
    except Exception as e:
        print(f"Suggest Substitutes API Error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/analyze-ingredient', methods=['POST'])
def analyze_ingredient_api():
    try:
        data = request.get_json()
        prompt = data.get('prompt')
        
        if not prompt:
            return jsonify({'success': False, 'error': 'Prompt is required'})
            
        # Load validation constraints
        data_dir = os.path.join(app.root_path, 'data', 'constraints')
        with open(os.path.join(data_dir, 'categories.json'), 'r') as f:
            valid_categories = json.load(f)
            
        # Call AI Engine
        analysis = analyze_ingredient_ai(prompt, valid_categories)
        
        return jsonify({'success': True, 'data': analysis})
        
    except Exception as e:
        print(f"Analysis API Error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/extract-nutrients', methods=['POST'])
def extract_nutrients_api():
    try:
        data = request.get_json()
        raw_text = data.get('raw_text', '').strip()
        ingredient_name = data.get('ingredient_name', '')

        if not raw_text:
            return jsonify({'success': False, 'error': 'No text provided'})

        # Call AI
        nutrients = extract_nutrients_from_text(raw_text, ingredient_name)
        
        return jsonify({'success': True, 'nutrients': nutrients})

    except Exception as e:
        print(f"Nutrient Extraction Error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/generate-ingredient-image', methods=['POST'])
def generate_ingredient_image_api():
    try:
        data = request.get_json()
        prompt = data.get('prompt')
        if not prompt:
            return jsonify({'success': False, 'error': 'No prompt provided'})

        # Generate 4 Images
        images_list = generate_actual_image(prompt, number_of_images=4)
        
        results = []
        for img in images_list:
            filename = f"ing_temp_{uuid.uuid4().hex}.png"
            
            # Save to BytesIO
            img_io = io.BytesIO()
            img.save(img_io, format='PNG')
            img_io.seek(0)
            
            # Save via storage provider (Local or GCS)
            # This ensures 'temp' folder exists on the correct provider
            public_url = storage_provider.save(img_io.read(), filename, "temp")
            
            results.append({
                'url': public_url,
                'filename': filename
            })
        
        return jsonify({
            'success': True, 
            'images': results
        })
        
    except Exception as e:
        print(f"Image Gen Error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/ingredient/<int:id>', methods=['GET'])
def get_ingredient_details_api(id):
    try:
        ingredient = db.session.get(Ingredient, id)
        if not ingredient:
            return jsonify({'success': False, 'error': 'Ingredient not found'}), 404
            
        return jsonify({
            'success': True,
            'id': ingredient.id,
            'name': ingredient.name,
            'image_prompt': ingredient.image_prompt or "No prompt available.",
            'main_category': ingredient.main_category,
            'sub_category': ingredient.sub_category,
            'unit': ingredient.default_unit,
            'average_g_per_unit': ingredient.average_g_per_unit,
            'calories_per_100g': ingredient.calories_per_100g,
            'protein_per_100g': ingredient.protein_per_100g,
            'fat_per_100g': ingredient.fat_per_100g,
            'carbs_per_100g': ingredient.carbs_per_100g,
            'sugar_per_100g': ingredient.sugar_per_100g,
            'fiber_per_100g': ingredient.fiber_per_100g,
            'fat_saturated_per_100g': ingredient.fat_saturated_per_100g,
            'sodium_mg_per_100g': ingredient.sodium_mg_per_100g,
            'kj_per_100g': ingredient.kj_per_100g
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/ingredient/<int:id>', methods=['DELETE'])
def delete_ingredient_api(id):
    try:
        ingredient = db.session.get(Ingredient, id)
        if not ingredient:
            return jsonify({'success': False, 'error': 'Ingredient not found'}), 404
            
        # Check usage in recipes
        if ingredient.recipe_ingredients:
            force = request.args.get('force') == 'true'
            if not force:
                recipes = [ri.recipe.title for ri in ingredient.recipe_ingredients]
                return jsonify({
                    'success': False, 
                    'requires_confirmation': True,
                    'message': f"Used in {len(recipes)} recipes: {', '.join(recipes)}. Delete anyway?",
                    'recipes': recipes
                }), 409

            # Explicitly delete associations if forcing
            for ri in ingredient.recipe_ingredients:
                db.session.delete(ri)
            
        db.session.delete(ingredient)
        db.session.commit()
        
        return jsonify({'success': True})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/update-ingredient-image', methods=['POST'])
def update_ingredient_image_api():
    try:
        data = request.get_json()
        ing_id = data.get('id')
        temp_filename = data.get('temp_filename')
        image_prompt = data.get('image_prompt')
        
        if not ing_id or not temp_filename:
            return jsonify({'success': False, 'error': 'Missing ID or Image'}), 400
            
        ingredient = db.session.get(Ingredient, ing_id)
        if not ingredient:
            return jsonify({'success': False, 'error': 'Ingredient not found'}), 404

        # Create new unique name to bust cache
        new_filename = f"{ingredient.food_id}_{uuid.uuid4().hex[:8]}.png"
        
        # Use storage provider to move from temp to pantry
        # This works for both local and GCS storage
        try:
            new_url = storage_provider.move(temp_filename, "temp", new_filename, "pantry")
        except FileNotFoundError:
            return jsonify({'success': False, 'error': 'Temp image not found'}), 404
        
        # Update DB with the new image URL
        # For GCS, this will be the full public URL
        # For local, this will be /static/pantry/{filename}
        if new_url.startswith('http'):
            # GCS - store full URL
            ingredient.image_url = new_url
        else:
            # Local - store relative path
            ingredient.image_url = f"pantry/{new_filename}"
            
        if image_prompt:
            ingredient.image_prompt = image_prompt
            
        db.session.commit()
        
        return jsonify({
            'success': True,
            'new_image_url': new_url
        })

    except Exception as e:
        print(f"Update Image Error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/save-ingredient', methods=['POST'])
def save_new_ingredient_api():
    try:
        data = request.get_json()
        
        # 1. Generate Unique ID
        all_ids = db.session.execute(db.select(Ingredient.food_id)).scalars().all()
        max_id = 0
        for fid in all_ids:
            if fid.isdigit():
                val = int(fid)
                if val > max_id:
                    max_id = val
        
        new_id_int = max_id + 1
        new_food_id = f"{new_id_int:06d}" 
        
        # 2. Handle Image
        image_url = None
        temp_filename = data.get('temp_image_filename')
        if temp_filename:
            # Move from temp to pantry
            src = os.path.join(app.root_path, 'static', 'temp', temp_filename)
            if os.path.exists(src):
                # We use the food_id for the filename: 000123.png
                new_filename = f"{new_food_id}.png"
                dst_dir = os.path.join(app.root_path, 'static', 'pantry')
                os.makedirs(dst_dir, exist_ok=True)
                
                dst = os.path.join(dst_dir, new_filename)
                shutil.move(src, dst) # Keep this line
                
                image_url = f"pantry/{new_filename}"

        # 3. Create Object
        new_ing = Ingredient(
            food_id=new_food_id,
            name=data.get('name'),
            main_category=data.get('main_category'),
            sub_category=data.get('sub_category'),
            default_unit=data.get('unit'),
            average_g_per_unit=data.get('average_g_per_unit'),
            
            # Nutrition
            calories_per_100g=data.get('calories_per_100g'),
            protein_per_100g=data.get('protein_per_100g'),
            fat_per_100g=data.get('fat_per_100g'),
            carbs_per_100g=data.get('carbs_per_100g'),
            sugar_per_100g=data.get('sugar_per_100g'),
            fiber_per_100g=data.get('fiber_per_100g'),
            sodium_mg_per_100g=data.get('sodium_mg_per_100g'),
            fat_saturated_per_100g=data.get('fat_saturated_per_100g'),
            
            # Metadata
            image_prompt=data.get('image_prompt'),
            image_url=image_url,
            created_at=datetime.datetime.now().isoformat()
        )
        
        db.session.add(new_ing)
        db.session.commit()
        
        return jsonify({'success': True, 'id': new_ing.id})
        
    except Exception as e:
        db.session.rollback()
        print(f"Save Ingredient Error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/add-synonym', methods=['POST'])
@login_required
def add_synonym_api():
    try:
        data = request.get_json()
        name = data.get('name')
        food_id = data.get('food_id')
        
        if not name or not food_id:
            return jsonify({'success': False, 'error': 'Missing name or food_id'}), 400
            
        from ai_engine import add_synonym
        add_synonym(name, food_id)
        
        return jsonify({'success': True})
    except Exception as e:
        print(f"Synonym API Error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
        


@app.route('/api/quick-add-ingredient', methods=['POST'])
def quick_add_ingredient_api():
    try:
        data = request.get_json()
        name = data.get('name')
        
        if not name:
            return jsonify({'success': False, 'error': 'Name is required'}), 400
            
        # 1. Load Categories via Constraints
        data_dir = os.path.join(app.root_path, 'data', 'constraints')
        with open(os.path.join(data_dir, 'categories.json'), 'r') as f:
            category_data = json.load(f)
            
        # 2. Analyze
        analysis = analyze_ingredient_ai(name, category_data)
        
        # 3. Generate Unique ID
        all_ids = db.session.execute(db.select(Ingredient.food_id)).scalars().all()
        max_id = 0
        for fid in all_ids:
             # Ensure we parse only numeric IDs
             if fid.isdigit():
                val = int(fid)
                if val > max_id:
                    max_id = val
        
        new_id_int = max_id + 1
        new_food_id = f"{new_id_int:06d}"
        
        # 4. Create Object (No Image for Quick Add - can regenerate later)
        new_ing = Ingredient(
            food_id=new_food_id,
            name=analysis.get('name', name), # Use analyzed name if available
            main_category=analysis.get('main_category'),
            sub_category=analysis.get('sub_category'),
            default_unit=analysis.get('unit'),
            average_g_per_unit=analysis.get('average_g_per_unit'),
            
            # Nutrition
            calories_per_100g=analysis.get('calories_per_100g'),
            protein_per_100g=analysis.get('protein_per_100g'),
            fat_per_100g=analysis.get('fat_per_100g'),
            carbs_per_100g=analysis.get('carbs_per_100g'),
            sugar_per_100g=analysis.get('sugar_per_100g'),
            fiber_per_100g=analysis.get('fiber_per_100g'),
            sodium_mg_per_100g=analysis.get('sodium_mg_per_100g'),
            fat_saturated_per_100g=analysis.get('fat_saturated_per_100g'),
            kj_per_100g=analysis.get('kj_per_100g'),
            
            # Metadata
            image_prompt=analysis.get('image_prompt'),
            created_at=datetime.datetime.now().isoformat()
        )
        
        db.session.add(new_ing)
        db.session.commit()
        
        # Update cache/map if needed?
        # Typically the app gets context from DB on request, 
        # but generate_recipe_ai uses a "slim_context" passed to it.
        # We assume the user RE-SUBMITS the generation request, which will fetch fresh context.
        
        return jsonify({
            'success': True, 
            'ingredient': {
                'id': new_ing.id,
                'name': new_ing.name
            }
        })

    except Exception as e:
        db.session.rollback()
        print(f"Quick Add Error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/update-ingredient-data', methods=['POST'])
def update_ingredient_data_api():
    try:
        data = request.get_json()
        ing_id = data.get('id')
        
        if not ing_id:
             return jsonify({'success': False, 'error': 'ID is required'}), 400
             
        ingredient = db.session.get(Ingredient, ing_id)
        if not ingredient:
             return jsonify({'success': False, 'error': 'Ingredient not found'}), 404
             
        # Update Fields
        ingredient.name = data.get('name')
        ingredient.main_category = data.get('main_category')
        ingredient.sub_category = data.get('sub_category')
        ingredient.default_unit = data.get('unit')
        ingredient.average_g_per_unit = data.get('average_g_per_unit')
        
        ingredient.calories_per_100g = data.get('calories_per_100g')
        ingredient.kj_per_100g = data.get('kj_per_100g', 0)
        ingredient.protein_per_100g = data.get('protein_per_100g')
        ingredient.fat_per_100g = data.get('fat_per_100g')
        ingredient.carbs_per_100g = data.get('carbs_per_100g')
        ingredient.sugar_per_100g = data.get('sugar_per_100g')
        ingredient.fiber_per_100g = data.get('fiber_per_100g')
        ingredient.fat_saturated_per_100g = data.get('fat_saturated_per_100g')
        ingredient.sodium_mg_per_100g = data.get('sodium_mg_per_100g')
        
        if data.get('image_prompt'):
            ingredient.image_prompt = data.get('image_prompt')
            
        # Handle New Image if provided
        temp_filename = data.get('temp_image_filename')
        if temp_filename:
            src = os.path.join(app.root_path, 'static', 'temp', temp_filename)
            if os.path.exists(src):
                # Use existing food_id + random to bust cache
                new_filename = f"{ingredient.food_id}_{uuid.uuid4().hex[:6]}.png"
                dst_dir = os.path.join(app.root_path, 'static', 'pantry')
                os.makedirs(dst_dir, exist_ok=True)
                
                dst = os.path.join(dst_dir, new_filename)
                shutil.move(src, dst)
                
                ingredient.image_url = f"pantry/{new_filename}"
        
        db.session.commit()
        return jsonify({'success': True})
        
    except Exception as e:
        db.session.rollback()
        print(f"Update Ing Data Error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/recipe/<int:recipe_id>', methods=['GET'])
@login_required
def get_recipe_json(recipe_id):
    if not current_user.is_admin:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
    recipe = db.session.get(Recipe, recipe_id)
    if not recipe:
        return jsonify({'success': False, 'error': 'Recipe not found'}), 404
        
    try:
        # Construct JSON
        data = {
            'id': recipe.id,
            'title': recipe.title,
            'cuisine': recipe.cuisine,
            'diets': recipe.diets_list,
            'difficulty': recipe.difficulty,
            'protein_type': recipe.protein_type,
            'meal_types': recipe.meal_types_list,
            'chef_id': recipe.chef_id or 'gourmet',
            'taste_level': recipe.taste_level,
            'prep_time_mins': recipe.prep_time_mins,
            'cleanup_factor': recipe.cleanup_factor,
            'image_filename': recipe.image_filename,
            'nutrition': {
                'calories': recipe.total_calories,
                'protein': recipe.total_protein,
                'carbs': recipe.total_carbs,
                'fat': recipe.total_fat,
                'sugar': recipe.total_sugar,
                'fiber': recipe.total_fiber
            },
            'ingredients': [],
            'instructions': []
        }
        
        # Serialize Ingredients
        for ri in recipe.ingredients:
            data['ingredients'].append({
                'id': ri.id,
                'name': ri.ingredient.name,
                'amount': ri.amount,
                'unit': ri.unit,
                'gram_weight': ri.gram_weight,
                'component': ri.component,
                'food_id': ri.ingredient.food_id,
                'category': ri.ingredient.main_category
            })
            
        # Serialize Instructions
        sorted_instructions = sorted(recipe.instructions, key=lambda x: x.step_number)
        for step in sorted_instructions:
            data['instructions'].append({
                'step': step.step_number,
                'phase': step.phase,
                'text': step.text,
                'component': step.component
            })
            
        return jsonify({'success': True, 'recipe': data})
        
    except Exception as e:
        print(f"Error serializing recipe {recipe_id}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/merge-ingredients', methods=['POST'])
def merge_ingredients_api():
    try:
        data = request.get_json()
        source_id = data.get('source_id')
        target_id = data.get('target_id')
        
        if not source_id or not target_id:
            return jsonify({'success': False, 'error': 'Source and Target IDs required'}), 400
        
        if source_id == target_id:
            return jsonify({'success': False, 'error': 'Cannot merge ingredient into itself'}), 400

        source = db.session.get(Ingredient, source_id)
        target = db.session.get(Ingredient, target_id)
        
        if not source or not target:
             return jsonify({'success': False, 'error': 'One or both ingredients not found'}), 404
             
        # Begin Merge
        # 1. Get all usages of source
        usages = list(source.recipe_ingredients) 
        
        count_updated = 0
        count_conflicts = 0
        
        for usage in usages:
            recipe = usage.recipe
            
            # Check if recipe already has target
            conflict = next((ri for ri in recipe.ingredients if ri.ingredient_id == target.id), None)
            
            if conflict:
                # Recipe uses both. Remove source usage (redundant).
                db.session.delete(usage)
                count_conflicts += 1
            else:
                # No conflict, just reassign
                usage.ingredient = target
                db.session.add(usage)
                count_updated += 1
        
        # Flush changes to DB so Foreign Keys are updated/deleted
        db.session.flush()
        
        # Refresh source to ensure it knows it has no more associated ingredients
        # preventing SQLAlchemy from trying to SET NULL on delete
        db.session.refresh(source)
        
        # 2. Delete the Source Ingredient
        db.session.delete(source)
        
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': f"Merged '{source.name}' into '{target.name}'. Updated {count_updated} recipes, resolved {count_conflicts} conflicts."
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Merge Error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

        print(f"Merge Error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

def find_best_ingredient_match(name):
    """
    Tries to find the best existing ingredient for a given name.
    Uses the robust fuzzy matching from ai_engine.get_pantry_id,
    then resolves the food_id to a DB record.
    Returns an Ingredient ORM object or None.
    """
    from ai_engine import get_pantry_id
    
    food_id_str = get_pantry_id(name)
    if not food_id_str:
        return None
    
    return db.session.execute(
        db.select(Ingredient).where(Ingredient.food_id == food_id_str)
    ).scalars().first()

# ---------------------------------------------------------------------------
# Helper: Handle the result dict from process_recipe_workflow
# ---------------------------------------------------------------------------
def _handle_workflow_result(result: dict, query_context: str, chef_id: str):
    """Shared response handler for all generation routes."""
    is_ajax = 'application/json' in request.headers.get('Accept', '')

    if result['status'] == STATUS_MISSING:
        if is_ajax:
            missing_names = [m['name'] for m in result.get('missing_ingredients', [])]
            return jsonify({
                'success': False, 
                'error': f"Missing ingredients: {', '.join(missing_names)}"
            })
            
        data_dir = os.path.join(app.root_path, 'data', 'constraints')
        with open(os.path.join(data_dir, 'categories.json'), 'r') as f:
            cat_data = json.load(f)
        return render_template(
            'missing_ingredients_resolution.html',
            missing_items=result['missing_ingredients'],
            query=query_context,
            chef_id=chef_id,
            main_categories=cat_data.get('main_categories', []),
            sub_categories_map=cat_data.get('sub_categories', {}),
        )
    # STATUS_SUCCESS
    if is_ajax:
        return jsonify({
            'success': True,
            'recipe_id': result['recipe_id']
        })
    return redirect(url_for('recipe_detail', recipe_id=result['recipe_id']))


@app.route('/generate/web', methods=['POST'])
def generate_web_recipe():
    blog_url = request.form.get('blog_url')
    if not blog_url:
        return redirect(url_for('discover'))

    try:
        # 1. Scrape content
        scraper = WebScraper()
        scraped_data = scraper.scrape_url(blog_url)
        if not scraped_data or not scraped_data['text']:
            return "Could not extract text from this URL", 400

        # 2. Build clean pantry context (no IMP duplicates)
        slim_context = get_slim_pantry_context()
        clean_context = slim_context

        # 3. Call AI
        recipe_data = generate_recipe_from_web_text(
            scraped_data['text'],
            source_url=blog_url,
            slim_context=clean_context,
        )
        if not recipe_data:
            return "AI could not extract a valid recipe from the page.", 400

        # 4. Unified persistence pipeline
        result = process_recipe_workflow(recipe_data, query_context=blog_url, chef_id='gourmet')
        return _handle_workflow_result(result, query_context=blog_url, chef_id='gourmet')

    except Exception as e:
        db.session.rollback()
        print(f"Web Import Error: {e}")
        import traceback; traceback.print_exc()
        if 'application/json' in request.headers.get('Accept', ''):
            return jsonify({'success': False, 'error': str(e)}), 500
        return f"Error processing web import: {e}", 500

@app.route('/generate/text', methods=['POST'])
@app.route('/generate/text', methods=['POST'])
def generate_from_text():
    """Generate a recipe from raw pasted text (free-form text dump)."""
    raw_text = request.form.get('raw_text', '').strip()
    if not raw_text:
        flash("Please paste some recipe text.", "error")
        return redirect(url_for('new_recipe'))

    try:
        # 1. Build clean pantry context (no IMP duplicates)
        slim_context = get_slim_pantry_context()
        clean_context = slim_context

        # 2. Call AI — reuse web-text extractor (handles noisy input)
        recipe_data = generate_recipe_from_web_text(
            raw_text,
            source_url="Manual Text Input",
            slim_context=clean_context,
        )
        if not recipe_data:
            flash("AI could not extract a valid recipe from the text.", "error")
            return redirect(url_for('new_recipe'))

        # 3. Unified persistence pipeline
        query_context = raw_text[:200]  # truncated for display on resolution page
        result = process_recipe_workflow(recipe_data, query_context=query_context, chef_id='gourmet')
        return _handle_workflow_result(result, query_context=query_context, chef_id='gourmet')

    except Exception as e:
        db.session.rollback()
        import traceback; traceback.print_exc()
        if 'application/json' in request.headers.get('Accept', ''):
            return jsonify({'success': False, 'error': str(e)}), 500
        flash(f"Error processing text: {str(e)}", "error")
        return redirect(url_for('new_recipe'))

@app.route('/admin/bulk-generate')
@login_required
@admin_required
def bulk_generate_view():
    return render_template('admin/bulk_generate.html')

@app.route('/admin/api/generate-single-idea', methods=['POST'])
@login_required
@admin_required
def api_generate_single_idea():
    data = request.get_json()
    if not data or not data.get('idea'):
        return jsonify({'success': False, 'error': 'No idea provided'}), 400
        
    query = data.get('idea')
    chef_id = data.get('chef_id', 'gourmet')
    
    try:
        pantry_context = get_slim_pantry_context()
        clean_context = pantry_context

        recipe_data = generate_recipe_ai(query, clean_context, chef_id=chef_id)
        result = process_recipe_workflow(recipe_data, query_context=query, chef_id=chef_id)
        
        if result.get('status') == 'SUCCESS':
            return jsonify({
                'success': True,
                'recipe_id': result['recipe_id'],
                'recipe_title': recipe_data.title
            })
        else:
            missing_names = [m['name'] for m in result.get('missing_ingredients', [])]
            return jsonify({
                'success': False, 
                'error': f"Missing ingredients: {', '.join(missing_names)}"
            })
            
    except Exception as e:
        db.session.rollback()
        import traceback; traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/admin/api/generate-single-url', methods=['POST'])
@login_required
@admin_required
def api_generate_single_url():
    data = request.get_json()
    if not data or not data.get('url'):
        return jsonify({'success': False, 'error': 'No URL provided'}), 400
        
    url = data.get('url')
    chef_id = data.get('chef_id', 'gourmet')
    
    try:
        from services.social_media_service import SocialMediaExtractor
        from ai_engine import generate_recipe_from_video

        # Download video to temporary storage
        extract_result = SocialMediaExtractor.download_video(url)
        video_path = extract_result['video_path']
        caption = extract_result.get('caption', '')
        
        try:
            pantry_context = get_slim_pantry_context()
            clean_context = pantry_context

            # Generate via video pipeline
            recipe_data = generate_recipe_from_video(video_path, caption, clean_context)
            
            query_context = caption or url
            result = process_recipe_workflow(recipe_data, query_context=query_context, chef_id=chef_id)
            
            if result.get('status') == 'SUCCESS':
                return jsonify({
                    'success': True,
                    'recipe_id': result['recipe_id'],
                    'recipe_title': recipe_data.title
                })
            else:
                missing_names = [m['name'] for m in result.get('missing_ingredients', [])]
                return jsonify({
                    'success': False, 
                    'error': f"Missing ingredients: {', '.join(missing_names)}"
                })
        finally:
            # Always ensure the temp video file is deleted
            SocialMediaExtractor.cleanup(video_path)
            
    except Exception as e:
        db.session.rollback()
        import traceback; traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/generate')
def generate():
    query = request.args.get('query')
    chef_id = request.args.get('chef_id', 'gourmet')
    if not query:
        return redirect(url_for('discover'))

    try:
        # 1. Build clean pantry context (no IMP duplicates)
        pantry_context = get_slim_pantry_context()
        clean_context = pantry_context

        # 2. Call AI
        recipe_data = generate_recipe_ai(query, clean_context, chef_id=chef_id)

        # 3. Unified persistence pipeline
        result = process_recipe_workflow(recipe_data, query_context=query, chef_id=chef_id)
        return _handle_workflow_result(result, query_context=query, chef_id=chef_id)

    except ValueError as ve:
        flash(f"Validation Error: {str(ve)}", "error")
        return redirect(url_for('discover'))
    except Exception as e:
        db.session.rollback()
        import traceback; traceback.print_exc()
        if 'application/json' in request.headers.get('Accept', ''):
            return jsonify({'success': False, 'error': str(e)}), 500
        flash(f"Generation error: {str(e)}", "error")
        return redirect(url_for('new_recipe'))

@app.route('/recipe/<int:recipe_id>')
def recipe_detail(recipe_id):
    recipe = db.session.get(Recipe, recipe_id)
    if not recipe:
        flash("Recipe not found.", "error")
        return redirect(url_for('discover'))
    
    # Group instructions by phase for display
    instructions = Instruction.query.filter_by(recipe_id=recipe_id).order_by(Instruction.component, Instruction.phase, Instruction.step_number).all()
    
    steps_by_phase = {
        'Prep': [i for i in instructions if i.phase == 'Prep'],
        'Cook': [i for i in instructions if i.phase == 'Cook'],
        'Serve': [i for i in instructions if i.phase == 'Serve']
    }
    
    # NEW: Group instructions by component for multi-component display
    from itertools import groupby
    steps_by_component = []
    for component_name, steps in groupby(instructions, key=lambda x: x.component):
        steps_by_component.append((component_name, list(steps)))
    
    # Group ingredients by component
    ingredients_by_component = {}
    for recipe_ing in recipe.ingredients:
        comp = recipe_ing.component
        if comp not in ingredients_by_component:
            ingredients_by_component[comp] = []
        ingredients_by_component[comp].append(recipe_ing)
    
    # DEFENSIVE: Reconcile mismatched component names
    # If ingredient components don't match instruction components,
    # ingredients become invisible in the template. Fix by redistributing.
    instruction_comp_names = {name for name, _ in steps_by_component}
    ingredient_comp_names = set(ingredients_by_component.keys())
    orphaned_comps = ingredient_comp_names - instruction_comp_names
    
    if orphaned_comps:
        print(f"⚠️  Component name mismatch for recipe {recipe_id}:")
        print(f"   Instruction components: {instruction_comp_names}")
        print(f"   Ingredient components:  {ingredient_comp_names}")
        print(f"   Orphaned:               {orphaned_comps}")
        
        # Collect all orphaned ingredients
        orphaned_ingredients = []
        for comp in orphaned_comps:
            orphaned_ingredients.extend(ingredients_by_component.pop(comp))
        
        if len(steps_by_component) == 1:
            # Single instruction component — put all ingredients there
            sole_comp = steps_by_component[0][0]
            if sole_comp not in ingredients_by_component:
                ingredients_by_component[sole_comp] = []
            ingredients_by_component[sole_comp].extend(orphaned_ingredients)
        elif len(steps_by_component) > 1 and not ingredients_by_component:
            # No ingredients matched ANY component — distribute evenly by splitting
            # based on ingredient order across the instruction components
            comp_names = [name for name, _ in steps_by_component]
            per_comp = max(1, len(orphaned_ingredients) // len(comp_names))
            for idx, comp_name in enumerate(comp_names):
                start = idx * per_comp
                end = start + per_comp if idx < len(comp_names) - 1 else len(orphaned_ingredients)
                ingredients_by_component[comp_name] = orphaned_ingredients[start:end]
        else:
            # Some matched, some didn't — attach orphans to "Other Ingredients"
            ingredients_by_component["Other Ingredients"] = orphaned_ingredients
            # Also add a pseudo-component for display if not already in steps
            if not any(name == "Other Ingredients" for name, _ in steps_by_component):
                steps_by_component.append(("Other Ingredients", []))
    # NEW: Chronological Sequence (Parallel Dashboard)
    has_chronological_data = False
    chrono_steps = []
    component_meta = {}
    
    if len(instructions) > 0:
        has_chronological_data = all(i.global_order_index is not None for i in instructions)
        if has_chronological_data:
            chrono_steps = sorted(instructions, key=lambda x: x.global_order_index)
            
            # Phase 1: Backend metadata for sandbox Views
            unique_components = []
            for step in chrono_steps:
                if step.component not in unique_components:
                    unique_components.append(step.component)
                    
            themes = [
                {'color': 'bg-blue-50 text-blue-800', 'border': 'border-blue-200', 'indent': 'ml-0 md:ml-0'},
                {'color': 'bg-rose-50 text-rose-800', 'border': 'border-rose-200', 'indent': 'ml-4 md:ml-12'},
                {'color': 'bg-emerald-50 text-emerald-800', 'border': 'border-emerald-200', 'indent': 'ml-8 md:ml-24'},
                {'color': 'bg-amber-50 text-amber-800', 'border': 'border-amber-200', 'indent': 'ml-12 md:ml-36'},
                {'color': 'bg-purple-50 text-purple-800', 'border': 'border-purple-200', 'indent': 'ml-16 md:ml-48'},
            ]
            
            for index, comp in enumerate(unique_components):
                if index < len(themes):
                    component_meta[comp] = themes[index]
                else:
                    component_meta[comp] = themes[-1]

    return render_template('recipe.html', 
                            recipe=recipe, 
                            steps_by_phase=steps_by_phase, 
                            ingredients_by_component=ingredients_by_component, 
                            steps_by_component=steps_by_component,
                            has_chronological_data=has_chronological_data,
                            chrono_steps=chrono_steps,
                            component_meta=component_meta)

@app.route('/recipe/<int:recipe_id>/kitchen')
def recipe_kitchen_mode(recipe_id):
    """A highly isolated, 1-screen landscape view for cooking on tablets."""
    query = db.select(Recipe).where(Recipe.id == recipe_id).options(
        joinedload(Recipe.ingredients).joinedload(RecipeIngredient.ingredient),
        joinedload(Recipe.instructions)
    )
    recipe = db.session.execute(query).unique().scalar_one_or_none()

    if not recipe:
        flash("Recipe not found.", "error")
        return redirect(url_for('index'))

    return render_template('kitchen_mode.html', recipe=recipe)

@app.route('/api/recipe/<int:recipe_id>/generate-components', methods=['POST'])
@login_required
@admin_required
def generate_component_images(recipe_id):
    recipe = db.session.get(Recipe, recipe_id)
    if not recipe:
        return jsonify({'success': False, 'error': 'Recipe not found'}), 404
        
    try:
        from io import BytesIO
        import uuid
        
        # Ensure dictionary exists
        if recipe.component_images is None:
            recipe.component_images = {}
            
        new_images = dict(recipe.component_images)
        components = {i.component for i in recipe.instructions if i.component}
        
        from services.photographer_service import generate_actual_image
        
        generated_count = 0
        for comp in components:
            if comp not in new_images:
                prompt_text = f"A clean, minimalist 4k product photo of just {comp} alone, explicitly isolated on a pure solid white background. Strictly NO other components, NO distracting plates or utensils, NO background clutter, highly appetizing."
                try:
                    images = generate_actual_image(prompt_text, number_of_images=1)
                    if images and len(images) > 0:
                        img = images[0]
                        filename = f"comp_{recipe_id}_{uuid.uuid4().hex[:8]}.png"
                        
                        img_byte_arr = BytesIO()
                        img.save(img_byte_arr, format='PNG')
                        
                        # Save directly to recipes folder
                        storage_provider.save(img_byte_arr.getvalue(), filename, "recipes")
                        
                        new_images[comp] = filename
                        generated_count += 1
                except Exception as e:
                    print(f"Failed to generate image for component {comp}: {e}")
                    
        if generated_count > 0:
            recipe.component_images = new_images
            from sqlalchemy.orm.attributes import flag_modified
            flag_modified(recipe, "component_images")
            db.session.commit()
            
        return jsonify({'success': True, 'generated': generated_count})
        
    except Exception as e:
        print(f"Gen Error in generate-components: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/placeholder/ingredient/\u003cfood_id\u003e')
def ingredient_placeholder(food_id):
    """Generate a dynamic SVG placeholder for an ingredient without an image."""
    ingredient = db.session.execute(
        db.select(Ingredient).where(Ingredient.food_id == food_id)
    ).scalar_one_or_none()
    
    if ingredient:
        return generate_ingredient_placeholder(ingredient.name)
    else:
        return generate_ingredient_placeholder("Unknown")


from services.social_media_service import SocialMediaExtractor
from ai_engine import generate_recipe_ai, get_pantry_id, chefs_data, generate_recipe_from_video



@app.route('/generate/video', methods=['POST'])
def generate_from_video():
    video_url = request.form.get('video_url')
    if not video_url:
        flash("Please provide a video URL", "error")
        return redirect(url_for('discover'))

    try:
        # 1. Download video
        extract_result = SocialMediaExtractor.download_video(video_url)
        video_path = extract_result['video_path']
        caption = extract_result.get('caption', '')

        try:
            # 2. Build clean pantry context (no IMP duplicates)
            pantry_context = get_slim_pantry_context()
            clean_context = pantry_context

            # 3. Call AI (video analysis)
            recipe_data = generate_recipe_from_video(video_path, caption, clean_context)

            # 4. Unified persistence pipeline
            query_context = caption or f"Video Import: {video_url}"
            result = process_recipe_workflow(recipe_data, query_context=query_context, chef_id='gourmet')
            return _handle_workflow_result(result, query_context=query_context, chef_id='gourmet')

        finally:
            # Always cleanup the video file
            SocialMediaExtractor.cleanup(video_path)

    except Exception as e:
        db.session.rollback()
        import traceback; traceback.print_exc()
        if 'application/json' in request.headers.get('Accept', ''):
            return jsonify({'success': False, 'error': str(e)}), 500
        flash(f"Error processing video: {str(e)}", "error")
        return redirect(url_for('discover'))


# --- INGREDIENT DASHBOARD ROUTES ---
@app.route('/ingredient-images')
def ingredient_dashboard():
    # 1. Load ALL Ingredients from Database (Single Source of Truth)
    # The DB contains the updated GCS URLs from our sync script
    # We map them to the dictionary format expected by the template
    db_ingredients = db.session.execute(
        db.select(Ingredient).order_by(Ingredient.food_id)
    ).scalars().all()
    
    pantry_items = []
    
    # 2. Convert SQLAlchemy objects to Dicts for the template/logic below
    for ing in db_ingredients:
        item = {
            'food_id': ing.food_id,
            'food_name': ing.name,
            'main_category': ing.main_category,
            'images': {
                'image_url': ing.image_url,
                'image_prompt': ing.image_prompt
            }
        }
        pantry_items.append(item)

    # 3. Check for Candidates & Apply Overrides
    # (Existing logic continues below relying on pantry_items list)
    
    # Create DB Map for O(1) lookup if needed, but we already have the items from DB
    db_map = {ing.food_id: ing.image_url for ing in db_ingredients}
    
    generator = VertexImageGenerator(storage_provider=storage_provider, root_path=app.root_path)
    
    for item in pantry_items:
        # DB Override
        if item['food_id'] in db_map and db_map[item['food_id']]:
             item['images']['image_url'] = db_map[item['food_id']]
        
        # Candidate Logic
        safe_name = generator._get_safe_filename(item['food_name'])
        
        # Check storage backend to determine existence check
        storage_backend = os.getenv('STORAGE_BACKEND', 'local')
        if storage_backend == 'gcs':
             # For GCS, we should ideally check if the blob exists.
             # But checking 100+ blobs per request is slow.
             # Strategy: Assume if we found a way to "list" them efficiently, or just rely on a naming convention?
             # Better: The frontend generates them. The backend check is only for "Reload".
             # Let's perform a CHECK only if we really need to, or skip it for performance?
             # Attempt to check existence:
             # We can use storage_provider.exists, but we need to instantiate it efficiently.
             # NOTE: This N+1 check will be slow on GCS.
             # Optimization: List valid candidates once per request?
             # For now, let's just constructing the URL and checking if it *should* exist? 
             # No, we need to know IF it exists to show the "Approve" button state or the image.
             
             # HACK: For now, we will skip the server-side check for candidates on GCS to avoid latency.
             # OR we implement a "list_candidates" method in generator.
             # Let's try to verify existence for the *single* item if possible, but for the dashboard loop it's heavy.
             
             # Alternative: The dashboard JS handles the "broken image" by hiding it?
             # But we need 'has_candidate' to be True to show the UI.
             
             # Let's try storage.exists(filename, folder)
             # We need to make sure we don't kill performance.
             # Actually, let's just check the "Current" images mapping? No, candidates are new.
             
             # Compromise: We will NOT check existence loop-side in GCS mode for now to avoid timeout.
             # We will assume False unless we have a better way (e.g. separate API to fetch candidates).
             # Wait, if we assume False, the user can't approve them after reload.
             
             # Fix: Generator should provide `list_candidates()`
             # For this immediate fix, let's just check `storage_provider.exists` and accept the latency for the admin page.
             item['has_candidate'] = storage_provider.exists(safe_name, "pantry/candidates")
             if item['has_candidate']:
                  bucket_name = os.getenv('GCS_BUCKET_NAME')
                  item['candidate_url'] = f"https://storage.googleapis.com/{bucket_name}/pantry/candidates/{safe_name}"
             else:
                  item['candidate_url'] = None
        else:
             # Local check
             candidate_path = os.path.join(generator.candidates_dir, safe_name)
             item['has_candidate'] = os.path.exists(candidate_path)
             item['candidate_url'] = f"/static/pantry/candidates/{safe_name}" if item['has_candidate'] else None
        
        # Ensure image_url is fully qualified for display if it's relative AND NOT from GCS (which starts with https)
        if 'images' in item and item['images'].get('image_url'):
             url = item['images']['image_url']
             if not url.startswith('/') and not url.startswith('http'):
                 item['images']['image_url'] = f"/static/{url}"
                 
        # 3. Check for Originals (Locked Assets)
        if 'images' in item and item['images'].get('image_url'):
            current_url = item['images']['image_url']
            basename = os.path.basename(current_url)
            
            # Smart Detection of Originals
            # If we are using GCS, we assume the original exists if we have a main image (since we synced them)
            # OR we could check if the main image is a GCS URL
            
            storage_backend = os.getenv('STORAGE_BACKEND', 'local')
            bucket_name = os.getenv('GCS_BUCKET_NAME')
            
            if storage_backend == 'gcs' and bucket_name:
                # GCS Mode: Construct URL directly
                # Public URL format: https://storage.googleapis.com/BUCKET_NAME/OBJECT_NAME
                item['original_url'] = f"https://storage.googleapis.com/{bucket_name}/pantry/originals/{basename}"
            else:
                # Local Mode: Check filesystem
                original_path = os.path.join(app.root_path, 'static', 'pantry', 'originals', basename)
                if os.path.exists(original_path):
                    item['original_url'] = f"/static/pantry/originals/{basename}"
                else:
                    item['original_url'] = None

    return render_template('ingredient_dashboard.html', ingredients=pantry_items)

@app.route('/api/generate-ingredient-image', methods=['POST'])
def generate_ingredient_image():
    data = request.json
    ingredient_name = data.get('ingredient_name')
    # The frontend text box value, treated as details if name exists, or raw prompt if not
    user_input = data.get('prompt') 
    
    if not ingredient_name and not user_input:
        return jsonify({'success': False, 'error': 'Missing name or details'})
        
    generator = VertexImageGenerator(storage_provider=storage_provider, root_path=app.root_path)

    if ingredient_name:
        # STRATEGY A: Use the Studio Template (Preferred)
        # We treat the user's input as the 'visual_details' variable
        final_prompt = generator.get_prompt(ingredient_name, visual_details=user_input or "")
        print(f"DEBUG: Generating image for '{ingredient_name}' using Template. Final Prompt: {final_prompt[:50]}...")
        result = generator.generate_candidate(ingredient_name, final_prompt)
        print(f"DEBUG: Generation Result for '{ingredient_name}': {result}") # ADDED LOG
    elif user_input:
        # STRATEGY B: Fallback (Raw Mode) - generate a temp name
        temp_name = f"unknown_{uuid.uuid4().hex[:6]}"
        print(f"DEBUG: Generating raw image using Prompt: {user_input[:50]}...")
        result = generator.generate_candidate(temp_name, user_input)
    else:
         return jsonify({'success': False, 'error': 'Missing name or prompt'})

    return jsonify(result)

@app.route('/api/approve-ingredient-image', methods=['POST'])
def approve_ingredient_image():
    data = request.json
    ingredient_name = data.get('ingredient_name')
    
    if not ingredient_name:
        return jsonify({'success': False, 'error': 'Missing ingredient name'})
        
    generator = VertexImageGenerator(storage_provider=storage_provider, root_path=app.root_path)
    result = generator.approve_candidate(ingredient_name)
    
    return jsonify(result)


# RESOURCE ADMIN ROUTES
@app.route('/admin/resources')
@login_required
@admin_required
def admin_resources_list():
    resources = db.session.execute(db.select(Resource).order_by(Resource.created_at.desc())).scalars().all()
    return render_template('admin/resources_list.html', resources=resources)

@app.route('/admin/resources/new', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_resource_new():
    if request.method == 'POST':
        title = request.form.get('title')
        slug = request.form.get('slug')
        if not slug:
            slug = slugify(title)
            
        summary = request.form.get('summary')
        content_markdown = request.form.get('content_markdown')
        tags = request.form.get('tags')
        status = request.form.get('status', 'draft')
        
        # Image Upload
        image_filename = None
        file = request.files.get('cover_image')
        if file and file.filename != '':
            new_filename = f"resource_{uuid.uuid4().hex[:8]}_{file.filename}"
            # Save returns the public URL (path for local, http url for GCS)
            public_url = storage_provider.save(file.read(), new_filename, "resources")
            image_filename = public_url
        
        resource = Resource(
            title=title,
            slug=slug,
            summary=summary,
            content_markdown=content_markdown,
            image_filename=image_filename,
            tags=tags,
            status=status
        )
        
        # Handle Relations
        related_ids = request.form.getlist('related_ids')
        for r_id in related_ids:
            related = db.session.get(Resource, int(r_id))
            if related:
                resource.related_resources.append(related)
                
        db.session.add(resource)
        try:
            db.session.commit()
            flash('Resource created successfully!', 'success')
            return redirect(url_for('admin_resources_list'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating resource: {str(e)}', 'error')
    
    all_resources = db.session.execute(db.select(Resource).order_by(Resource.title)).scalars().all()
    return render_template('admin/resource_editor.html', resource=None, all_resources=all_resources)

@app.route('/admin/resources/edit/<int:resource_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_resource_edit(resource_id):
    resource = db.session.get(Resource, resource_id)
    if not resource:
        flash('Resource not found', 'error')
        return redirect(url_for('admin_resources_list'))

    if request.method == 'POST':
        resource.title = request.form.get('title')
        
        slug = request.form.get('slug')
        if not slug:
            slug = slugify(resource.title)
        resource.slug = slug
        
        resource.summary = request.form.get('summary')
        resource.content_markdown = request.form.get('content_markdown')
        resource.tags = request.form.get('tags')
        resource.status = request.form.get('status', 'draft')
        
        # Image Upload
        file = request.files.get('cover_image')
        if file and file.filename != '':
            new_filename = f"resource_{uuid.uuid4().hex[:8]}_{file.filename}"
            public_url = storage_provider.save(file.read(), new_filename, "resources")
            resource.image_filename = public_url
        
        # Handle Relations (Update: clear and re-add)
        resource.related_resources = [] # This empties the relationship
        related_ids = request.form.getlist('related_ids')
        for r_id in related_ids:
             related = db.session.get(Resource, int(r_id))
             if related:
                 resource.related_resources.append(related)
        
        try:
            db.session.commit()
            flash('Resource updated successfully!', 'success')
            return redirect(url_for('admin_resources_list'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating resource: {str(e)}', 'error')

    all_resources = db.session.execute(db.select(Resource).order_by(Resource.title)).scalars().all()
    return render_template('admin/resource_editor.html', resource=resource, all_resources=all_resources)


@app.route('/api/delete-recipe/<int:recipe_id>', methods=['DELETE'])
@login_required
@admin_required
def delete_recipe_api(recipe_id):
    try:
        recipe = db.session.get(Recipe, recipe_id)
        if not recipe:
             return jsonify({'success': False, 'error': 'Recipe not found'}), 404
             
        # Delete the recipe (Cascades should handle children, but let's be safe if configured)
        # SQLAlchemy models have cascade="all, delete-orphan", so deleting parent is enough.
        db.session.delete(recipe)
        db.session.commit()
        
        return jsonify({'success': True, 'message': f"Recipe {recipe_id} deleted successfully."})
        
    except Exception as e:
        db.session.rollback()
        print(f"Delete Recipe Error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/delete-recipes/bulk', methods=['POST'])
@login_required
@admin_required
def delete_bulk_recipes():
    """Permanently delete one or more recipes and all their child records.

    Uses SQLAlchemy ORM delete() + .in_() rather than raw text() SQL because
    pg8000 cannot bind a Python tuple as a single IN-list parameter.
    SQLAlchemy expands the IN list correctly for every driver.
    """
    from sqlalchemy import delete as sql_delete

    data = request.get_json(silent=True) or {}
    recipe_ids = data.get('recipe_ids', [])

    if not recipe_ids or not isinstance(recipe_ids, list):
        return jsonify({'success': False, 'error': 'No valid recipe IDs provided'}), 400

    try:
        recipe_ids = [int(rid) for rid in recipe_ids]
    except (ValueError, TypeError) as e:
        return jsonify({'success': False, 'error': f'Invalid recipe ID: {e}'}), 400

    if not recipe_ids:
        return jsonify({'success': False, 'error': 'No valid integer IDs after parsing'}), 400

    try:
        # Delete child tables in FK-safe order (children before parent).
        # ORM delete() + .in_() lets SQLAlchemy build the correct parameterized
        # IN clause regardless of driver (pg8000, psycopg2, etc.).
        db.session.execute(sql_delete(UserRecipeInteraction).where(UserRecipeInteraction.recipe_id.in_(recipe_ids)))
        db.session.execute(sql_delete(UserQueue).where(UserQueue.recipe_id.in_(recipe_ids)))
        db.session.execute(sql_delete(RecipeIngredient).where(RecipeIngredient.recipe_id.in_(recipe_ids)))
        db.session.execute(sql_delete(Instruction).where(Instruction.recipe_id.in_(recipe_ids)))
        db.session.execute(sql_delete(RecipeEvaluation).where(RecipeEvaluation.recipe_id.in_(recipe_ids)))
        db.session.execute(sql_delete(RecipeMealType).where(RecipeMealType.recipe_id.in_(recipe_ids)))
        db.session.execute(sql_delete(RecipeDiet).where(RecipeDiet.recipe_id.in_(recipe_ids)))
        db.session.execute(sql_delete(CollectionItem).where(CollectionItem.recipe_id.in_(recipe_ids)))

        # Delete parent recipes last
        result = db.session.execute(sql_delete(Recipe).where(Recipe.id.in_(recipe_ids)))
        deleted_count = result.rowcount
        db.session.commit()

        print(f"[Bulk Delete] Deleted {deleted_count} recipes: {recipe_ids}")
        return jsonify({'success': True, 'count': deleted_count,
                        'message': f"Deleted {deleted_count} recipes."})

    except Exception as e:
        db.session.rollback()
        import traceback
        print(f"[Bulk Delete ERROR] {e}\n{traceback.format_exc()}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/cms/upload-image', methods=['POST'])
@login_required
@admin_required
def cms_upload_image():
    if 'image' not in request.files:
        return jsonify({'error': 'No file part'}), 400
        
    file = request.files['image']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
        
    if file:
        filename = f"cms_{uuid.uuid4().hex[:8]}_{file.filename}"
        public_url = storage_provider.save(file.read(), filename, "cms-uploads")
        return jsonify({
            'data': {
                'filePath': public_url
            }
        })
    return jsonify({'error': 'Upload failed'}), 500

# ---------------------------------------------------------------------------
# Public Collection Routes
# ---------------------------------------------------------------------------

@app.route('/collections')
def collections_index():
    """Public index of all published collections, with their approved recipes pre-loaded."""
    raw = (
        db.session.execute(
            db.select(RecipeCollection)
            .where(RecipeCollection.is_published.is_(True))
            .order_by(RecipeCollection.created_at.desc())
        )
        .scalars()
        .all()
    )
    # Build (collection, [recipe, ...]) pairs — filter approved at route level
    rows = [
        (col, [item.recipe for item in col.items if item.recipe.status == 'approved'])
        for col in raw
    ]
    return render_template('collections_index.html', rows=rows)


@app.route('/collections/<slug>')
def collection_detail(slug: str):
    """Public detail page for a single published collection."""
    collection = db.session.execute(
        db.select(RecipeCollection).where(RecipeCollection.slug == slug)
    ).scalar_one_or_none()

    if not collection or not collection.is_published:
        abort(404)

    # Filter only approved recipes at the route level (belt-and-suspenders)
    recipes = [
        item.recipe
        for item in collection.items
        if item.recipe.status == 'approved'
    ]

    return render_template('collection_detail.html', collection=collection, recipes=recipes)


if __name__ == '__main__':
    with app.app_context():
        db.create_all() # Ensure tables exist
    app.run(host='0.0.0.0', debug=True, port=8000)
