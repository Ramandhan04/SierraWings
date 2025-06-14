from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta
from models import User, Drone, Mission, TelemetryLog, ClinicProfile
from app import db
import socket
import json
import logging
import threading
import time
import random
from drone_controller import drone_controller

bp = Blueprint('admin', __name__)

def admin_required(f):
    """Decorator to ensure user has admin role"""
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('Access denied. Administrator access required.', 'error')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

@bp.route('/')
@login_required
@admin_required
def dashboard():
    # Get system statistics
    total_users = User.query.count()
    total_missions = Mission.query.count()
    active_drones = Drone.query.filter_by(status='available').count()
    total_drones = Drone.query.count()
    
    # Get payment statistics
    try:
        from models_payment import PaymentTransaction
        total_transactions = PaymentTransaction.query.count()
        total_revenue = db.session.query(db.func.sum(PaymentTransaction.total_amount)).scalar() or 0
        admin_fees_earned = db.session.query(db.func.sum(PaymentTransaction.admin_fee_amount)).scalar() or 0
        pending_payments = PaymentTransaction.query.filter_by(status='pending').count()
        completed_payments = PaymentTransaction.query.filter_by(status='completed').count()
        
        # Recent transactions
        recent_transactions = PaymentTransaction.query.order_by(PaymentTransaction.payment_date.desc()).limit(10).all()
        
        # Daily revenue for last 7 days
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        daily_revenue = db.session.query(
            db.func.date(PaymentTransaction.payment_date).label('date'),
            db.func.sum(PaymentTransaction.total_amount).label('revenue'),
            db.func.sum(PaymentTransaction.admin_fee_amount).label('admin_fees')
        ).filter(
            PaymentTransaction.payment_date >= seven_days_ago,
            PaymentTransaction.status == 'completed'
        ).group_by(db.func.date(PaymentTransaction.payment_date)).all()
        
    except Exception:
        total_transactions = 0
        total_revenue = 0
        admin_fees_earned = 0
        pending_payments = 0
        completed_payments = 0
        recent_transactions = []
        daily_revenue = []
    
    # Get recent missions
    recent_missions = Mission.query.order_by(Mission.created_at.desc()).limit(10).all()
    recent_users = User.query.order_by(User.created_at.desc()).limit(10).all()
    
    # Get mission statistics by status
    mission_stats = db.session.query(
        Mission.status,
        db.func.count(Mission.id)
    ).group_by(Mission.status).all()
    
    mission_status_data = {status: count for status, count in mission_stats}
    
    # Get user statistics by role
    user_stats = db.session.query(
        User.role,
        db.func.count(User.id)
    ).group_by(User.role).all()
    
    user_role_data = {role: count for role, count in user_stats}
    
    # Get clinic statistics
    total_clinics = ClinicProfile.query.count()
    verified_clinics = ClinicProfile.query.filter_by(is_verified=True).count()
    pending_clinics = ClinicProfile.query.filter_by(is_verified=False).count()
    
    return render_template('admin.html',
                         total_users=total_users,
                         total_missions=total_missions,
                         active_drones=active_drones,
                         total_drones=total_drones,
                         total_transactions=total_transactions,
                         total_revenue=total_revenue,
                         admin_fees_earned=admin_fees_earned,
                         pending_payments=pending_payments,
                         completed_payments=completed_payments,
                         recent_missions=recent_missions,
                         recent_users=recent_users,
                         recent_transactions=recent_transactions,
                         mission_status_data=mission_status_data,
                         user_role_data=user_role_data,
                         daily_revenue=daily_revenue,
                         total_clinics=total_clinics,
                         verified_clinics=verified_clinics,
                         pending_clinics=pending_clinics)

@bp.route('/users')
@login_required
@admin_required
def manage_users():
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template('manage_users.html', users=users)

@bp.route('/users/create', methods=['POST'])
@login_required
@admin_required
def create_user():
    try:
        email = request.form.get('email', '').lower().strip()
        password = request.form.get('password', '')
        role = request.form.get('role', '')
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        phone = request.form.get('phone', '').strip()
        address = request.form.get('address', '').strip()
        
        # Validation
        if not all([email, password, role, first_name, last_name]):
            flash('Please fill in all required fields.', 'error')
            return redirect(url_for('admin.manage_users'))
        
        if role not in ['patient', 'clinic', 'admin']:
            flash('Invalid role selected.', 'error')
            return redirect(url_for('admin.manage_users'))
        
        if User.query.filter_by(email=email).first():
            flash('User with this email already exists.', 'error')
            return redirect(url_for('admin.manage_users'))
        
        # Create user
        user = User(
            email=email,
            password_hash=generate_password_hash(password),
            role=role,
            first_name=first_name,
            last_name=last_name,
            phone=phone or None,
            address=address or None
        )
        
        db.session.add(user)
        db.session.commit()
        flash('User created successfully.', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash('An error occurred while creating the user.', 'error')
    
    return redirect(url_for('admin.manage_users'))

@bp.route('/users/<int:user_id>/toggle-status', methods=['POST'])
@login_required
@admin_required
def toggle_user_status(user_id):
    if user_id == current_user.id:
        flash('You cannot deactivate your own account.', 'error')
        return redirect(url_for('admin.manage_users'))
    
    user = User.query.get(user_id)
    if not user:
        flash('User not found.', 'error')
        return redirect(url_for('admin.manage_users'))
    
    try:
        user.is_active = not user.is_active
        db.session.commit()
        status = "activated" if user.is_active else "deactivated"
        flash(f'User {status} successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash('An error occurred while updating user status.', 'error')
    
    return redirect(url_for('admin.manage_users'))

@bp.route('/users/<int:user_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    user = User.query.get(user_id)
    if not user:
        flash('User not found.', 'error')
        return redirect(url_for('admin.manage_users'))
    
    if user.role == 'admin':
        flash('Cannot delete admin users.', 'error')
        return redirect(url_for('admin.manage_users'))
    
    if user.id == current_user.id:
        flash('Cannot delete your own account.', 'error')
        return redirect(url_for('admin.manage_users'))
    
    try:
        # Delete user and all related data (cascading delete)
        # This will also delete missions, payment transactions, etc.
        user_name = user.full_name
        
        # Handle clinic profile if exists
        if hasattr(user, 'clinic_profile') and user.clinic_profile:
            db.session.delete(user.clinic_profile)
        
        # Handle payment transactions
        if hasattr(user, 'payment_transactions'):
            for transaction in user.payment_transactions:
                db.session.delete(transaction)
        
        # Handle missions
        for mission in user.missions:
            # Delete related telemetry logs
            for telemetry in mission.telemetry_logs:
                db.session.delete(telemetry)
            db.session.delete(mission)
        
        # Handle feedback
        if hasattr(user, 'feedbacks'):
            for feedback in user.feedbacks:
                db.session.delete(feedback)
        
        # Delete the user
        db.session.delete(user)
        db.session.commit()
        
        flash(f'User {user_name} and all associated data deleted successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'An error occurred while deleting the user: {str(e)}', 'error')
    
    return redirect(url_for('admin.manage_users'))

@bp.route('/drones')
@login_required
@admin_required
def manage_drones():
    drones = Drone.query.order_by(Drone.created_at.desc()).all()
    return render_template('manage_drones.html', drones=drones)

@bp.route('/drones/create', methods=['POST'])
@login_required
@admin_required
def create_drone():
    try:
        name = request.form.get('name', '').strip()
        model = request.form.get('model', '').strip()
        
        if not all([name, model]):
            flash('Please fill in all required fields.', 'error')
            return redirect(url_for('admin.manage_drones'))
        
        if Drone.query.filter_by(name=name).first():
            flash('Drone with this name already exists.', 'error')
            return redirect(url_for('admin.manage_drones'))
        
        # Get live GPS coordinates if provided
        live_lat = request.form.get('live_lat')
        live_lon = request.form.get('live_lon')
        
        drone = Drone(
            name=name,
            model=model,
            status='available',
            battery_level=100,
            location_lat=float(live_lat) if live_lat else None,
            location_lon=float(live_lon) if live_lon else None
        )
        
        db.session.add(drone)
        db.session.commit()
        flash('Drone created successfully.', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash('An error occurred while creating the drone.', 'error')
    
    return redirect(url_for('admin.manage_drones'))

@bp.route('/drones/<int:drone_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_drone(drone_id):
    drone = Drone.query.get(drone_id)
    if not drone:
        flash('Drone not found.', 'error')
        return redirect(url_for('admin.manage_drones'))
    
    try:
        # Check if drone has active missions
        active_missions = Mission.query.filter(
            Mission.drone_id == drone_id,
            Mission.status.in_(['accepted', 'in_flight'])
        ).count()
        
        if active_missions > 0:
            flash('Cannot delete drone with active missions.', 'error')
            return redirect(url_for('admin.manage_drones'))
        
        db.session.delete(drone)
        db.session.commit()
        flash('Drone deleted successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash('An error occurred while deleting the drone.', 'error')
    
    return redirect(url_for('admin.manage_drones'))

@bp.route('/drones/scan-wireless', methods=['POST'])
@login_required
@admin_required
def scan_wireless_drones():
    """Scan for available wireless drones on the network"""
    try:
        # Start drone controller if not running
        if not drone_controller.running:
            if not drone_controller.start_server():
                return jsonify({
                    'success': False,
                    'error': 'Failed to start drone discovery service'
                }), 500
        
        # Wait a moment for discovery
        time.sleep(2)
        
        # Get discovered drones
        discovered_drones = drone_controller.get_discovered_drones()
        
        return jsonify({
            'success': True,
            'drones': discovered_drones,
            'scan_time': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': 'Failed to scan for wireless drones',
            'details': str(e)
        }), 500

@bp.route('/drones/connect-wireless', methods=['POST'])
@login_required
@admin_required
def connect_wireless_drone():
    """Connect to a discovered wireless drone"""
    try:
        data = request.get_json()
        drone_id = data.get('drone_id')
        drone_name = data.get('drone_name')
        drone_model = data.get('drone_model')
        ip_address = data.get('ip_address')
        
        if not all([drone_id, drone_name, drone_model, ip_address]):
            return jsonify({
                'success': False,
                'error': 'Missing required drone information'
            }), 400
        
        # Check if drone already exists in database
        existing_drone = Drone.query.filter_by(name=drone_name).first()
        if existing_drone:
            return jsonify({
                'success': False,
                'error': 'Drone already registered in the system'
            }), 400
        
        # Establish MAVLink connection
        success, message = drone_controller.connect_to_drone(drone_id, ip_address)
        
        if not success:
            return jsonify({
                'success': False,
                'error': message
            }), 400
        
        # Real connection steps
        connection_steps = [
            {'step': 1, 'message': 'Establishing MAVLink connection...', 'progress': 20},
            {'step': 2, 'message': 'Waiting for Pixhawk heartbeat...', 'progress': 40},
            {'step': 3, 'message': 'Synchronizing flight parameters...', 'progress': 60},
            {'step': 4, 'message': 'Requesting system information...', 'progress': 80},
            {'step': 5, 'message': 'Live connection established!', 'progress': 100}
        ]
        
        return jsonify({
            'success': True,
            'connection_id': f"live_conn_{drone_id}_{int(time.time())}",
            'steps': connection_steps,
            'drone_info': {
                'id': drone_id,
                'name': drone_name,
                'model': drone_model,
                'ip_address': ip_address,
                'connected_at': datetime.utcnow().isoformat(),
                'connection_type': 'live_mavlink'
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': 'Failed to connect to wireless drone',
            'details': str(e)
        }), 500

@bp.route('/drones/register-wireless', methods=['POST'])
@login_required
@admin_required
def register_wireless_drone():
    """Register a connected wireless drone to the fleet"""
    try:
        data = request.get_json()
        drone_id = data.get('drone_id')
        drone_name = data.get('drone_name')
        drone_model = data.get('drone_model')
        ip_address = data.get('ip_address')
        connection_id = data.get('connection_id')
        
        if not all([drone_id, drone_name, drone_model, connection_id]):
            return jsonify({
                'success': False,
                'error': 'Missing required registration information'
            }), 400
        
        # Check if drone already exists
        existing_drone = Drone.query.filter_by(name=drone_name).first()
        if existing_drone:
            return jsonify({
                'success': False,
                'error': 'Drone already registered'
            }), 400
        
        # Create new drone record
        new_drone = Drone(
            name=drone_name,
            model=drone_model,
            status='available',
            battery_level=random.randint(80, 100),
            location_lat=8.4606,  # Freetown coordinates
            location_lon=-13.2317,
            created_at=datetime.utcnow(),
            last_maintenance=datetime.utcnow()
        )
        
        db.session.add(new_drone)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Drone {drone_name} registered successfully',
            'drone_id': new_drone.id,
            'fleet_size': Drone.query.count()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': 'Failed to register wireless drone',
            'details': str(e)
        }), 500



@bp.route('/drones/wireless-status')
@login_required
@admin_required
def wireless_status():
    """Get live wireless connectivity status for all drones"""
    try:
        drones = Drone.query.all()
        wireless_status = []
        online_count = 0
        
        for drone in drones:
            # Get real-time telemetry
            telemetry = drone_controller.get_telemetry(drone.name)
            is_live = telemetry is not None
            
            if is_live:
                online_count += 1
                # Extract real data from telemetry
                battery_level = telemetry.get('battery', {}).get('remaining', 0) if telemetry.get('battery') else drone.battery_level
                connection_quality = 'excellent'
                data_rate = 'Live MAVLink'
                last_seen = telemetry.get('timestamp', datetime.utcnow().isoformat())
                
                # Update drone with live GPS data from Pixhawk
                if telemetry.get('battery'):
                    drone.battery_level = max(0, min(100, battery_level))
                if telemetry.get('position'):
                    pos = telemetry['position']
                    drone.location_lat = pos['lat']
                    drone.location_lon = pos['lon']
                    
                    # Log GPS position update from Pixhawk
                    logging.info(f"Pixhawk GPS Update - Drone {drone.name}: {pos['lat']:.6f}, {pos['lon']:.6f}, Alt: {pos['alt']:.1f}m, Sats: {telemetry.get('gps', {}).get('satellites_visible', 0)}")
                
                db.session.commit()
            else:
                battery_level = drone.battery_level
                connection_quality = 'offline'
                data_rate = 'No Connection'
                last_seen = (datetime.utcnow() - timedelta(minutes=30)).isoformat()
            
            # Get discovered drone info if available
            discovered_drones = drone_controller.get_discovered_drones()
            discovered_info = next((d for d in discovered_drones if d['name'] == drone.name), None)
            
            # Calculate signal strength from live connection
            if is_live and discovered_info:
                signal_strength = discovered_info['signal_strength']
            elif is_live:
                signal_strength = 90  # Strong signal if live but not in discovery list
            else:
                signal_strength = 0  # No signal if offline
            
            status = {
                'id': drone.id,
                'name': drone.name,
                'model': drone.model,
                'status': drone.status,
                'battery_level': int(battery_level),
                'last_seen': last_seen,
                'signal_strength': signal_strength,
                'connection_quality': connection_quality,
                'data_rate': data_rate,
                'location': {
                    'lat': drone.location_lat,
                    'lon': drone.location_lon,
                    'altitude': telemetry.get('position', {}).get('alt') if is_live else None,
                    'gps_status': telemetry.get('gps', {}).get('fix_type') if is_live else 'No GPS',
                    'satellites': telemetry.get('gps', {}).get('satellites_visible') if is_live else 0,
                    'accuracy': telemetry.get('gps', {}).get('eph') if is_live else None
                } if drone.location_lat and drone.location_lon else None,
                'live_connected': is_live
            }
            wireless_status.append(status)
        
        return jsonify({
            'success': True,
            'drones': wireless_status,
            'total_drones': len(drones),
            'online_drones': online_count,
            'last_updated': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': 'Failed to get live wireless status',
            'details': str(e)
        }), 500

@bp.route('/drones/live-control')
@login_required
@admin_required
def live_drone_control():
    """Live drone control interface"""
    # Get all registered drones
    drones = Drone.query.order_by(Drone.created_at.desc()).all()
    
    # Get live status for connected drones
    live_drones = []
    for drone in drones:
        telemetry = drone_controller.get_telemetry(drone.name)
        live_info = {
            'id': drone.id,
            'name': drone.name,
            'model': drone.model,
            'status': drone.status,
            'live_connected': telemetry is not None,
            'telemetry': telemetry
        }
        live_drones.append(live_info)
    
    return render_template('live_drone_control.html', drones=live_drones)

@bp.route('/drones/send-command', methods=['POST'])
@login_required
@admin_required
def send_drone_command():
    """Send command to live drone"""
    try:
        data = request.get_json()
        drone_id = data.get('drone_id')
        command = data.get('command')
        params = data.get('params', {})
        
        # Get drone from database
        drone = Drone.query.get(drone_id)
        if not drone:
            return jsonify({
                'success': False,
                'error': 'Drone not found'
            }), 404
        
        # Send command to live drone
        success, message = drone_controller.send_command(drone.name, command, params)
        
        return jsonify({
            'success': success,
            'message': message,
            'command': command,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Command failed: {str(e)}'
        }), 500

@bp.route('/drones/test/<drone_name>')
@login_required
@admin_required
def test_drone_live_connection(drone_name):
    """Test live connection to specific drone"""
    try:
        # Test connection using drone controller
        test_result = drone_controller.test_connection(drone_name)
        
        if test_result:
            # Get live telemetry for comprehensive test
            telemetry = drone_controller.get_telemetry(drone_name)
            
            return jsonify({
                'success': True,
                'test_results': test_result,
                'telemetry': {
                    'battery': telemetry.get('battery', {}).get('remaining', 0) if telemetry else 0,
                    'gps_status': telemetry.get('gps', {}).get('fix_type', 'No GPS') if telemetry else 'No GPS',
                    'satellites': telemetry.get('gps', {}).get('satellites_visible', 0) if telemetry else 0,
                    'armed': telemetry.get('armed', False) if telemetry else False,
                    'flight_mode': telemetry.get('flight_mode', 'Unknown') if telemetry else 'Unknown',
                    'altitude': telemetry.get('position', {}).get('alt', 0) if telemetry else 0,
                    'lat': telemetry.get('position', {}).get('lat', 0) if telemetry else 0,
                    'lon': telemetry.get('position', {}).get('lon', 0) if telemetry else 0,
                    'signal_strength': telemetry.get('signal_strength', 0) if telemetry else 0
                }
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Connection test failed',
                'test_results': {'ping_test': {'status': 'failed', 'error': 'No response'}}
            }), 404
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Test failed: {str(e)}'
        }), 500

@bp.route('/drones/details/<drone_name>')
@login_required
@admin_required
def get_drone_details(drone_name):
    """Get detailed information about specific drone"""
    try:
        # Get drone from database
        drone = Drone.query.filter_by(name=drone_name).first()
        if not drone:
            return jsonify({
                'success': False,
                'error': 'Drone not found in database'
            }), 404
        
        # Get live telemetry
        telemetry = drone_controller.get_telemetry(drone.name)
        
        # Prepare detailed response
        details = {
            'drone_info': {
                'id': drone.id,
                'name': drone.name,
                'model': drone.model,
                'status': drone.status,
                'battery_level': drone.battery_level,
                'location': {
                    'lat': drone.location_lat,
                    'lon': drone.location_lon
                } if drone.location_lat and drone.location_lon else None,
                'created_at': drone.created_at.isoformat(),
                'last_maintenance': drone.last_maintenance.isoformat() if drone.last_maintenance else None
            },
            'live_telemetry': telemetry,
            'connection_status': 'connected' if telemetry else 'offline'
        }
        
        return jsonify({
            'success': True,
            'details': details
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to get drone details: {str(e)}'
        }), 500

@bp.route('/drones/telemetry/<int:drone_id>')
@login_required
@admin_required
def get_drone_telemetry(drone_id):
    """Get real-time telemetry from drone"""
    try:
        drone = Drone.query.get(drone_id)
        if not drone:
            return jsonify({
                'success': False,
                'error': 'Drone not found'
            }), 404
        
        # Get live telemetry
        telemetry = drone_controller.get_telemetry(drone.name)
        
        if telemetry:
            # Update database with latest telemetry
            if telemetry.get('position'):
                pos = telemetry['position']
                drone.location_lat = pos['lat']
                drone.location_lon = pos['lon']
            
            if telemetry.get('battery'):
                battery = telemetry['battery']
                drone.battery_level = max(0, min(100, battery.get('remaining', 0)))
            
            db.session.commit()
            
            return jsonify({
                'success': True,
                'telemetry': telemetry
            })
        else:
            return jsonify({
                'success': False,
                'error': 'No live telemetry available'
            }), 404
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Telemetry error: {str(e)}'
        }), 500

@bp.route('/missions')
@login_required
@admin_required
def manage_missions():
    # Get filter parameters
    status_filter = request.args.get('status', '')
    user_filter = request.args.get('user', '')
    
    # Build query
    query = Mission.query
    
    if status_filter:
        query = query.filter(Mission.status == status_filter)
    
    if user_filter:
        query = query.join(User).filter(User.email.contains(user_filter))
    
    missions = query.order_by(Mission.created_at.desc()).all()
    
    return render_template('manage_missions.html', missions=missions)

@bp.route('/missions/<int:mission_id>/cancel', methods=['POST'])
@login_required
@admin_required
def cancel_mission(mission_id):
    mission = Mission.query.get(mission_id)
    if not mission:
        flash('Mission not found.', 'error')
        return redirect(url_for('admin.manage_missions'))
    
    try:
        mission.status = 'cancelled'
        
        # Free up drone if assigned
        if mission.drone:
            mission.drone.status = 'available'
        
        db.session.commit()
        flash('Mission cancelled successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash('An error occurred while cancelling the mission.', 'error')
    
    return redirect(url_for('admin.manage_missions'))

@bp.route('/system-monitor')
@login_required
@admin_required
def system_monitor():
    from datetime import datetime, timedelta
    import psutil
    
    # System metrics
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    # Database metrics
    total_users = User.query.count()
    active_users = User.query.filter_by(is_active=True).count()
    total_clinics = ClinicProfile.query.count()
    verified_clinics = ClinicProfile.query.filter_by(is_verified=True).count()
    total_drones = Drone.query.count()
    available_drones = Drone.query.filter_by(status='available').count()
    total_missions = Mission.query.count()
    
    # Recent activity (last 24 hours)
    yesterday = datetime.utcnow() - timedelta(days=1)
    recent_users = User.query.filter(User.created_at >= yesterday).count()
    recent_missions = Mission.query.filter(Mission.created_at >= yesterday).count()
    
    # Mission status breakdown
    pending_missions = Mission.query.filter_by(status='pending').count()
    in_flight_missions = Mission.query.filter_by(status='in_flight').count()
    completed_missions = Mission.query.filter_by(status='completed').count()
    
    # Recent missions for activity feed
    recent_mission_list = Mission.query.order_by(Mission.created_at.desc()).limit(10).all()
    
    # Recent users for activity feed
    recent_user_list = User.query.order_by(User.created_at.desc()).limit(10).all()
    
    # System health indicators
    system_health = {
        'database': 'healthy',
        'storage': 'healthy' if disk.percent < 80 else 'warning' if disk.percent < 90 else 'critical',
        'memory': 'healthy' if memory.percent < 80 else 'warning' if memory.percent < 90 else 'critical',
        'cpu': 'healthy' if cpu_percent < 80 else 'warning' if cpu_percent < 90 else 'critical'
    }
    
    return render_template('system_monitor.html',
                         cpu_percent=cpu_percent,
                         memory=memory,
                         disk=disk,
                         total_users=total_users,
                         active_users=active_users,
                         total_clinics=total_clinics,
                         verified_clinics=verified_clinics,
                         total_drones=total_drones,
                         available_drones=available_drones,
                         total_missions=total_missions,
                         recent_users=recent_users,
                         recent_missions=recent_missions,
                         pending_missions=pending_missions,
                         in_flight_missions=in_flight_missions,
                         completed_missions=completed_missions,
                         recent_mission_list=recent_mission_list,
                         recent_user_list=recent_user_list,
                         system_health=system_health)
    system_stats = {
        'total_flights_today': Mission.query.filter(
            Mission.created_at >= datetime.utcnow().date()
        ).count(),
        'successful_deliveries': Mission.query.filter_by(status='completed').count(),
        'average_flight_time': 0,  # Calculate from completed missions
        'drone_utilization': 0  # Calculate from active vs total drones
    }
    
    return render_template('system_monitor.html', 
                         missions=in_flight_missions,
                         system_stats=system_stats)
