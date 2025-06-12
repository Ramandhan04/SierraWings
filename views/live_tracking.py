from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from models import Mission, Drone, TelemetryLog, User
from app import db
from datetime import datetime, timedelta
import json

bp = Blueprint('live_tracking', __name__)

@bp.route('/live-map')
@login_required
def live_map():
    """Live drone tracking map for admin and clinic users"""
    if current_user.role not in ['admin', 'clinic']:
        flash('Access denied. Live tracking is for admin and clinic users only.', 'error')
        return redirect(url_for(current_user.role + '.dashboard'))
    
    # Get active missions with drones
    active_missions = Mission.query.filter(
        Mission.status.in_(['accepted', 'in_flight', 'dispatched'])
    ).join(Drone).all()
    
    return render_template('live_map.html', 
                         active_missions=active_missions,
                         user_role=current_user.role)

@bp.route('/api/telemetry')
@login_required
def get_live_telemetry():
    """API endpoint for real-time telemetry data"""
    if current_user.role not in ['admin', 'clinic']:
        return jsonify({'error': 'Unauthorized'}), 403
    
    # Get missions from last 24 hours that are active
    since = datetime.utcnow() - timedelta(hours=24)
    
    active_missions = Mission.query.filter(
        Mission.status.in_(['accepted', 'in_flight', 'dispatched']),
        Mission.created_at >= since
    ).all()
    
    missions_data = []
    for mission in active_missions:
        # Get latest telemetry for this mission
        telemetry = TelemetryLog.query.filter_by(
            mission_id=mission.id
        ).order_by(TelemetryLog.timestamp.desc()).limit(50).all()
        
        mission_data = {
            'id': mission.id,
            'drone_id': mission.drone_id,
            'status': mission.status,
            'priority': mission.priority,
            'payload_type': mission.payload_type,
            'pickup_lat': mission.pickup_lat,
            'pickup_lon': mission.pickup_lon,
            'delivery_lat': mission.delivery_lat,
            'delivery_lon': mission.delivery_lon,
            'telemetry': [t.to_dict() for t in telemetry]
        }
        missions_data.append(mission_data)
    
    # Generate recent events for timeline
    recent_events = []
    recent_missions = Mission.query.order_by(Mission.created_at.desc()).limit(10).all()
    
    for mission in recent_missions:
        event_type = 'success' if mission.status == 'completed' else 'info'
        recent_events.append({
            'title': f'Mission #{mission.id}',
            'description': f'{mission.payload_type} - {mission.status}',
            'timestamp': mission.created_at.strftime('%H:%M'),
            'type': event_type
        })
    
    return jsonify({
        'missions': missions_data,
        'recent_events': recent_events,
        'timestamp': datetime.utcnow().isoformat()
    })

@bp.route('/api/missions/<int:mission_id>/emergency', methods=['POST'])
@login_required
def trigger_emergency_landing(mission_id):
    """Trigger emergency landing for a mission"""
    if current_user.role not in ['admin', 'clinic']:
        return jsonify({'error': 'Unauthorized'}), 403
    
    mission = Mission.query.get_or_404(mission_id)
    
    # Update mission status to emergency
    mission.status = 'emergency'
    mission.notes = (mission.notes or '') + f'\nEmergency landing triggered by {current_user.full_name} at {datetime.utcnow()}'
    
    # Create emergency telemetry log
    if mission.drone_id:
        emergency_log = TelemetryLog(
            mission_id=mission.id,
            latitude=mission.delivery_lat or 0,
            longitude=mission.delivery_lon or 0,
            altitude=50.0,  # Emergency descent altitude
            heading=0.0,
            speed=0.0,
            battery_level=50,
            signal_strength=80,
            flight_mode='EMERGENCY_LANDING',
            temperature=25.0,
            wind_speed=5.0,
            wind_direction=180.0
        )
        db.session.add(emergency_log)
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Emergency landing initiated',
        'mission_id': mission_id,
        'status': mission.status
    })

@bp.route('/api/missions/<int:mission_id>/landing-spot', methods=['POST'])
@login_required
def set_landing_spot(mission_id):
    """Set emergency landing spot coordinates"""
    if current_user.role not in ['admin', 'clinic']:
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.get_json()
    latitude = data.get('latitude')
    longitude = data.get('longitude')
    
    if not latitude or not longitude:
        return jsonify({'error': 'Invalid coordinates'}), 400
    
    mission = Mission.query.get_or_404(mission_id)
    
    # Update mission with emergency landing coordinates
    mission.delivery_lat = latitude
    mission.delivery_lon = longitude
    mission.notes = (mission.notes or '') + f'\nEmergency landing spot set: {latitude}, {longitude} by {current_user.full_name}'
    
    # Create landing spot telemetry log
    landing_log = TelemetryLog(
        mission_id=mission.id,
        latitude=latitude,
        longitude=longitude,
        altitude=0.0,  # Ground level for landing
        heading=0.0,
        speed=0.0,
        battery_level=30,
        signal_strength=90,
        flight_mode='LANDING',
        temperature=25.0,
        wind_speed=3.0,
        wind_direction=90.0
    )
    db.session.add(landing_log)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Landing spot coordinates set',
        'coordinates': {'lat': latitude, 'lng': longitude}
    })

@bp.route('/api/drone-simulation/<int:mission_id>')
@login_required
def simulate_drone_movement(mission_id):
    """Simulate drone movement for testing (admin only)"""
    if current_user.role != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    
    mission = Mission.query.get_or_404(mission_id)
    
    if not mission.drone_id:
        return jsonify({'error': 'No drone assigned to mission'}), 400
    
    # Generate realistic telemetry data for simulation
    import random
    
    # Simulate flight path from pickup to delivery
    start_lat = mission.pickup_lat or 8.4657  # Default to Freetown
    start_lon = mission.pickup_lon or -11.7799
    end_lat = mission.delivery_lat or 8.4500
    end_lon = mission.delivery_lon or -11.7500
    
    # Create several telemetry points along the route
    num_points = 10
    for i in range(num_points):
        progress = i / (num_points - 1)
        
        # Interpolate position
        current_lat = start_lat + (end_lat - start_lat) * progress
        current_lon = start_lon + (end_lon - start_lon) * progress
        
        # Add some random variation for realistic movement
        current_lat += random.uniform(-0.001, 0.001)
        current_lon += random.uniform(-0.001, 0.001)
        
        # Simulate flight parameters
        altitude = 100 + random.uniform(-20, 20)  # 80-120m altitude
        speed = 15 + random.uniform(-5, 5)  # 10-20 m/s
        battery = max(20, 100 - (progress * 60))  # Battery drains during flight
        signal = max(60, 100 - random.uniform(0, 20))  # Signal strength varies
        
        telemetry_log = TelemetryLog(
            mission_id=mission.id,
            latitude=current_lat,
            longitude=current_lon,
            altitude=altitude,
            heading=random.uniform(0, 360),
            speed=speed,
            battery_level=int(battery),
            signal_strength=int(signal),
            flight_mode='AUTO' if progress < 0.9 else 'LANDING',
            temperature=25 + random.uniform(-5, 5),
            wind_speed=random.uniform(2, 10),
            wind_direction=random.uniform(0, 360)
        )
        db.session.add(telemetry_log)
    
    # Update mission status
    if mission.status == 'accepted':
        mission.status = 'in_flight'
        mission.started_at = datetime.utcnow()
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': f'Generated {num_points} telemetry points for mission {mission_id}',
        'mission_status': mission.status
    })