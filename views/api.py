from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from datetime import datetime, timedelta
import random
import math
from models import Mission, TelemetryLog, Drone
from app import db

bp = Blueprint('api', __name__)

@bp.route('/telemetry')
@login_required
def get_telemetry():
    """Get telemetry data for a specific mission or all active missions"""
    mission_id = request.args.get('mission_id', type=int)
    
    if mission_id:
        # Get telemetry for specific mission
        mission = Mission.query.get(mission_id)
        if not mission:
            return jsonify({'error': 'Mission not found'}), 404
        
        # Check if user has access to this mission
        if current_user.role == 'patient' and mission.user_id != current_user.id:
            return jsonify({'error': 'Access denied'}), 403
        
        telemetry = TelemetryLog.query.filter_by(mission_id=mission_id).order_by(TelemetryLog.timestamp.desc()).limit(100).all()
        return jsonify([t.to_dict() for t in telemetry])
    
    else:
        # Get telemetry for all active missions (clinic/admin only)
        if current_user.role not in ['clinic', 'admin']:
            return jsonify({'error': 'Access denied'}), 403
        
        # Get all in-flight missions
        in_flight_missions = Mission.query.filter_by(status='in_flight').all()
        
        telemetry_data = {}
        for mission in in_flight_missions:
            latest_telemetry = TelemetryLog.query.filter_by(mission_id=mission.id).order_by(TelemetryLog.timestamp.desc()).limit(10).all()
            telemetry_data[mission.id] = [t.to_dict() for t in latest_telemetry]
        
        return jsonify(telemetry_data)

@bp.route('/active-missions')
@login_required
def get_active_missions():
    """Get active missions for real-time tracking"""
    missions = Mission.query.filter(
        Mission.status.in_(['accepted', 'in_flight', 'dispatched'])
    ).order_by(Mission.created_at.desc()).all()
    
    active_missions = []
    for mission in missions:
        mission_data = {
            'id': mission.id,
            'user_name': mission.user.full_name,
            'user_email': mission.user.email,
            'payload_type': mission.payload_type,
            'payload_weight': mission.payload_weight,
            'status': mission.status,
            'pickup_address': mission.pickup_address,
            'delivery_address': mission.delivery_address,
            'pickup_lat': mission.pickup_lat,
            'pickup_lon': mission.pickup_lon,
            'delivery_lat': mission.delivery_lat,
            'delivery_lon': mission.delivery_lon,
            'created_at': mission.created_at.isoformat() if mission.created_at else None
        }
        active_missions.append(mission_data)
    
    return jsonify(active_missions)

@bp.route('/mission/<int:mission_id>/tracking')
@login_required
def get_mission_tracking(mission_id):
    """Get tracking data for a specific mission"""
    mission = Mission.query.get_or_404(mission_id)
    
    # Get latest telemetry data
    latest_telemetry = None
    if mission.drone:
        latest_telemetry = TelemetryLog.query.filter_by(
            mission_id=mission_id
        ).order_by(TelemetryLog.timestamp.desc()).first()
    
    tracking_data = {
        'id': mission.id,
        'user_name': mission.user.full_name,
        'status': mission.status,
        'payload_type': mission.payload_type,
        'pickup_address': mission.pickup_address,
        'delivery_address': mission.delivery_address,
        'pickup_lat': mission.pickup_lat,
        'pickup_lon': mission.pickup_lon,
        'delivery_lat': mission.delivery_lat,
        'delivery_lon': mission.delivery_lon,
        'drone_name': mission.drone.name if mission.drone else None,
        'drone_lat': latest_telemetry.latitude if latest_telemetry else None,
        'drone_lon': latest_telemetry.longitude if latest_telemetry else None,
        'battery_level': latest_telemetry.battery_level if latest_telemetry else None,
        'speed': latest_telemetry.speed if latest_telemetry else None,
        'altitude': latest_telemetry.altitude if latest_telemetry else None,
        'route_points': []
    }
    
    # Get route points for tracking line
    if mission.drone:
        telemetry_points = TelemetryLog.query.filter_by(
            mission_id=mission_id
        ).order_by(TelemetryLog.timestamp.asc()).all()
        
        tracking_data['route_points'] = [
            [log.latitude, log.longitude] for log in telemetry_points
            if log.latitude and log.longitude
        ]
    
    return jsonify(tracking_data)

@bp.route('/mission/<int:mission_id>/drone-position')
@login_required
def get_drone_position(mission_id):
    """Get current drone position for a mission"""
    mission = Mission.query.get_or_404(mission_id)
    
    if not mission.drone:
        return jsonify({'error': 'No drone assigned to this mission'}), 404
    
    # Get latest telemetry
    latest_telemetry = TelemetryLog.query.filter_by(
        mission_id=mission_id
    ).order_by(TelemetryLog.timestamp.desc()).first()
    
    if not latest_telemetry:
        return jsonify({'error': 'No telemetry data available'}), 404
    
    position_data = {
        'lat': latest_telemetry.latitude,
        'lon': latest_telemetry.longitude,
        'altitude': latest_telemetry.altitude,
        'heading': latest_telemetry.heading,
        'speed': latest_telemetry.speed,
        'battery_level': latest_telemetry.battery_level,
        'signal_strength': latest_telemetry.signal_strength,
        'drone_name': mission.drone.name,
        'timestamp': latest_telemetry.timestamp.isoformat()
    }
    
    return jsonify(position_data)

@bp.route('/notifications')
@login_required
def get_notifications():
    """Get real-time notifications for current user"""
    from datetime import datetime, timedelta
    
    notifications = []
    
    # Check for mission updates
    if current_user.role == 'patient':
        # Check for mission status updates
        recent_missions = Mission.query.filter_by(user_id=current_user.id).filter(
            Mission.created_at > datetime.utcnow() - timedelta(minutes=5)
        ).all()
        
        for mission in recent_missions:
            if mission.status == 'accepted':
                notifications.append({
                    'id': f'mission_{mission.id}_accepted',
                    'type': 'mission_update',
                    'message': f'Your delivery request #{mission.id} has been accepted by a clinic!',
                    'url': f'/patient/track/{mission.id}',
                    'duration': 10000
                })
            elif mission.status == 'in_flight':
                notifications.append({
                    'id': f'mission_{mission.id}_in_flight',
                    'type': 'mission_update',
                    'message': f'Your medical delivery #{mission.id} is now in transit!',
                    'url': f'/patient/track/{mission.id}',
                    'duration': 8000
                })
            elif mission.status == 'completed':
                notifications.append({
                    'id': f'mission_{mission.id}_completed',
                    'type': 'success',
                    'message': f'Your medical delivery #{mission.id} has been completed successfully!',
                    'url': f'/patient/track/{mission.id}',
                    'duration': 12000
                })
    
    elif current_user.role == 'clinic':
        # Check for new mission requests
        pending_missions = Mission.query.filter_by(status='pending').filter(
            Mission.created_at > datetime.utcnow() - timedelta(minutes=5)
        ).all()
        
        for mission in pending_missions:
            notifications.append({
                'id': f'new_mission_{mission.id}',
                'type': 'mission_update',
                'message': f'New emergency delivery request: {mission.payload_type} - {mission.payload_weight}kg',
                'url': '/clinic/dashboard',
                'duration': 15000
            })
        
        # Check for urgent/emergency missions
        emergency_missions = Mission.query.filter_by(
            status='pending', 
            priority='emergency'
        ).filter(
            Mission.created_at > datetime.utcnow() - timedelta(minutes=10)
        ).all()
        
        for mission in emergency_missions:
            notifications.append({
                'id': f'emergency_{mission.id}',
                'type': 'emergency',
                'message': f'🚨 EMERGENCY: Urgent medical delivery needed - {mission.payload_type}',
                'url': '/clinic/dashboard',
                'duration': 20000
            })
    
    elif current_user.role == 'admin':
        # Check for payment notifications - skip if table doesn't exist
        try:
            from models_payment import PaymentTransaction
            recent_payments = PaymentTransaction.query.filter_by(status='completed').filter(
                PaymentTransaction.payment_date > datetime.utcnow() - timedelta(minutes=5)
            ).all()
            
            for payment in recent_payments:
                notifications.append({
                    'id': f'payment_{payment.id}',
                    'type': 'payment',
                    'message': f'New payment received: {payment.total_amount:.2f} NLE (Mission #{payment.mission_id})',
                    'url': '/admin/payment-management',
                    'duration': 8000
                })
        except Exception:
            # Payment table not ready yet, skip payment notifications
            pass
        
        # Check for system alerts
        low_battery_drones = Drone.query.filter(Drone.battery_level < 20).all()
        for drone in low_battery_drones:
            notifications.append({
                'id': f'low_battery_{drone.id}',
                'type': 'warning',
                'message': f'Drone {drone.name} has low battery: {drone.battery_level}%',
                'url': '/admin/manage-drones',
                'duration': 10000
            })
    
    return jsonify(notifications)

# Production system - telemetry comes from authentic drone hardware only

@bp.route('/clinics')
@login_required
def get_clinics():
    """Get all verified clinics for patient search"""
    from models import ClinicProfile
    
    clinics = ClinicProfile.query.filter_by(is_active=True).all()
    
    clinic_data = []
    for clinic in clinics:
        clinic_info = {
            'id': clinic.id,
            'clinic_name': clinic.clinic_name,
            'address': clinic.address,
            'city': clinic.city,
            'state': clinic.state,
            'latitude': clinic.latitude,
            'longitude': clinic.longitude,
            'specialties': clinic.specialties,
            'description': clinic.description,
            'operating_hours': clinic.operating_hours,
            'emergency_contact': clinic.emergency_contact,
            'website': clinic.website,
            'service_radius': clinic.service_radius,
            'is_verified': clinic.is_verified,
            'license_number': clinic.license_number
        }
        clinic_data.append(clinic_info)
    
    return jsonify(clinic_data)

@bp.route('/missions/<int:mission_id>/start', methods=['POST'])
@login_required
def start_mission_api(mission_id):
    """Start a mission via API"""
    mission = Mission.query.get_or_404(mission_id)
    
    if mission.status != 'accepted':
        return jsonify({'error': 'Mission must be accepted before starting'}), 400
    
    try:
        # Update mission status
        mission.status = 'in_flight'
        mission.started_at = datetime.utcnow()
        
        # Assign available drone if not already assigned
        if not mission.drone:
            available_drone = Drone.query.filter_by(status='available').first()
            if available_drone:
                mission.drone = available_drone
                available_drone.status = 'in_flight'
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Mission #{mission_id} started successfully',
            'status': mission.status
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@bp.route('/missions/<int:mission_id>/accept', methods=['POST'])
@login_required
def accept_mission_api(mission_id):
    """API endpoint to accept a mission"""
    if current_user.role != 'clinic':
        return jsonify({'error': 'Access denied'}), 403
    
    mission = Mission.query.get(mission_id)
    if not mission:
        return jsonify({'error': 'Mission not found'}), 404
    
    if mission.status != 'pending':
        return jsonify({'error': 'Mission cannot be accepted'}), 400
    
    try:
        mission.status = 'accepted'
        mission.accepted_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Mission accepted successfully',
            'mission': {
                'id': mission.id,
                'status': mission.status,
                'accepted_at': mission.accepted_at.isoformat()
            }
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to accept mission'}), 500

@bp.route('/missions/<int:mission_id>/reject', methods=['POST'])
@login_required
def reject_mission_api(mission_id):
    """API endpoint to reject a mission"""
    if current_user.role != 'clinic':
        return jsonify({'error': 'Access denied'}), 403
    
    mission = Mission.query.get(mission_id)
    if not mission:
        return jsonify({'error': 'Mission not found'}), 404
    
    if mission.status != 'pending':
        return jsonify({'error': 'Mission cannot be rejected'}), 400
    
    try:
        mission.status = 'rejected'
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Mission rejected',
            'mission': {
                'id': mission.id,
                'status': mission.status
            }
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to reject mission'}), 500

@bp.route('/missions/<int:mission_id>/dispatch', methods=['POST'])
@login_required
def dispatch_mission_api(mission_id):
    """API endpoint to dispatch a mission"""
    if current_user.role != 'clinic':
        return jsonify({'error': 'Access denied'}), 403
    
    mission = Mission.query.get(mission_id)
    if not mission:
        return jsonify({'error': 'Mission not found'}), 404
    
    if mission.status != 'accepted':
        return jsonify({'error': 'Mission must be accepted before dispatch'}), 400
    
    drone_id = request.json.get('drone_id') if request.json else None
    if not drone_id:
        return jsonify({'error': 'Drone ID required'}), 400
    
    drone = Drone.query.get(drone_id)
    if not drone or drone.status != 'available':
        return jsonify({'error': 'Drone not available'}), 400
    
    try:
        mission.status = 'in_flight'
        mission.drone_id = drone_id
        mission.started_at = datetime.utcnow()
        drone.status = 'in_flight'
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Mission dispatched successfully',
            'mission': {
                'id': mission.id,
                'status': mission.status,
                'drone_id': drone_id,
                'started_at': mission.started_at.isoformat()
            }
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to dispatch mission'}), 500

@bp.route('/drones/available')
@login_required
def get_available_drones():
    """Get list of available drones"""
    if current_user.role not in ['clinic', 'admin']:
        return jsonify({'error': 'Access denied'}), 403
    
    drones = Drone.query.filter_by(status='available').all()
    
    return jsonify([{
        'id': drone.id,
        'name': drone.name,
        'model': drone.model,
        'battery_level': drone.battery_level,
        'status': drone.status
    } for drone in drones])

@bp.route('/missions/stats')
@login_required
def get_mission_stats():
    """Get mission statistics"""
    if current_user.role == 'patient':
        # Patient can only see their own stats
        missions = Mission.query.filter_by(user_id=current_user.id).all()
    else:
        # Clinic and admin can see all stats
        missions = Mission.query.all()
    
    stats = {
        'total': len(missions),
        'pending': len([m for m in missions if m.status == 'pending']),
        'accepted': len([m for m in missions if m.status == 'accepted']),
        'in_flight': len([m for m in missions if m.status == 'in_flight']),
        'completed': len([m for m in missions if m.status == 'completed']),
        'cancelled': len([m for m in missions if m.status == 'cancelled']),
        'rejected': len([m for m in missions if m.status == 'rejected'])
    }
    
    return jsonify(stats)

@bp.route('/mission/<int:mission_id>', methods=['GET'])
@login_required
def get_mission_details(mission_id):
    """Get detailed mission information"""
    mission = Mission.query.get(mission_id)
    if not mission:
        return jsonify({'error': 'Mission not found'}), 404
    
    # Check access permissions
    if current_user.role == 'patient' and mission.user_id != current_user.id:
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        mission_data = {
            'id': mission.id,
            'status': mission.status,
            'priority': mission.priority,
            'payload_type': mission.payload_type,
            'payload_weight': mission.payload_weight,
            'pickup_address': mission.pickup_address,
            'delivery_address': mission.delivery_address,
            'special_instructions': mission.special_instructions,
            'notes': mission.notes,
            'created_at': mission.created_at.isoformat() if mission.created_at else None,
            'accepted_at': mission.accepted_at.isoformat() if mission.accepted_at else None,
            'started_at': mission.started_at.isoformat() if mission.started_at else None,
            'completed_at': mission.completed_at.isoformat() if mission.completed_at else None,
            'user': {
                'id': mission.user.id,
                'full_name': mission.user.full_name,
                'email': mission.user.email
            },
            'drone': {
                'id': mission.drone.id,
                'name': mission.drone.name,
                'model': mission.drone.model
            } if mission.drone else None
        }
        
        return jsonify(mission_data)
    except Exception as e:
        return jsonify({'error': 'Failed to fetch mission details'}), 500

@bp.route('/drone/<int:drone_id>', methods=['GET'])
@login_required
def get_drone_details(drone_id):
    """Get detailed drone information"""
    if current_user.role not in ['clinic', 'admin']:
        return jsonify({'error': 'Access denied'}), 403
    
    drone = Drone.query.get(drone_id)
    if not drone:
        return jsonify({'error': 'Drone not found'}), 404
    
    try:
        drone_data = {
            'id': drone.id,
            'name': drone.name,
            'model': drone.model,
            'status': drone.status,
            'battery_level': drone.battery_level,
            'location_lat': drone.location_lat,
            'location_lon': drone.location_lon,
            'created_at': drone.created_at.isoformat() if drone.created_at else None,
            'last_maintenance': drone.last_maintenance.isoformat() if drone.last_maintenance else None
        }
        
        return jsonify(drone_data)
    except Exception as e:
        return jsonify({'error': 'Failed to fetch drone details'}), 500

@bp.route('/drone/<int:drone_id>/missions', methods=['GET'])
@login_required
def get_drone_missions(drone_id):
    """Get recent missions for a specific drone"""
    if current_user.role not in ['clinic', 'admin']:
        return jsonify({'error': 'Access denied'}), 403
    
    drone = Drone.query.get(drone_id)
    if not drone:
        return jsonify({'error': 'Drone not found'}), 404
    
    try:
        # Get last 10 missions for this drone
        missions = Mission.query.filter_by(drone_id=drone_id)\
                               .order_by(Mission.created_at.desc())\
                               .limit(10).all()
        
        missions_data = [{
            'id': mission.id,
            'status': mission.status,
            'priority': mission.priority,
            'payload_type': mission.payload_type,
            'created_at': mission.created_at.isoformat() if mission.created_at else None,
            'completed_at': mission.completed_at.isoformat() if mission.completed_at else None
        } for mission in missions]
        
        return jsonify(missions_data)
    except Exception as e:
        return jsonify({'error': 'Failed to fetch drone missions'}), 500
