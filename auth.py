from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from email_validator import validate_email, EmailNotValidError
import pyotp
import qrcode
import io
import base64
import json
import secrets
import random
import os
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
from models import User
from app import db
from email_service import send_welcome_email
import random

bp = Blueprint('auth', __name__)

# Invite codes for role-based registration (kept secure and not exposed to frontend)
INVITE_CODES = {
    'clinic': '3499',  # Hospital/Clinic Secret Code
    'admin': '7267'    # Developer Secret Code
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
        if role == 'clinic':
            if not invite_code:
                errors.append('Access denied: Medical facility registration requires an invitation code. Please contact your facility administrator.')
            elif invite_code != INVITE_CODES.get('clinic'):
                errors.append('Invalid invite code')
        elif role == 'admin':
            if not invite_code:
                errors.append('Access denied: Administrator registration requires an invitation code. Please contact the system administrator.')
            elif invite_code != INVITE_CODES.get('admin'):
                errors.append('Invalid invite code')
        
        # Check if email already exists
        if User.query.filter_by(email=email).first():
            errors.append('An account with this email already exists.')
        
        if errors:
            for error in errors:
                flash(error, 'error')
            return render_template('register.html')
        
        # Create new user
        try:
            user = User()
            user.email = email
            user.password_hash = generate_password_hash(password)
            user.role = role
            user.first_name = first_name
            user.last_name = last_name
            user.phone = phone or None
            user.address = address or None
            db.session.add(user)
            db.session.commit()
            
            # Send welcome email
            send_welcome_email(user.email, user.full_name, user.role)
            
            flash('Registration successful! Check your email for welcome instructions and you can now log in.', 'success')
            return redirect(url_for('auth.login'))
            
        except Exception as e:
            db.session.rollback()
            flash('An error occurred during registration. Please try again.', 'error')
            return render_template('register.html')
    
    return render_template('register.html')

@bp.route('/profile')
@login_required
def profile():
    return render_template('profile.html')

@bp.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    if request.method == 'POST':
        try:
            # Validate email
            email = request.form.get('email', '').strip().lower()
            
            try:
                validate_email(email)
            except EmailNotValidError:
                flash('Please enter a valid email address.', 'error')
                return render_template('edit_profile.html')
            
            # Check if email is already taken by another user
            existing_user = User.query.filter(User.email == email, User.id != current_user.id).first()
            if existing_user:
                flash('This email is already in use by another account.', 'error')
                return render_template('edit_profile.html')
            
            # Update user information
            current_user.email = email
            current_user.first_name = request.form.get('first_name', '').strip()
            current_user.last_name = request.form.get('last_name', '').strip()
            current_user.phone = request.form.get('phone', '').strip() or None
            current_user.address = request.form.get('address', '').strip() or None
            
            # Change password if provided
            current_password = request.form.get('current_password')
            new_password = request.form.get('new_password')
            confirm_password = request.form.get('confirm_password')
            
            if new_password:
                if not current_password:
                    flash('Current password is required to change password.', 'error')
                    return render_template('edit_profile.html')
                
                if not check_password_hash(current_user.password_hash, current_password):
                    flash('Current password is incorrect.', 'error')
                    return render_template('edit_profile.html')
                
                if new_password != confirm_password:
                    flash('New passwords do not match.', 'error')
                    return render_template('edit_profile.html')
                
                if len(new_password) < 6:
                    flash('Password must be at least 6 characters long.', 'error')
                    return render_template('edit_profile.html')
                
                current_user.password_hash = generate_password_hash(new_password)
            
            db.session.commit()
            flash('Profile updated successfully!', 'success')
            return redirect(url_for('auth.settings'))
            
        except Exception as e:
            db.session.rollback()
            flash('An error occurred while updating your profile.', 'error')
    
    return render_template('edit_profile.html')

@bp.route('/profile/2fa')
@login_required
def two_factor_setup():
    if current_user.two_factor_enabled:
        return render_template('2fa_manage.html')
    
    # Generate new secret for setup
    secret = pyotp.random_base32()
    session['temp_2fa_secret'] = secret
    
    # Generate QR code
    totp = pyotp.TOTP(secret)
    qr_url = totp.provisioning_uri(
        current_user.email,
        issuer_name="SierraWings Emergency Medical"
    )
    
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(qr_url)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    img_buffer = io.BytesIO()
    img.save(img_buffer, format='PNG')
    img_buffer.seek(0)
    
    qr_code_data = base64.b64encode(img_buffer.getvalue()).decode()
    
    return render_template('2fa_setup.html', 
                         secret=secret, 
                         qr_code=qr_code_data)

@bp.route('/profile/2fa/verify', methods=['POST'])
@login_required
def verify_2fa_setup():
    temp_secret = session.get('temp_2fa_secret')
    if not temp_secret:
        flash('2FA setup session expired. Please try again.', 'error')
        return redirect(url_for('auth.two_factor_setup'))
    
    token = request.form.get('token')
    if not token:
        flash('Please enter the verification code.', 'error')
        return redirect(url_for('auth.two_factor_setup'))
    
    totp = pyotp.TOTP(temp_secret)
    if totp.verify(token):
        # Generate backup codes
        backup_codes = [secrets.token_hex(4).upper() for _ in range(10)]
        
        # Save 2FA settings
        current_user.two_factor_enabled = True
        current_user.two_factor_secret = temp_secret
        current_user.backup_codes = json.dumps(backup_codes)
        
        db.session.commit()
        session.pop('temp_2fa_secret', None)
        
        flash('Two-factor authentication enabled successfully!', 'success')
        return render_template('2fa_backup_codes.html', backup_codes=backup_codes)
    else:
        flash('Invalid verification code. Please try again.', 'error')
        return redirect(url_for('auth.two_factor_setup'))

@bp.route('/profile/2fa/disable', methods=['POST'])
@login_required
def disable_2fa():
    token = request.form.get('token')
    password = request.form.get('password')
    
    if not password or not current_user.password_hash or not check_password_hash(current_user.password_hash, password):
        flash('Incorrect password.', 'error')
        return redirect(url_for('auth.two_factor_setup'))
    
    # Verify 2FA token or backup code
    is_valid = False
    if current_user.two_factor_secret:
        totp = pyotp.TOTP(current_user.two_factor_secret)
        if token and totp.verify(token):
            is_valid = True
        else:
            # Check backup codes
            backup_codes = json.loads(current_user.backup_codes or '[]')
            if token and token.upper() in backup_codes:
                backup_codes.remove(token.upper())
                current_user.backup_codes = json.dumps(backup_codes)
                is_valid = True
    
    if is_valid:
        current_user.two_factor_enabled = False
        current_user.two_factor_secret = None
        current_user.backup_codes = None
        db.session.commit()
        flash('Two-factor authentication disabled.', 'success')
    else:
        flash('Invalid verification code.', 'error')
    
    return redirect(url_for('auth.profile'))

@bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))

@bp.route('/settings')
@login_required
def settings():
    return render_template('profile.html', user=current_user)

@bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        user = User.query.filter_by(email=email).first()
        
        if user:
            # Generate secure reset token
            import secrets
            import string
            reset_token = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(64))
            user.reset_token = reset_token
            user.reset_token_expires = datetime.utcnow() + timedelta(hours=1)
            db.session.commit()
            
            # Send professional reset email
            from email_service import send_password_reset_email
            send_password_reset_email(user.email, user.full_name, reset_token)
            
        # Always show success message for security
        flash('Password reset instructions have been sent to your email address if it exists in our system.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('forgot_password.html')

@bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    user = User.query.filter_by(reset_token=token).first()
    
    if not user or not user.reset_token_expires or user.reset_token_expires < datetime.utcnow():
        flash('Invalid or expired reset token. Please request a new password reset.', 'error')
        return redirect(url_for('auth.forgot_password'))
    
    if request.method == 'POST':
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if not password or len(password) < 8:
            flash('Password must be at least 8 characters long.', 'error')
            return render_template('reset_password.html', token=token)
        
        if password != confirm_password:
            flash('Passwords do not match.', 'error')
            return render_template('reset_password.html', token=token)
        
        # Validate password strength
        import re
        if not (re.search(r'[A-Z]', password) and 
                re.search(r'[a-z]', password) and 
                re.search(r'\d', password) and 
                re.search(r'[!@#$%^&*(),.?":{}|<>]', password)):
            flash('Password must contain uppercase, lowercase, number, and special character.', 'error')
            return render_template('reset_password.html', token=token)
        
        # Update password and clear reset token
        user.password_hash = generate_password_hash(password)
        user.reset_token = None
        user.reset_token_expires = None
        db.session.commit()
        
        flash('Your password has been successfully updated. You can now log in with your new password.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('reset_password.html', token=token)
