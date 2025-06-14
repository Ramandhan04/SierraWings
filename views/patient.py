from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from datetime import datetime
import json
from models import Mission, Drone, TelemetryLog, User, ClinicProfile
from app import db

bp = Blueprint('patient', __name__)

def patient_required(f):
    """Decorator to ensure user has patient role"""
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'patient':
            flash('Access denied. Patient access required.', 'error')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

@bp.route('/find-clinics')
@login_required
@patient_required
def find_clinics():
    """Search and view available medical facilities"""
    return render_template('find_clinics.html')

@bp.route('/')
@login_required
@patient_required
def dashboard():
    # Get user's missions
    missions = Mission.query.filter_by(user_id=current_user.id).order_by(Mission.created_at.desc()).all()
    
    # Get mission statistics
    total_missions = len(missions)
    pending_missions = len([m for m in missions if m.status == 'pending'])
    in_flight_missions = len([m for m in missions if m.status == 'in_flight'])
    completed_missions = len([m for m in missions if m.status == 'completed'])
    
    # Get available clinics for delivery requests
    available_clinics = ClinicProfile.query.filter_by(is_verified=True, is_active=True).all()
    
    return render_template('patient.html', 
                         missions=missions,
                         total_missions=total_missions,
                         pending_missions=pending_missions,
                         in_flight_missions=in_flight_missions,
                         completed_missions=completed_missions,
                         available_clinics=available_clinics)

@bp.route('/request-delivery', methods=['POST'])
@login_required
@patient_required
def request_delivery():
    try:
        # Get form data
        clinic_id = request.form.get('clinic_id')
        payload_type = request.form.get('payload_type')
        payload_weight = request.form.get('payload_weight')
        pickup_address = request.form.get('pickup_address')
        delivery_address = request.form.get('delivery_address')
        priority = request.form.get('priority', 'normal')
        special_instructions = request.form.get('special_instructions', '')
        
        # Validation
        if not all([clinic_id, payload_type, pickup_address, delivery_address]):
            flash('Please fill in all required fields including clinic selection.', 'error')
            return redirect(url_for('patient.dashboard'))
        
        # Verify clinic exists and is active
        clinic = ClinicProfile.query.filter_by(id=clinic_id, is_verified=True, is_active=True).first()
        if not clinic:
            flash('Selected clinic is not available.', 'error')
            return redirect(url_for('patient.dashboard'))
        
        # Convert weight to float if provided
        if payload_weight:
            try:
                payload_weight = float(payload_weight)
                if payload_weight > 10:
                    flash('Maximum payload weight is 10kg.', 'error')
                    return redirect(url_for('patient.dashboard'))
            except ValueError:
                payload_weight = None
        
        # Create mission with clinic association
        mission = Mission()
        mission.user_id = current_user.id
        mission.payload_type = payload_type
        mission.payload_weight = payload_weight
        mission.pickup_address = f"{clinic.clinic_name}, {pickup_address}"
        mission.delivery_address = delivery_address
        mission.priority = priority
        mission.special_instructions = special_instructions
        mission.status = 'pending'
        mission.notes = f"Clinic: {clinic.clinic_name} (ID: {clinic_id})"
        
        db.session.add(mission)
        db.session.commit()
        
        flash(f'Delivery request submitted successfully to {clinic.clinic_name}!', 'success')
        return redirect(url_for('patient.dashboard'))
        
    except Exception as e:
        db.session.rollback()
        flash('An error occurred while submitting your request.', 'error')
        return redirect(url_for('patient.dashboard'))

@bp.route('/track/<int:mission_id>')
@login_required
@patient_required
def track_mission():
    return render_template('track_mission.html')

@bp.route('/mission/<int:mission_id>/details')
@login_required
@patient_required
def mission_details(mission_id):
    mission = Mission.query.filter_by(id=mission_id, user_id=current_user.id).first()
    if not mission:
        flash('Mission not found.', 'error')
        return redirect(url_for('patient.dashboard'))
    
    # Get telemetry data for the mission
    telemetry = TelemetryLog.query.filter_by(mission_id=mission_id).order_by(TelemetryLog.timestamp.asc()).all()
    
    return render_template('mission_details.html', mission=mission, telemetry=telemetry)

@bp.route('/mission/<int:mission_id>/cancel', methods=['POST'])
@login_required
@patient_required
def cancel_mission(mission_id):
    mission = Mission.query.filter_by(id=mission_id, user_id=current_user.id).first()
    if not mission:
        flash('Mission not found.', 'error')
        return redirect(url_for('patient.dashboard'))
    
    if mission.status not in ['pending', 'accepted']:
        flash('Mission cannot be cancelled at this stage.', 'error')
        return redirect(url_for('patient.dashboard'))
    
    try:
        mission.status = 'cancelled'
        db.session.commit()
        flash('Mission cancelled successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash('An error occurred while cancelling the mission.', 'error')
    
    return redirect(url_for('patient.dashboard'))

@bp.route('/clinics')
@login_required
@patient_required
def clinics():
    # Get all active and verified clinics
    clinics = ClinicProfile.query.filter_by(is_active=True, is_verified=True).all()
    
    # Filter by location if provided
    city = request.args.get('city')
    state = request.args.get('state')
    specialty = request.args.get('specialty')
    
    if city:
        clinics = [c for c in clinics if c.city.lower() == city.lower()]
    if state:
        clinics = [c for c in clinics if c.state.lower() == state.lower()]
    if specialty:
        clinics = [c for c in clinics if specialty.lower() in (json.loads(c.specialties or '[]'))]
    
    return render_template('clinic_directory.html', clinics=clinics)

@bp.route('/clinic/<int:clinic_id>')
@login_required
@patient_required
def clinic_details(clinic_id):
    clinic = ClinicProfile.query.get_or_404(clinic_id)
    
    # Get clinic's recent mission statistics
    clinic_missions = Mission.query.join(User).filter(User.id == clinic.user_id).all()
    total_missions = len(clinic_missions)
    completed_missions = len([m for m in clinic_missions if m.status == 'completed'])
    
    return render_template('clinic_details.html', 
                         clinic=clinic,
                         total_missions=total_missions,
                         completed_missions=completed_missions)
