"""Mirror Blueprint: pair with a partner and see the recipes you both favorited."""
import secrets
import string

from flask import jsonify, redirect, render_template, request
from flask_login import current_user, login_required
from sqlalchemy import or_

from database.models import Recipe, User, UserLink, UserRecipeInteraction, db
from routes._flat import FlatBlueprint

mirror_bp = FlatBlueprint("mirror", __name__)


def _generate_pairing_code(length: int = 8) -> str:
    """Generate a unique alphanumeric pairing code."""
    alphabet = string.ascii_uppercase + string.digits
    while True:
        code = ''.join(secrets.choice(alphabet) for _ in range(length))
        exists = db.session.execute(
            db.select(UserLink).where(UserLink.pairing_code == code)
        ).scalar_one_or_none()
        if not exists:
            return code


@mirror_bp.route('/mirror')
@login_required
def mirror_hub():
    """Partner hub — generate / enter codes, see active partners."""
    # Auto-redirect to the default or sole partner's mirror
    # (skip if user explicitly navigated to hub via ?skip_redirect=1)
    if not request.args.get('skip_redirect'):
        # Priority 1: explicit default partner
        default_link = db.session.execute(
            db.select(UserLink).where(
                UserLink.status == 'ACCEPTED',
                UserLink.is_default == True,
                or_(
                    UserLink.user_id_1 == current_user.id,
                    UserLink.user_id_2 == current_user.id
                )
            )
        ).scalar_one_or_none()

        if default_link:
            partner_id = default_link.user_id_2 if default_link.user_id_1 == current_user.id else default_link.user_id_1
            return redirect(f'/api/graph/mirror/{partner_id}')

        # Priority 2: if exactly one accepted partner, go straight to them
        accepted_links = db.session.execute(
            db.select(UserLink).where(
                UserLink.status == 'ACCEPTED',
                or_(
                    UserLink.user_id_1 == current_user.id,
                    UserLink.user_id_2 == current_user.id
                )
            )
        ).scalars().all()

        if len(accepted_links) == 1:
            link = accepted_links[0]
            partner_id = link.user_id_2 if link.user_id_1 == current_user.id else link.user_id_1
            return redirect(f'/api/graph/mirror/{partner_id}')

    # Get or create this user's pending code
    pending_link = db.session.execute(
        db.select(UserLink).where(
            UserLink.user_id_1 == current_user.id,
            UserLink.status == 'PENDING'
        )
    ).scalar_one_or_none()

    if not pending_link:
        pending_link = UserLink(
            user_id_1=current_user.id,
            pairing_code=_generate_pairing_code()
        )
        db.session.add(pending_link)
        db.session.commit()

    # Get accepted partners
    partners_raw = db.session.execute(
        db.select(UserLink).where(
            UserLink.status == 'ACCEPTED',
            or_(
                UserLink.user_id_1 == current_user.id,
                UserLink.user_id_2 == current_user.id
            )
        )
    ).scalars().all()

    partners = []
    for link in partners_raw:
        partner_id = link.user_id_2 if link.user_id_1 == current_user.id else link.user_id_1
        partner_user = db.session.get(User, partner_id)
        if partner_user:
            partners.append({
                'id': partner_user.id,
                'email': partner_user.email,
                'link_id': link.id,
                'is_default': link.is_default
            })

    return render_template('mirror_hub.html',
                           pairing_code=pending_link.pairing_code,
                           partners=partners)


@mirror_bp.route('/api/mirror/accept', methods=['POST'])
@login_required
def mirror_accept_code():
    """Accept a pairing code from another user."""
    data = request.get_json(silent=True) or {}
    code = (data.get('code') or '').strip().upper()

    if not code:
        return jsonify({'success': False, 'error': 'No code provided'}), 400

    link = db.session.execute(
        db.select(UserLink).where(
            UserLink.pairing_code == code,
            UserLink.status == 'PENDING'
        )
    ).scalar_one_or_none()

    if not link:
        return jsonify({'success': False, 'error': 'Invalid or expired code'}), 404

    if link.user_id_1 == current_user.id:
        return jsonify({'success': False, 'error': 'Cannot pair with yourself'}), 400

    # Check for existing accepted link between these two users
    existing = db.session.execute(
        db.select(UserLink).where(
            UserLink.status == 'ACCEPTED',
            or_(
                (UserLink.user_id_1 == current_user.id) & (UserLink.user_id_2 == link.user_id_1),
                (UserLink.user_id_1 == link.user_id_1) & (UserLink.user_id_2 == current_user.id),
            )
        )
    ).scalar_one_or_none()

    if existing:
        return jsonify({'success': False, 'error': 'Already paired with this user'}), 400

    link.user_id_2 = current_user.id
    link.status = 'ACCEPTED'
    db.session.commit()

    # Generate a fresh pending code for the original user
    new_pending = UserLink(
        user_id_1=link.user_id_1,
        pairing_code=_generate_pairing_code()
    )
    db.session.add(new_pending)
    db.session.commit()

    partner = db.session.get(User, link.user_id_1)
    return jsonify({'success': True, 'partner_email': partner.email if partner else 'Partner'})


@mirror_bp.route('/api/mirror/regenerate', methods=['POST'])
@login_required
def mirror_regenerate_code():
    """Regenerate the user's pending pairing code."""
    pending = db.session.execute(
        db.select(UserLink).where(
            UserLink.user_id_1 == current_user.id,
            UserLink.status == 'PENDING'
        )
    ).scalar_one_or_none()

    if pending:
        db.session.delete(pending)

    new_link = UserLink(
        user_id_1=current_user.id,
        pairing_code=_generate_pairing_code()
    )
    db.session.add(new_link)
    db.session.commit()
    return jsonify({'success': True, 'code': new_link.pairing_code})


@mirror_bp.route('/api/graph/mirror/<int:partner_id>', methods=['GET'])
@login_required
def get_mirror_recipes(partner_id):
    """Return recipes mutually favorited by current_user and partner_id."""
    # Verify an ACCEPTED link exists
    link = db.session.execute(
        db.select(UserLink).where(
            UserLink.status == 'ACCEPTED',
            or_(
                (UserLink.user_id_1 == current_user.id) & (UserLink.user_id_2 == partner_id),
                (UserLink.user_id_1 == partner_id) & (UserLink.user_id_2 == current_user.id),
            )
        )
    ).scalar_one_or_none()

    if not link:
        return jsonify({'success': False, 'error': 'No active link with this partner'}), 403

    # Subquery: recipe_ids favorited by current_user
    my_favs = db.select(UserRecipeInteraction.recipe_id).where(
        UserRecipeInteraction.user_id == current_user.id,
        UserRecipeInteraction.status == 'favorite'
    ).scalar_subquery()

    # Subquery: recipe_ids favorited by partner
    partner_favs = db.select(UserRecipeInteraction.recipe_id).where(
        UserRecipeInteraction.user_id == partner_id,
        UserRecipeInteraction.status == 'favorite'
    ).scalar_subquery()

    # Intersection: recipes favorited by both
    shared_recipes = db.session.execute(
        db.select(Recipe).where(
            Recipe.id.in_(my_favs),
            Recipe.id.in_(partner_favs),
            Recipe.status == 'approved'
        )
    ).scalars().all()

    partner_user = db.session.get(User, partner_id)
    partner_name = partner_user.email.split('@')[0] if partner_user else 'Partner'

    # Check if this partner is the current user's default
    current_link = db.session.execute(
        db.select(UserLink).where(
            UserLink.status == 'ACCEPTED',
            or_(
                (UserLink.user_id_1 == current_user.id) & (UserLink.user_id_2 == partner_id),
                (UserLink.user_id_1 == partner_id) & (UserLink.user_id_2 == current_user.id),
            )
        )
    ).scalar_one_or_none()
    is_default = current_link.is_default if current_link else False

    return render_template('mirror_results.html',
                           recipes=shared_recipes,
                           partner_name=partner_name,
                           partner_id=partner_id,
                           is_default=is_default)


@mirror_bp.route('/api/mirror/set-default/<int:partner_id>', methods=['POST'])
@login_required
def mirror_set_default(partner_id):
    """Toggle a partner as the default mirror destination for the current user."""
    # Find the link between current_user and partner_id
    link = db.session.execute(
        db.select(UserLink).where(
            UserLink.status == 'ACCEPTED',
            or_(
                (UserLink.user_id_1 == current_user.id) & (UserLink.user_id_2 == partner_id),
                (UserLink.user_id_1 == partner_id) & (UserLink.user_id_2 == current_user.id),
            )
        )
    ).scalar_one_or_none()

    if not link:
        return jsonify({'success': False, 'error': 'No active link with this partner'}), 404

    if link.is_default:
        # Unset default
        link.is_default = False
        db.session.commit()
        return jsonify({'success': True, 'is_default': False})

    # Clear any existing defaults for this user
    all_links = db.session.execute(
        db.select(UserLink).where(
            UserLink.status == 'ACCEPTED',
            UserLink.is_default == True,
            or_(
                UserLink.user_id_1 == current_user.id,
                UserLink.user_id_2 == current_user.id
            )
        )
    ).scalars().all()
    for old in all_links:
        old.is_default = False

    # Set new default
    link.is_default = True
    db.session.commit()
    return jsonify({'success': True, 'is_default': True})
