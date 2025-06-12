import os
import sys
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content
from flask import url_for, current_app

sendgrid_key = os.environ.get('SENDGRID_API_KEY')
if not sendgrid_key:
    print('Warning: SENDGRID_API_KEY environment variable not set')

def send_email(to_email, from_email, subject, text_content=None, html_content=None):
    """Send email using SendGrid"""
    if not sendgrid_key:
        print(f"Email not sent (no API key): {subject} to {to_email}")
        return False
    
    try:
        sg = SendGridAPIClient(sendgrid_key)
        
        message = Mail(
            from_email=Email(from_email),
            to_emails=To(to_email),
            subject=subject
        )
        
        if html_content:
            message.content = Content("text/html", html_content)
        elif text_content:
            message.content = Content("text/plain", text_content)
        
        response = sg.send(message)
        return True
    except Exception as e:
        print(f"SendGrid error: {e}")
        return False

def send_welcome_email(user_email, user_name, role):
    """Send welcome email to new users"""
    subject = "Welcome to SierraWings Emergency Drone Delivery"
    
    html_content = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <div style="background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); padding: 30px; text-align: center;">
            <h1 style="color: white; margin: 0;">Welcome to SierraWings</h1>
            <p style="color: #e3f2fd; margin: 10px 0 0 0;">Emergency Medical Drone Delivery System</p>
        </div>
        
        <div style="padding: 30px; background: #ffffff;">
            <h2 style="color: #1e3c72;">Hello {user_name},</h2>
            
            <p>Welcome to SierraWings! Your account has been successfully created as a <strong>{role.title()}</strong>.</p>
            
            <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0;">
                <h3 style="color: #1e3c72; margin-top: 0;">What's Next?</h3>
                {"<p>• Complete your clinic profile to appear in our directory</p><p>• Review incoming delivery requests</p><p>• Access live operations dashboard</p>" if role == 'clinic' else "<p>• Request emergency medical deliveries</p><p>• Track your missions in real-time</p><p>• View available medical facilities</p>" if role == 'patient' else "<p>• Manage system operations</p><p>• Monitor all drone activities</p><p>• Oversee user management</p>"}
            </div>
            
            <div style="text-align: center; margin: 30px 0;">
                <a href="{url_for('auth.login', _external=True)}" 
                   style="background: #1e3c72; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; display: inline-block;">
                    Access Your Dashboard
                </a>
            </div>
            
            <p style="color: #666; font-size: 14px; margin-top: 30px;">
                If you have any questions, please contact our support team.<br>
                This is an automated message from SierraWings Emergency Medical Services.
            </p>
        </div>
    </div>
    """
    
    return send_email(user_email, "noreply@sierrawings.com", subject, html_content=html_content)

def send_clinic_registration_confirmation(user_email, clinic_name):
    """Send confirmation email when clinic profile is registered"""
    subject = "Clinic Profile Registered - SierraWings"
    
    html_content = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <div style="background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); padding: 30px; text-align: center;">
            <h1 style="color: white; margin: 0;">Clinic Registration Confirmed</h1>
            <p style="color: #e3f2fd; margin: 10px 0 0 0;">SierraWings Medical Network</p>
        </div>
        
        <div style="padding: 30px; background: #ffffff;">
            <h2 style="color: #1e3c72;">Congratulations!</h2>
            
            <p>Your clinic <strong>{clinic_name}</strong> has been successfully registered in the SierraWings medical network.</p>
            
            <div style="background: #e8f5e8; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #4caf50;">
                <h3 style="color: #2e7d32; margin-top: 0;">✓ Your clinic is now visible to patients</h3>
                <p style="margin-bottom: 0;">Patients can now see your facility when requesting emergency medical deliveries in your service area.</p>
            </div>
            
            <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0;">
                <h3 style="color: #1e3c72; margin-top: 0;">Next Steps:</h3>
                <p>• Monitor incoming delivery requests</p>
                <p>• Update your service hours and capabilities</p>
                <p>• Review and accept emergency missions</p>
            </div>
            
            <div style="text-align: center; margin: 30px 0;">
                <a href="{url_for('clinic.dashboard', _external=True)}" 
                   style="background: #1e3c72; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; display: inline-block;">
                    Access Clinic Dashboard
                </a>
            </div>
        </div>
    </div>
    """
    
    return send_email(user_email, "noreply@sierrawings.com", subject, html_content=html_content)

def send_password_reset_email(user_email, user_name, reset_token):
    """Send password reset email"""
    subject = "Password Reset - SierraWings"
    reset_url = url_for('auth.reset_password', token=reset_token, _external=True)
    
    html_content = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <div style="background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); padding: 30px; text-align: center;">
            <h1 style="color: white; margin: 0;">Password Reset Request</h1>
            <p style="color: #e3f2fd; margin: 10px 0 0 0;">SierraWings Security</p>
        </div>
        
        <div style="padding: 30px; background: #ffffff;">
            <h2 style="color: #1e3c72;">Hello {user_name},</h2>
            
            <p>We received a request to reset your password for your SierraWings account.</p>
            
            <div style="background: #fff3cd; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #ffc107;">
                <p style="margin: 0;"><strong>Security Notice:</strong> This link will expire in 1 hour for your protection.</p>
            </div>
            
            <div style="text-align: center; margin: 30px 0;">
                <a href="{reset_url}" 
                   style="background: #dc3545; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; display: inline-block;">
                    Reset Your Password
                </a>
            </div>
            
            <p>If you didn't request this password reset, you can safely ignore this email. Your password will not be changed.</p>
            
            <p style="color: #666; font-size: 14px; margin-top: 30px;">
                For security reasons, do not share this email with anyone.<br>
                This link is valid for 1 hour only.
            </p>
        </div>
    </div>
    """
    
    return send_email(user_email, "noreply@sierrawings.com", subject, html_content=html_content)