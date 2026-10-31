"""Auth Blueprint: login, registration and logout, and the signed-in user's measuring system."""
from flask import flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy import func

from database.models import User, db
from routes._flat import FlatBlueprint
from services.measures import SYSTEMS
from services import funnel, signup

auth_bp = FlatBlueprint("auth", __name__)


def _email(form):
    """An email as stored and looked up: no spaces around it, lower case, so Pal@… and pal@… are one account."""
    return (form.get('email') or '').strip().lower()


def _by_email(email):
    # lower() on the column too, for accounts made before emails were stored in lower case
    return db.session.execute(db.select(User).where(func.lower(User.email) == email)).scalar()


def _signed_in(user, hello=None):
    """Signs the user in, kept on this device (a year, Flask-Login's remember cookie) so a cook who signs up at
    breakfast is still signed in at dinner, then does what they pressed before they had an account (services/signup.py)
    and goes back to where they were."""
    login_user(user, remember=True)
    wanted = signup.pending(request.args)
    if wanted or hello:
        flash(signup.do(user, *wanted) if wanted else hello, 'success')
    return redirect(signup.safe_next(request.args.get('next')) or url_for('recipes_list'))


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return _signed_in(current_user._get_current_object()) if signup.pending(request.args) else redirect(
            url_for('new_recipe') if current_user.is_admin else url_for('recipes_list'))

    if request.method == 'POST':
        user = _by_email(_email(request.form))
        if user and user.check_password(request.form.get('password') or ''):
            if user.is_admin and not request.args.get('next'):
                login_user(user, remember=True)
                return redirect(url_for('new_recipe'))
            return _signed_in(user)
        flash('That email and password do not match.', 'error')

    return render_template('login.html', carry=signup.carry(request.args), wanted=signup.pending(request.args))


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return _signed_in(current_user._get_current_object()) if signup.pending(request.args) else redirect(url_for('recipes_list'))

    if request.method == 'POST':
        email, password = _email(request.form), request.form.get('password') or ''
        if not email or not password:
            flash('Give an email and a password.', 'error')
        elif _by_email(email):
            flash('There is already an account with that email: log in instead.', 'error')
            return redirect(url_for('login', **signup.carry(request.args)))
        else:
            # The user, with where they came from (services/funnel.py)
            source = request.form.get('source')
            user = User(email=email, is_admin=False, signup_ref=funnel.session_ref(),
                        signup_source=source if source in dict(funnel.SOURCES) else None)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            return _signed_in(user, hello='Welcome to The Lazy Chef.')

    return render_template('register.html', sources=funnel.SOURCES, carry=signup.carry(request.args),
                           wanted=signup.pending(request.args))


@auth_bp.route('/logout')
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('content.home'))


@auth_bp.route('/api/me/units', methods=['POST'])
@login_required
def set_unit_system():
    """Keep the measuring system the user chose in the menu (components/unit_switch.html) on the user, so it follows
    them to other devices. The page sets the cookie itself, for visitors too."""
    units = (request.get_json(silent=True) or {}).get('units')
    if units not in SYSTEMS:
        return jsonify({'error': 'units must be metric or us'}), 400
    current_user.unit_system = units
    db.session.commit()
    return jsonify({'units': units})
