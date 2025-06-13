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
from models import User, Drone, Mission, TelemetryLog, ClinicProfile
from models_extensions import Feedback
from models_hospital import HospitalPatient, MedicalRecord, PatientDataRequest, DataProcessingLog
import auth
from views.patient import bp as patient_bp
from views.clinic import bp as clinic_bp
from views.admin import bp as admin_bp
from views.api import bp as api_bp
from views.live_tracking import bp as live_tracking_bp
from views.payment import bp as payment_bp
from views.feedback import bp as feedback_bp
from views.legal import bp as legal_bp
from views.hospital import bp as hospital_bp
from views.emergency import bp as emergency_bp
import json

# Register blueprints
app.register_blueprint(auth.bp)
app.register_blueprint(patient_bp, url_prefix='/patient')
app.register_blueprint(clinic_bp, url_prefix='/clinic')
app.register_blueprint(admin_bp, url_prefix='/admin')
app.register_blueprint(api_bp, url_prefix='/api')
app.register_blueprint(live_tracking_bp)
app.register_blueprint(payment_bp)
app.register_blueprint(feedback_bp)
app.register_blueprint(legal_bp)
app.register_blueprint(hospital_bp, url_prefix='/hospital')
app.register_blueprint(emergency_bp)

# Add template filter for JSON parsing
@app.template_filter('from_json')
def from_json_filter(value):
    if value:
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return []
    return []

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

with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
