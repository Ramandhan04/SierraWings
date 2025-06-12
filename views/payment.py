from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from models import Mission, User
from app import db
from datetime import datetime
import json
import hashlib
import secrets

bp = Blueprint('payment', __name__)

@bp.route('/payment/select/<int:mission_id>')
@login_required
def select_payment(mission_id):
    """Payment method selection page"""
    mission = Mission.query.get_or_404(mission_id)
    
    # Ensure user owns this mission
    if mission.user_id != current_user.id:
        flash('Unauthorized access to payment.', 'error')
        return redirect(url_for('patient.dashboard'))
    
    # Calculate delivery fee based on distance and priority
    base_fee = 50000  # Base fee in Leones
    priority_multiplier = {'low': 1.0, 'normal': 1.2, 'high': 1.5, 'emergency': 2.0}
    total_amount = base_fee * priority_multiplier.get(mission.priority, 1.2)
    
    return render_template('payment_select.html',
                         mission_id=mission_id,
                         mission=mission,
                         payload_type=mission.payload_type,
                         priority=mission.priority,
                         amount=total_amount)

@bp.route('/payment/gateway')
@login_required
def payment_gateway():
    """Secure payment gateway"""
    mission_id = request.args.get('mission_id', type=int)
    method = request.args.get('method', '')
    amount = request.args.get('amount', type=float)
    
    if not mission_id or not method or not amount:
        flash('Invalid payment parameters.', 'error')
        return redirect(url_for('patient.dashboard'))
    
    mission = Mission.query.get_or_404(mission_id)
    
    # Ensure user owns this mission
    if mission.user_id != current_user.id:
        flash('Unauthorized access to payment.', 'error')
        return redirect(url_for('patient.dashboard'))
    
    return render_template('payment_gateway.html',
                         mission_id=mission_id,
                         method=method,
                         amount=amount)

@bp.route('/api/payment/process', methods=['POST'])
@login_required
def process_payment():
    """Process secure payment transaction"""
    try:
        data = request.get_json()
        
        mission_id = data.get('mission_id')
        payment_method = data.get('method')
        amount = data.get('amount')
        
        if not all([mission_id, payment_method, amount]):
            return jsonify({'success': False, 'message': 'Missing payment parameters'}), 400
        
        mission = Mission.query.get_or_404(mission_id)
        
        # Verify user authorization
        if mission.user_id != current_user.id:
            return jsonify({'success': False, 'message': 'Unauthorized'}), 403
        
        # Generate secure transaction ID
        transaction_id = generate_transaction_id()
        
        # Process payment based on method
        if payment_method in ['africanmoney', 'orangemoney', 'qmoney']:
            success = process_mobile_payment(data, transaction_id)
        elif payment_method == 'card':
            success = process_card_payment(data, transaction_id)
        else:
            return jsonify({'success': False, 'message': 'Invalid payment method'}), 400
        
        if success:
            # Update mission payment status
            mission.payment_status = 'completed'
            mission.payment_method = payment_method
            mission.status = 'accepted'  # Move to next stage
            
            # Add payment reference to notes
            mission.notes = (mission.notes or '') + f'\nPayment completed: {transaction_id} via {payment_method}'
            
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'Payment processed successfully',
                'transaction_id': transaction_id,
                'mission_status': mission.status
            })
        else:
            return jsonify({'success': False, 'message': 'Payment processing failed'}), 400
            
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Payment system error'}), 500

def generate_transaction_id():
    """Generate secure transaction ID"""
    timestamp = str(int(datetime.utcnow().timestamp()))
    random_part = secrets.token_hex(8)
    return f"SW{timestamp}{random_part}".upper()

def process_mobile_payment(data, transaction_id):
    """Process mobile money payment (simulated for security)"""
    # In production, this would integrate with actual mobile money APIs
    # For security, we simulate the process
    
    phone = data.get('phone', '')
    pin = data.get('pin', '')
    
    # Validate phone number format
    if not phone or len(phone) < 10:
        return False
    
    # Validate PIN (basic check)
    if not pin or len(pin) < 4:
        return False
    
    # Simulate API call to mobile money provider
    # In production: encrypt sensitive data, use OAuth, implement proper authentication
    
    # For demo: simulate success (90% success rate)
    import random
    return random.random() > 0.1

def process_card_payment(data, transaction_id):
    """Process bank card payment (simulated for security)"""
    # In production, this would integrate with payment processors like Stripe
    
    card_token = data.get('card_token', '')
    cardholder = data.get('cardholder', '')
    
    # Basic validation
    if not card_token or not cardholder:
        return False
    
    # Simulate card processing
    # In production: use tokenization, 3D Secure, fraud detection
    
    # For demo: simulate success (95% success rate for cards)
    import random
    return random.random() > 0.05

@bp.route('/payment/success/<transaction_id>')
@login_required
def payment_success(transaction_id):
    """Payment success confirmation page"""
    # Find mission by transaction reference
    mission = Mission.query.filter(
        Mission.notes.contains(transaction_id),
        Mission.user_id == current_user.id
    ).first()
    
    if not mission:
        flash('Transaction not found.', 'error')
        return redirect(url_for('patient.dashboard'))
    
    return render_template('payment_success.html',
                         transaction_id=transaction_id,
                         mission=mission)

@bp.route('/payment/failed')
@login_required
def payment_failed():
    """Payment failure page"""
    return render_template('payment_failed.html')