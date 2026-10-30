"""Auth Blueprint: login, registration and logout, and the signed-in user's measuring system."""
from flask import flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from database.models import User, db
from routes._flat import FlatBlueprint
from services.measures import SYSTEMS
from services import funnel

auth_bp = FlatBlueprint("auth", __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
         return redirect(url_for('new_recipe') if current_user.is_admin else url_for('recipes_list'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = db.session.execute(db.select(User).where(User.email == email)).scalar()
        
        if user and user.check_password(password):
            login_user(user)
            next_page = request.args.get('next')
            # Intelligent Redirect based on Role
            if not next_page:
                next_page = url_for('new_recipe') if user.is_admin else url_for('recipes_list')
            return redirect(next_page)
        
        flash('Invalid email or password', 'error')
    
    return render_template('login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
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
            
        # Create User, with where they came from (services/funnel.py)
        source = request.form.get('source')
        new_user = User(email=email, is_admin=False, signup_ref=funnel.session_ref(),
                        signup_source=source if source in dict(funnel.SOURCES) else None)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        
        # Auto Login
        login_user(new_user)
        flash('Account created successfully!', 'success')
        return redirect(url_for('recipes_list'))
        
    return render_template('register.html', sources=funnel.SOURCES)

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
