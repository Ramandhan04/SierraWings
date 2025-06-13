from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from models import User
from models_extensions import Feedback
from app import db
from datetime import datetime

bp = Blueprint('feedback', __name__)

@bp.route('/feedback')
@login_required
def feedback_form():
    """Display feedback form"""
    return render_template('feedback_form.html')

@bp.route('/feedback', methods=['POST'])
@login_required
def submit_feedback():
    """Submit feedback"""
    try:
        subject = request.form.get('subject', '').strip()
        message = request.form.get('message', '').strip()
        rating = int(request.form.get('rating', 5))
        category = request.form.get('category', 'general')
        
        if not subject or not message:
            flash('Please fill in all required fields.', 'error')
            return redirect(url_for('feedback.feedback_form'))
        
        # Create feedback entry
        feedback = Feedback(
            user_id=current_user.id,
            subject=subject,
            message=message,
            rating=rating,
            category=category,
            status='pending'
        )
        
        db.session.add(feedback)
        db.session.commit()
        
        flash('Thank you for your feedback! We will review it shortly.', 'success')
        return redirect(url_for(current_user.role + '.dashboard'))
        
    except Exception as e:
        db.session.rollback()
        flash('Error submitting feedback. Please try again.', 'error')
        return redirect(url_for('feedback.feedback_form'))

@bp.route('/my-feedback')
@login_required
def my_feedback():
    """View user's feedback history"""
    feedbacks = Feedback.query.filter_by(user_id=current_user.id).order_by(Feedback.created_at.desc()).all()
    return render_template('my_feedback.html', feedbacks=feedbacks)

@bp.route('/admin/feedback')
@login_required
def admin_feedback():
    """Admin view of all feedback"""
    if current_user.role != 'admin':
        flash('Access denied.', 'error')
        return redirect(url_for('auth.login'))
    
    status_filter = request.args.get('status', 'all')
    category_filter = request.args.get('category', 'all')
    
    query = Feedback.query
    
    if status_filter != 'all':
        query = query.filter_by(status=status_filter)
    
    if category_filter != 'all':
        query = query.filter_by(category=category_filter)
    
    feedbacks = query.order_by(Feedback.created_at.desc()).all()
    
    return render_template('admin_feedback.html', 
                         feedbacks=feedbacks,
                         status_filter=status_filter,
                         category_filter=category_filter)

@bp.route('/admin/feedback/<int:feedback_id>/respond', methods=['POST'])
@login_required
def respond_to_feedback(feedback_id):
    """Admin respond to feedback"""
    if current_user.role != 'admin':
        flash('Access denied.', 'error')
        return redirect(url_for('auth.login'))
    
    feedback = Feedback.query.get_or_404(feedback_id)
    response = request.form.get('response', '').strip()
    new_status = request.form.get('status', 'reviewed')
    
    if response:
        feedback.admin_response = response
        feedback.status = new_status
        feedback.updated_at = datetime.utcnow()
        
        db.session.commit()
        flash('Response sent successfully.', 'success')
    else:
        flash('Please provide a response.', 'error')
    
    return redirect(url_for('feedback.admin_feedback'))

# This will be handled by the main app initialization