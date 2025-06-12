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
    
    return render_template('patient.html', 
                         missions=missions,
                         total_missions=total_missions,
                         pending_missions=pending_missions,
                         in_flight_missions=in_flight_missions,
                         completed_missions=completed_missions)

@bp.route('/request-delivery', methods=['POST'])
@login_required
@patient_required
def request_delivery():
    try:
        # Get form data
        payload_type = request.form.get('payload_type', '').strip()
        payload_weight = request.form.get('payload_weight', type=float)
        pickup_address = request.form.get('pickup_address', '').strip()
        delivery_address = request.form.get('delivery_address', '').strip()
        priority = request.form.get('priority', 'normal')
        special_instructions = request.form.get('special_instructions', '').strip()
        
        # Validation
        if not all([payload_type, pickup_address, delivery_address]):
            flash('Please fill in all required fields.', 'error')
            return redirect(url_for('patient.dashboard'))
        
        if payload_weight and payload_weight <= 0:
            flash('Payload weight must be greater than 0.', 'error')
            return redirect(url_for('patient.dashboard'))
        
        # Create new mission
        mission = Mission(
            user_id=current_user.id,
            payload_type=payload_type,
            payload_weight=payload_weight,
            pickup_address=pickup_address,
            delivery_address=delivery_address,
            priority=priority,
            special_instructions=special_instructions or None,
            status='pending'
        )
        
        db.session.add(mission)
        db.session.commit()
        
        flash('Delivery request submitted successfully! You will be notified when a clinic accepts your request.', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash('An error occurred while submitting your request. Please try again.', 'error')
    
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
