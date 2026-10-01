"""Interactions Blueprint: favorites, the feed, ratings, feedback and 'made it' marks."""
import datetime
import io
import uuid

from flask import jsonify, redirect, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import func
from sqlalchemy.orm.attributes import flag_modified

from database.models import Recipe, UserRecipeInteraction, db
from routes._flat import FlatBlueprint
from routes._shared import get_recipe_image_url, get_storage

interactions_bp = FlatBlueprint("interactions", __name__)


@interactions_bp.route('/api/me/favorites', methods=['GET'])
@login_required
def get_user_favorites():
    """Returns a list of recipe IDs favorited by the current user."""
    # Efficiently fetch only the IDs
    # Using the relationship:
    fav_ids = [i.recipe_id for i in current_user.interactions if i.status == 'favorite']
    return jsonify({'favorite_ids': fav_ids})

@interactions_bp.route('/api/recipes/<int:recipe_id>/favorite', methods=['POST'])
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

@interactions_bp.route('/api/feed/recipes', methods=['GET'])
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
            'difficulty': r.difficulty,
            'calories': int(r.total_calories) if getattr(r, 'total_calories', 0) else 0,
            'portions': f"{r.base_servings or 1} servings",
            'diet': r.diets_list[0] if getattr(r, 'diets_list', None) and len(r.diets_list) > 0 else 'None'
        })
        
    return jsonify({'recipes': data, 'has_more': len(data) == limit})

@interactions_bp.route('/api/interactions/recipe/<int:recipe_id>', methods=['POST'])
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


@interactions_bp.route('/api/interactions/recipe/<int:recipe_id>/made', methods=['PATCH'])
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


@interactions_bp.route('/api/interactions/recipe/<int:recipe_id>/feedback', methods=['POST'])
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
            url = get_storage().save(file_bytes, filename, 'user_uploads')
            new_urls.append(url)
        except Exception as e:
            print(f"Photo upload error: {e}")

    interaction.user_photos = new_urls
    flag_modified(interaction, 'user_photos')  # Force SQLAlchemy to dirty-track JSON column
    db.session.commit()
    return jsonify({'success': True})


@interactions_bp.route('/api/interactions/recipe/<int:recipe_id>', methods=['GET'])
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


@interactions_bp.route('/saved-recipes')
@login_required
def saved_recipes_view():
    """Legacy route: Redirects to the unified library view."""
    return redirect(url_for('recipes_list', view='saved'))
