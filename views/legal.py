from flask import Blueprint, render_template

bp = Blueprint('legal', __name__)

@bp.route('/terms')
def terms_of_service():
    """Display Terms of Service"""
    return render_template('terms_of_service.html')

@bp.route('/privacy')
def privacy_policy():
    """Display Privacy Policy"""
    return render_template('privacy_policy.html')