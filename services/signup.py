"""Signing up where you are. A visitor who presses Save, Cook next or I made this is sent to sign up (or log in) with
what they pressed in the address (/register?next=/recipe/5&do=made&recipe=5), and it is done the moment the account
exists, so nothing they tried is lost and they land back where they were (routes/auth_routes.py)."""
import datetime

from sqlalchemy import func

from database.models import Recipe, UserQueue, UserRecipeInteraction, db

# What a visitor can ask for before they have an account, and what it says once it is done
ACTIONS = {'save': 'Saved {title}.', 'queue': 'Added {title} to Cook next.', 'made': 'You made {title}: it is in your Made list.'}

# Saving again soon after (the steps unticked and ticked off again, Save pressed twice) is the same meal
SAME_MEAL = datetime.timedelta(hours=3)


def safe_next(value):
    """A next address only when it is a path on this site, so a link cannot send someone elsewhere after signing in."""
    value = (value or '').strip()
    if value.startswith('/') and not value.startswith('//') and '\\' not in value:
        return value
    return None


def pending(args):
    """(action, recipe) from the address, or None when it asks for nothing this site can do. Only approved recipes:
    a visitor cannot see the others."""
    action, recipe_id = args.get('do'), args.get('recipe', '')
    if action not in ACTIONS or not recipe_id.isdigit():
        return None
    recipe = db.session.get(Recipe, int(recipe_id))
    return (action, recipe) if recipe and recipe.status == 'approved' else None


def carry(args):
    """The parts of the address that go along between sign up and log in, and into each form's action."""
    kept = {'next': safe_next(args.get('next')), 'do': args.get('do'), 'recipe': args.get('recipe')}
    return {key: value for key, value in kept.items() if value}


def cooked(user_id, recipe_id):
    """I made this: marks the recipe as made and counts the meal (once within SAME_MEAL). Returns the interaction."""
    interaction = db.session.get(UserRecipeInteraction, (user_id, recipe_id))
    if not interaction:
        interaction = UserRecipeInteraction(user_id=user_id, recipe_id=recipe_id, status='pass',
                                            is_super_like=False, made_count=0)
        db.session.add(interaction)
    now = datetime.datetime.utcnow()
    if not interaction.last_made_at or now - interaction.last_made_at > SAME_MEAL or not interaction.made_count:
        interaction.made_count = (interaction.made_count or 0) + 1
    interaction.is_made, interaction.last_made_at = True, now
    db.session.commit()
    return interaction


def do(user, action, recipe):
    """Does what the visitor pressed, now that they have an account. Saving and Cook next only add, never take away,
    so doing it twice (they had an account after all) changes nothing. Returns the line to tell them."""
    if action == 'made':
        cooked(user.id, recipe.id)
    elif action == 'save':
        interaction = db.session.get(UserRecipeInteraction, (user.id, recipe.id))
        if interaction:
            interaction.status, interaction.timestamp = 'favorite', datetime.datetime.utcnow()
        else:
            db.session.add(UserRecipeInteraction(user_id=user.id, recipe_id=recipe.id, status='favorite'))
        db.session.commit()
    elif action == 'queue':
        queued = db.session.execute(db.select(UserQueue.id).where(
            UserQueue.user_id == user.id, UserQueue.recipe_id == recipe.id)).first()
        if not queued:
            last = db.session.execute(
                db.select(func.max(UserQueue.position)).where(UserQueue.user_id == user.id)).scalar()
            db.session.add(UserQueue(user_id=user.id, recipe_id=recipe.id, position=(last or 0) + 1,
                                     added_at=datetime.datetime.utcnow()))
            db.session.commit()
    return ACTIONS[action].format(title=recipe.title)
