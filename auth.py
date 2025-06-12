from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from models import User
from app import db

bp = Blueprint('auth', __name__)

# Invite codes for role-based registration
INVITE_CODES = {
    'clinic': '947316',
    'admin': '583927'
}

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        remember = bool(request.form.get('remember'))
        
        if not email or not password:
            flash('Please fill in all fields.', 'error')
            return render_template('login.html')
        
        user = User.query.filter_by(email=email.lower()).first()
        
        if user and check_password_hash(user.password_hash, password):
            if user.is_active:
                login_user(user, remember=remember)
                next_page = request.args.get('next')
                if next_page:
                    return redirect(next_page)
                return redirect(url_for('index'))
            else:
                flash('Your account has been deactivated. Please contact support.', 'error')
        else:
            flash('Invalid email or password.', 'error')
    
    return render_template('login.html')

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        # Get form data
        email = request.form.get('email', '').lower().strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        role = request.form.get('role', '')
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        phone = request.form.get('phone', '').strip()
        address = request.form.get('address', '').strip()
        invite_code = request.form.get('invite_code', '').strip()
        
        # Validation
        errors = []
        
        if not all([email, password, confirm_password, role, first_name, last_name]):
            errors.append('Please fill in all required fields.')
        
        if password != confirm_password:
            errors.append('Passwords do not match.')
        
        if len(password) < 6:
            errors.append('Password must be at least 6 characters long.')
        
        if role not in ['patient', 'clinic', 'admin']:
            errors.append('Invalid role selected.')
        
        # Check invite code for clinic and admin roles
        if role in ['clinic', 'admin']:
            if not invite_code:
                errors.append(f'Invite code is required for {role} registration.')
            elif invite_code != INVITE_CODES.get(role):
                errors.append('Invalid invite code.')
        
        # Check if email already exists
        if User.query.filter_by(email=email).first():
            errors.append('An account with this email already exists.')
        
        if errors:
            for error in errors:
                flash(error, 'error')
            return render_template('register.html')
        
        # Create new user
        try:
            user = User(
                email=email,
                password_hash=generate_password_hash(password),
                role=role,
                first_name=first_name,
                last_name=last_name,
                phone=phone or None,
                address=address or None
            )
            db.session.add(user)
            db.session.commit()
            
            flash('Registration successful! You can now log in.', 'success')
            return redirect(url_for('auth.login'))
            
        except Exception as e:
            db.session.rollback()
            flash('An error occurred during registration. Please try again.', 'error')
            return render_template('register.html')
    
    return render_template('register.html')

@bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))

@bp.route('/profile')
@login_required
def profile():
    return render_template('profile.html', user=current_user)

@bp.route('/forgot-password')
def forgot_password():
    flash('Password reset functionality will be implemented soon. Please contact support.', 'info')
    return redirect(url_for('auth.login'))
