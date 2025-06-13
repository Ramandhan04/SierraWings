from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from datetime import datetime
import json
from models import Mission, Drone, TelemetryLog, User, ClinicProfile
from app import db
from email_service import send_clinic_registration_confirmation

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
    # Check if clinic profile exists
    clinic_profile = ClinicProfile.query.filter_by(user_id=current_user.id).first()
    
    # If no clinic profile, redirect to registration
    if not clinic_profile:
        flash('Please complete your clinic registration to access the dashboard.', 'info')
        return redirect(url_for('clinic.register_clinic'))
    
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
                         total_completed_today=total_completed_today,
                         clinic_profile=clinic_profile)

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

@bp.route('/register-clinic', methods=['GET', 'POST'])
@login_required
@clinic_required
def register_clinic():
    # Check if clinic profile already exists
    existing_profile = ClinicProfile.query.filter_by(user_id=current_user.id).first()
    if existing_profile:
        flash('Clinic profile already registered.', 'info')
        return redirect(url_for('clinic.dashboard'))
    
    if request.method == 'POST':
        try:
            # Get form data
            clinic_name = request.form.get('clinic_name')
            license_number = request.form.get('license_number')
            specialties = request.form.getlist('specialties')
            description = request.form.get('description')
            
            # Location details
            address = request.form.get('address')
            city = request.form.get('city')
            state = request.form.get('state')
            zip_code = request.form.get('zip_code', '').strip() or None
            
            # Get location coordinates
            latitude = request.form.get('latitude')
            longitude = request.form.get('longitude')
            location_permission = request.form.get('location_permission') == 'on'
            
            # Service details
            service_radius = int(request.form.get('service_radius', 50))
            emergency_contact = request.form.get('emergency_contact')
            website = request.form.get('website', '').strip() or None
            if website and not website.startswith(('http://', 'https://')):
                website = 'https://' + website
            
            # Operating hours
            operating_hours = {
                'monday': request.form.get('monday_hours'),
                'tuesday': request.form.get('tuesday_hours'),
                'wednesday': request.form.get('wednesday_hours'),
                'thursday': request.form.get('thursday_hours'),
                'friday': request.form.get('friday_hours'),
                'saturday': request.form.get('saturday_hours'),
                'sunday': request.form.get('sunday_hours'),
                'emergency_24_7': request.form.get('emergency_24_7') == 'on'
            }
            
            # Validate required fields
            if not all([clinic_name, license_number, address, city, state, zip_code]):
                flash('Please fill in all required fields.', 'error')
                return render_template('register_clinic.html')
            
            # Check for duplicate license number
            existing_license = ClinicProfile.query.filter_by(license_number=license_number).first()
            if existing_license:
                flash('License number already registered.', 'error')
                return render_template('register_clinic.html')
            
            # Create clinic profile
            clinic_profile = ClinicProfile(
                user_id=current_user.id,
                clinic_name=clinic_name,
                license_number=license_number,
                specialties=json.dumps(specialties),
                description=description,
                address=address,
                city=city,
                region=request.form.get('region'),
                state=state,
                zip_code=zip_code,
                service_radius=service_radius,
                operating_hours=json.dumps(operating_hours),
                emergency_contact=emergency_contact,
                website=website
            )
            
            db.session.add(clinic_profile)
            db.session.commit()
            
            # Send confirmation email
            send_clinic_registration_confirmation(current_user.email, clinic_name)
            
            flash('Clinic registered successfully! You should receive a confirmation email shortly.', 'success')
            return redirect(url_for('clinic.dashboard'))
            
        except Exception as e:
            db.session.rollback()
            flash('An error occurred while registering your clinic. Please try again.', 'error')
            return render_template('register_clinic.html')
    
    return render_template('register_clinic.html')

@bp.route('/profile')
@login_required
@clinic_required
def profile():
    clinic_profile = ClinicProfile.query.filter_by(user_id=current_user.id).first()
    if not clinic_profile:
        flash('Please complete your clinic registration first.', 'info')
        return redirect(url_for('clinic.register_clinic'))
    
    return render_template('clinic_profile.html', clinic_profile=clinic_profile)

@bp.route('/profile/edit', methods=['GET', 'POST'])
@login_required
@clinic_required
def edit_profile():
    clinic_profile = ClinicProfile.query.filter_by(user_id=current_user.id).first()
    if not clinic_profile:
        flash('Please complete your clinic registration first.', 'info')
        return redirect(url_for('clinic.register_clinic'))
    
    if request.method == 'POST':
        try:
            # Update clinic profile
            clinic_profile.clinic_name = request.form.get('clinic_name')
            clinic_profile.description = request.form.get('description')
            clinic_profile.address = request.form.get('address')
            clinic_profile.city = request.form.get('city')
            clinic_profile.state = request.form.get('state')
            clinic_profile.zip_code = request.form.get('zip_code')
            clinic_profile.service_radius = int(request.form.get('service_radius', 50))
            clinic_profile.emergency_contact = request.form.get('emergency_contact')
            clinic_profile.website = request.form.get('website')
            
            # Update specialties
            specialties = request.form.getlist('specialties')
            clinic_profile.specialties = json.dumps(specialties)
            
            # Update operating hours
            operating_hours = {
                'monday': request.form.get('monday_hours'),
                'tuesday': request.form.get('tuesday_hours'),
                'wednesday': request.form.get('wednesday_hours'),
                'thursday': request.form.get('thursday_hours'),
                'friday': request.form.get('friday_hours'),
                'saturday': request.form.get('saturday_hours'),
                'sunday': request.form.get('sunday_hours'),
                'emergency_24_7': request.form.get('emergency_24_7') == 'on'
            }
            clinic_profile.operating_hours = json.dumps(operating_hours)
            clinic_profile.updated_at = datetime.utcnow()
            
            db.session.commit()
            flash('Profile updated successfully!', 'success')
            return redirect(url_for('clinic.profile'))
            
        except Exception as e:
            db.session.rollback()
            flash('An error occurred while updating your profile.', 'error')
    
    return render_template('edit_clinic_profile.html', clinic_profile=clinic_profile)
