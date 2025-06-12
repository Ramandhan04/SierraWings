from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from datetime import datetime
from models import Mission, Drone, TelemetryLog, User
from app import db

bp = Blueprint('clinic', __name__)

def clinic_required(f):
    """Decorator to ensure user has clinic role"""
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'clinic':
            flash('Access denied. Clinic access required.', 'error')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

@bp.route('/')
@login_required
@clinic_required
def dashboard():
    # Get pending missions
    pending_missions = Mission.query.filter_by(status='pending').order_by(Mission.created_at.desc()).all()
    
    # Get accepted missions
    accepted_missions = Mission.query.filter_by(status='accepted').order_by(Mission.accepted_at.desc()).all()
    
    # Get in-flight missions
    in_flight_missions = Mission.query.filter_by(status='in_flight').order_by(Mission.started_at.desc()).all()
    
    # Get available drones
    available_drones = Drone.query.filter_by(status='available').all()
    
    # Get clinic statistics
    total_pending = len(pending_missions)
    total_in_flight = len(in_flight_missions)
    total_completed_today = Mission.query.filter(
        Mission.completed_at >= datetime.utcnow().date(),
        Mission.status == 'completed'
    ).count()
    
    return render_template('clinic.html',
                         pending_missions=pending_missions,
                         accepted_missions=accepted_missions,
                         in_flight_missions=in_flight_missions,
                         available_drones=available_drones,
                         total_pending=total_pending,
                         total_in_flight=total_in_flight,
                         total_completed_today=total_completed_today)

@bp.route('/mission/<int:mission_id>/accept', methods=['POST'])
@login_required
@clinic_required
def accept_mission(mission_id):
    mission = Mission.query.get(mission_id)
    if not mission:
        flash('Mission not found.', 'error')
        return redirect(url_for('clinic.dashboard'))
    
    if mission.status != 'pending':
        flash('Mission cannot be accepted at this stage.', 'error')
        return redirect(url_for('clinic.dashboard'))
    
    try:
        mission.status = 'accepted'
        mission.accepted_at = datetime.utcnow()
        db.session.commit()
        flash('Mission accepted successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash('An error occurred while accepting the mission.', 'error')
    
    return redirect(url_for('clinic.dashboard'))

@bp.route('/mission/<int:mission_id>/reject', methods=['POST'])
@login_required
@clinic_required
def reject_mission(mission_id):
    mission = Mission.query.get(mission_id)
    if not mission:
        flash('Mission not found.', 'error')
        return redirect(url_for('clinic.dashboard'))
    
    if mission.status != 'pending':
        flash('Mission cannot be rejected at this stage.', 'error')
        return redirect(url_for('clinic.dashboard'))
    
    try:
        mission.status = 'rejected'
        db.session.commit()
        flash('Mission rejected.', 'info')
    except Exception as e:
        db.session.rollback()
        flash('An error occurred while rejecting the mission.', 'error')
    
    return redirect(url_for('clinic.dashboard'))

@bp.route('/mission/<int:mission_id>/dispatch', methods=['POST'])
@login_required
@clinic_required
def dispatch_mission(mission_id):
    mission = Mission.query.get(mission_id)
    if not mission:
        flash('Mission not found.', 'error')
        return redirect(url_for('clinic.dashboard'))
    
    if mission.status != 'accepted':
        flash('Mission must be accepted before dispatching.', 'error')
        return redirect(url_for('clinic.dashboard'))
    
    # Get selected drone
    drone_id = request.form.get('drone_id', type=int)
    if not drone_id:
        flash('Please select a drone.', 'error')
        return redirect(url_for('clinic.dashboard'))
    
    drone = Drone.query.get(drone_id)
    if not drone or drone.status != 'available':
        flash('Selected drone is not available.', 'error')
        return redirect(url_for('clinic.dashboard'))
    
    try:
        # Update mission and drone status
        mission.status = 'in_flight'
        mission.drone_id = drone_id
        mission.started_at = datetime.utcnow()
        drone.status = 'in_flight'
        
        db.session.commit()
        flash('Mission dispatched successfully. Drone is now in flight.', 'success')
    except Exception as e:
        db.session.rollback()
        flash('An error occurred while dispatching the mission.', 'error')
    
    return redirect(url_for('clinic.dashboard'))

@bp.route('/mission/<int:mission_id>/complete', methods=['POST'])
@login_required
@clinic_required
def complete_mission(mission_id):
    mission = Mission.query.get(mission_id)
    if not mission:
        flash('Mission not found.', 'error')
        return redirect(url_for('clinic.dashboard'))
    
    if mission.status != 'in_flight':
        flash('Mission must be in flight to be completed.', 'error')
        return redirect(url_for('clinic.dashboard'))
    
    try:
        # Update mission status
        mission.status = 'completed'
        mission.completed_at = datetime.utcnow()
        
        # Update drone status
        if mission.drone:
            mission.drone.status = 'available'
        
        db.session.commit()
        flash('Mission completed successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash('An error occurred while completing the mission.', 'error')
    
    return redirect(url_for('clinic.dashboard'))

@bp.route('/live-operations')
@login_required
@clinic_required
def live_operations():
    # Get all in-flight missions with their telemetry data
    in_flight_missions = Mission.query.filter_by(status='in_flight').all()
    
    return render_template('live_operations.html', missions=in_flight_missions)
