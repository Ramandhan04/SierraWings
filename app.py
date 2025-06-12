import os
import logging
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_required, current_user
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix

# Set up logging
logging.basicConfig(level=logging.DEBUG)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

# Create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key-change-in-production")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Configure the database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///sierrawings.db")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Initialize extensions
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access this page.'

# Import models and views
from models import User, Drone, Mission, TelemetryLog
import auth
from views.patient import bp as patient_bp
from views.clinic import bp as clinic_bp
from views.admin import bp as admin_bp
from views.api import bp as api_bp

# Register blueprints
app.register_blueprint(auth.bp)
app.register_blueprint(patient_bp, url_prefix='/patient')
app.register_blueprint(clinic_bp, url_prefix='/clinic')
app.register_blueprint(admin_bp, url_prefix='/admin')
app.register_blueprint(api_bp, url_prefix='/api')

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def index():
    if current_user.is_authenticated:
        if current_user.role == 'patient':
            return redirect(url_for('patient.dashboard'))
        elif current_user.role == 'clinic':
            return redirect(url_for('clinic.dashboard'))
        elif current_user.role == 'admin':
            return redirect(url_for('admin.dashboard'))
    return redirect(url_for('auth.login'))

@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500

def create_sample_data():
    """Create sample data for testing"""
    from werkzeug.security import generate_password_hash
    
    # Create sample users if they don't exist
    if not User.query.filter_by(email='patient@example.com').first():
        patient_user = User(
            email='patient@example.com',
            password_hash=generate_password_hash('password123'),
            role='patient',
            first_name='John',
            last_name='Doe'
        )
        db.session.add(patient_user)
    
    if not User.query.filter_by(email='clinic@example.com').first():
        clinic_user = User(
            email='clinic@example.com',
            password_hash=generate_password_hash('password123'),
            role='clinic',
            first_name='City',
            last_name='Hospital'
        )
        db.session.add(clinic_user)
    
    if not User.query.filter_by(email='admin@example.com').first():
        admin_user = User(
            email='admin@example.com',
            password_hash=generate_password_hash('password123'),
            role='admin',
            first_name='System',
            last_name='Administrator'
        )
        db.session.add(admin_user)
    
    # Create sample drones
    if not Drone.query.first():
        drones = [
            Drone(name='SW-001', model='SierraWings Medical', status='available'),
            Drone(name='SW-002', model='SierraWings Emergency', status='available'),
            Drone(name='SW-003', model='SierraWings Standard', status='maintenance')
        ]
        for drone in drones:
            db.session.add(drone)
    
    db.session.commit()

with app.app_context():
    db.create_all()
    create_sample_data()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
