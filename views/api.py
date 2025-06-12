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

@bp.route('/telemetry/simulate/<int:mission_id>', methods=['POST'])
@login_required
def simulate_telemetry(mission_id):
    """Generate simulated telemetry data for testing"""
    if current_user.role not in ['clinic', 'admin']:
        return jsonify({'error': 'Access denied'}), 403
    
    mission = Mission.query.get(mission_id)
    if not mission or mission.status != 'in_flight':
        return jsonify({'error': 'Mission not found or not in flight'}), 404
    
    try:
        # Generate simulated telemetry data
        # Starting point (pickup location)
        start_lat = 37.7749 + random.uniform(-0.1, 0.1)  # San Francisco area
        start_lon = -122.4194 + random.uniform(-0.1, 0.1)
        
        # Destination (delivery location)
        end_lat = start_lat + random.uniform(-0.05, 0.05)
        end_lon = start_lon + random.uniform(-0.05, 0.05)
        
        # Get existing telemetry count to determine current position
        existing_count = TelemetryLog.query.filter_by(mission_id=mission_id).count()
        
        # Calculate progress (0 to 1)
        total_waypoints = 50  # Total points in the flight path
        progress = min(existing_count / total_waypoints, 1.0)
        
        # Interpolate current position
        current_lat = start_lat + (end_lat - start_lat) * progress
        current_lon = start_lon + (end_lon - start_lon) * progress
        
        # Add some realistic variation
        current_lat += random.uniform(-0.001, 0.001)
        current_lon += random.uniform(-0.001, 0.001)
        
        # Generate telemetry entry
        telemetry = TelemetryLog(
            mission_id=mission_id,
            latitude=current_lat,
            longitude=current_lon,
            altitude=random.uniform(50, 150),  # 50-150 meters
            heading=random.uniform(0, 360),
            speed=random.uniform(10, 25),  # 10-25 m/s
            battery_level=max(20, 100 - (progress * 70)),  # Battery drains during flight
            signal_strength=random.randint(75, 100),
            flight_mode='auto',
            temperature=random.uniform(15, 25),
            wind_speed=random.uniform(0, 8),
            wind_direction=random.uniform(0, 360),
            timestamp=datetime.utcnow()
        )
        
        db.session.add(telemetry)
        db.session.commit()
        
        return jsonify(telemetry.to_dict())
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to generate telemetry data'}), 500

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
