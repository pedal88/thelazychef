"""Auth Blueprint: login, registration and logout."""
from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user, login_user, logout_user

from database.models import User, db
from routes._flat import FlatBlueprint

auth_bp = FlatBlueprint("auth", __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
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

@auth_bp.route('/logout')
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('discover'))
