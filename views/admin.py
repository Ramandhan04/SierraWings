from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta
from models import User, Drone, Mission, TelemetryLog
from app import db

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
    total_drones = Drone.query.count()
    total_missions = Mission.query.count()
    active_missions = Mission.query.filter_by(status='in_flight').count()
    
    # Get recent activity
    recent_missions = Mission.query.order_by(Mission.created_at.desc()).limit(10).all()
    recent_users = User.query.order_by(User.created_at.desc()).limit(10).all()
    
    # Get mission statistics
    missions_by_status = db.session.query(
        Mission.status, 
        db.func.count(Mission.id)
    ).group_by(Mission.status).all()
    
    return render_template('admin.html',
                         total_users=total_users,
                         total_drones=total_drones,
                         total_missions=total_missions,
                         active_missions=active_missions,
                         recent_missions=recent_missions,
                         recent_users=recent_users,
                         missions_by_status=missions_by_status)

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
    if user_id == current_user.id:
        flash('You cannot delete your own account.', 'error')
        return redirect(url_for('admin.manage_users'))
    
    user = User.query.get(user_id)
    if not user:
        flash('User not found.', 'error')
        return redirect(url_for('admin.manage_users'))
    
    try:
        # Check if user has active missions
        active_missions = Mission.query.filter(
            Mission.user_id == user_id,
            Mission.status.in_(['pending', 'accepted', 'in_flight'])
        ).count()
        
        if active_missions > 0:
            flash('Cannot delete user with active missions.', 'error')
            return redirect(url_for('admin.manage_users'))
        
        db.session.delete(user)
        db.session.commit()
        flash('User deleted successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash('An error occurred while deleting the user.', 'error')
    
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
        
        drone = Drone(
            name=name,
            model=model,
            status='available'
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
    total_clinics = ClinicProfile.query.count() if 'ClinicProfile' in globals() else 0
    verified_clinics = ClinicProfile.query.filter_by(is_verified=True).count() if 'ClinicProfile' in globals() else 0
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
