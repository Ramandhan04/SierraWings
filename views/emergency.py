from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from models import Mission, ClinicProfile
from app import db
from datetime import datetime

bp = Blueprint('emergency', __name__)

@bp.route('/payment/emergency/<int:mission_id>')
@login_required
def emergency_payment(mission_id):
    """Handle emergency payment page"""
    mission = Mission.query.get_or_404(mission_id)
    
    # Verify this is the user's mission
    if mission.user_id != current_user.id:
        flash('Access denied.', 'error')
        return redirect(url_for('patient.dashboard'))
    
    # Calculate emergency pricing
    base_fee = 50.0
    priority_surcharge = 25.0
    weight_cost = max(0, (mission.payload_weight - 1) * 3)
    total_cost = base_fee + priority_surcharge + weight_cost
    
    return render_template('emergency_payment.html', 
                         mission=mission, 
                         total_cost=total_cost,
                         base_fee=base_fee,
                         priority_surcharge=priority_surcharge,
                         weight_cost=weight_cost)

@bp.route('/emergency/verify/<int:mission_id>', methods=['POST'])
@login_required
def verify_emergency(mission_id):
    """Verify emergency request and process payment"""
    mission = Mission.query.get_or_404(mission_id)
    
    if mission.user_id != current_user.id:
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        # Update mission status to verified
        mission.status = 'verified_emergency'
        mission.accepted_at = datetime.utcnow()
        
        # Create payment transaction
        from models_payment import PaymentTransaction
        import secrets
        
        transaction_id = f"EMERGENCY_{secrets.token_hex(8).upper()}"
        
        # Calculate costs
        base_fee = 50.0
        priority_surcharge = 25.0
        weight_cost = max(0, (mission.payload_weight - 1) * 3)
        total_amount = base_fee + priority_surcharge + weight_cost
        admin_fee = total_amount * 0.15
        net_amount = total_amount - admin_fee
        
        payment = PaymentTransaction(
            mission_id=mission.id,
            user_id=current_user.id,
            transaction_id=transaction_id,
            payment_method=request.json.get('payment_method', 'emergency_credit'),
            total_amount=total_amount,
            base_cost=base_fee,
            weight_cost=weight_cost,
            admin_fee_amount=admin_fee,
            net_amount=net_amount,
            status='completed',
            completion_date=datetime.utcnow()
        )
        
        db.session.add(payment)
        mission.payment_status = 'completed'
        
        db.session.commit()
        
        # Send confirmation emails to clinics
        verified_clinics = ClinicProfile.query.filter_by(is_verified=True, is_active=True).all()
        
        from email_service import send_emergency_confirmation_email
        for clinic in verified_clinics:
            try:
                send_emergency_confirmation_email(
                    clinic.user.email,
                    clinic.clinic_name,
                    {
                        'mission_id': mission.id,
                        'transaction_id': transaction_id,
                        'emergency_type': mission.payload_type,
                        'patient_name': current_user.full_name,
                        'total_amount': total_amount
                    }
                )
            except Exception as e:
                print(f"Failed to send confirmation to {clinic.clinic_name}: {e}")
        
        return jsonify({
            'success': True,
            'message': 'Emergency request verified and payment processed.',
            'transaction_id': transaction_id,
            'redirect_url': url_for('patient.dashboard')
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500