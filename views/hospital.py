from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from models import User, ClinicProfile
from models_hospital import HospitalPatient, MedicalRecord, PatientDataRequest, DataProcessingLog
from app import db
from datetime import datetime, timedelta
import json
import secrets

bp = Blueprint('hospital', __name__)

def hospital_clinic_required(f):
    """Decorator to ensure user has clinic role for hospital functions"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'clinic':
            flash('Access denied. Clinic access required.', 'error')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def log_data_access(patient_id, action_type, data_category, purpose, legal_basis, data_fields=None):
    """Log data processing activities for GDPR compliance"""
    try:
        log_entry = DataProcessingLog(
            patient_id=patient_id,
            clinic_id=current_user.clinic_profile.id,
            user_id=current_user.id,
            action_type=action_type,
            data_category=data_category,
            purpose=purpose,
            legal_basis=legal_basis,
            data_fields_accessed=json.dumps(data_fields) if data_fields else None,
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent', '')[:500]
        )
        db.session.add(log_entry)
        db.session.commit()
    except Exception as e:
        print(f"Failed to log data access: {e}")

@bp.route('/patients')
@login_required
@hospital_clinic_required
def patient_list():
    """Display hospital's patient list with data isolation"""
    if not current_user.clinic_profile:
        flash('Please complete your clinic profile first.', 'error')
        return redirect(url_for('clinic.register_clinic'))
    
    # Only show patients for current clinic
    patients = HospitalPatient.query.filter_by(
        clinic_id=current_user.clinic_profile.id,
        is_active=True
    ).order_by(HospitalPatient.last_name, HospitalPatient.first_name).all()
    
    # Log data access
    log_data_access(None, 'read', 'personal', 'patient_list_view', 'legitimate_interests')
    
    return render_template('hospital_patients.html', patients=patients)

@bp.route('/patients/register', methods=['GET', 'POST'])
@login_required
@hospital_clinic_required
def register_patient():
    """Register new patient with GDPR compliance"""
    if request.method == 'POST':
        try:
            # Generate unique patient ID
            patient_id = f"{current_user.clinic_profile.clinic_name[:3].upper()}-{secrets.token_hex(4).upper()}"
            
            # Check GDPR consent
            consent_data_processing = request.form.get('consent_data_processing') == 'on'
            consent_data_sharing = request.form.get('consent_data_sharing') == 'on'
            
            if not consent_data_processing:
                flash('Patient must consent to data processing to register.', 'error')
                return render_template('register_patient.html')
            
            # Create patient record
            patient = HospitalPatient(
                clinic_id=current_user.clinic_profile.id,
                first_name=request.form.get('first_name').strip(),
                last_name=request.form.get('last_name').strip(),
                date_of_birth=datetime.strptime(request.form.get('date_of_birth'), '%Y-%m-%d').date(),
                gender=request.form.get('gender'),
                phone=request.form.get('phone', '').strip() or None,
                email=request.form.get('email', '').strip() or None,
                address=request.form.get('address', '').strip() or None,
                city=request.form.get('city', '').strip() or None,
                region=request.form.get('region', '').strip() or None,
                emergency_contact_name=request.form.get('emergency_contact_name', '').strip() or None,
                emergency_contact_phone=request.form.get('emergency_contact_phone', '').strip() or None,
                blood_type=request.form.get('blood_type', '').strip() or None,
                allergies=request.form.get('allergies', '').strip() or None,
                chronic_conditions=request.form.get('chronic_conditions', '').strip() or None,
                current_medications=request.form.get('current_medications', '').strip() or None,
                patient_id=patient_id,
                consent_data_processing=consent_data_processing,
                consent_data_sharing=consent_data_sharing,
                consent_date=datetime.utcnow(),
                data_retention_until=datetime.utcnow() + timedelta(days=2555),  # 7 years
                authorize_record_sharing=request.form.get('authorize_record_sharing') == 'on'
            )
            
            db.session.add(patient)
            db.session.commit()
            
            # Log patient registration
            log_data_access(patient.id, 'create', 'personal', 'patient_registration', 'consent')
            
            flash(f'Patient registered successfully! Patient ID: {patient_id}', 'success')
            return redirect(url_for('hospital.patient_detail', patient_id=patient.id))
            
        except Exception as e:
            db.session.rollback()
            flash('Error registering patient. Please try again.', 'error')
            return render_template('register_patient.html')
    
    return render_template('register_patient.html')

@bp.route('/patients/<int:patient_id>')
@login_required
@hospital_clinic_required
def patient_detail(patient_id):
    """View patient details with access control"""
    patient = HospitalPatient.query.filter_by(
        id=patient_id,
        clinic_id=current_user.clinic_profile.id
    ).first_or_404()
    
    # Get medical records for this patient
    medical_records = MedicalRecord.query.filter_by(
        patient_id=patient_id
    ).order_by(MedicalRecord.visit_date.desc()).all()
    
    # Log data access
    log_data_access(patient.id, 'read', 'medical', 'patient_care', 'legitimate_interests', 
                   ['name', 'medical_history', 'records'])
    
    return render_template('patient_detail.html', patient=patient, medical_records=medical_records)

@bp.route('/patients/<int:patient_id>/medical-record', methods=['GET', 'POST'])
@login_required
@hospital_clinic_required
def add_medical_record(patient_id):
    """Add medical record for patient"""
    patient = HospitalPatient.query.filter_by(
        id=patient_id,
        clinic_id=current_user.clinic_profile.id
    ).first_or_404()
    
    if request.method == 'POST':
        try:
            medical_record = MedicalRecord(
                patient_id=patient_id,
                clinic_id=current_user.clinic_profile.id,
                created_by=current_user.id,
                visit_type=request.form.get('visit_type'),
                chief_complaint=request.form.get('chief_complaint', '').strip() or None,
                symptoms=request.form.get('symptoms', '').strip() or None,
                diagnosis=request.form.get('diagnosis', '').strip() or None,
                treatment_plan=request.form.get('treatment_plan', '').strip() or None,
                prescribed_medications=request.form.get('prescribed_medications', '').strip() or None,
                lab_results=request.form.get('lab_results', '').strip() or None,
                blood_pressure=request.form.get('blood_pressure', '').strip() or None,
                heart_rate=int(request.form.get('heart_rate', 0)) or None,
                temperature=float(request.form.get('temperature', 0)) or None,
                weight=float(request.form.get('weight', 0)) or None,
                height=float(request.form.get('height', 0)) or None,
                follow_up_instructions=request.form.get('follow_up_instructions', '').strip() or None,
                doctor_notes=request.form.get('doctor_notes', '').strip() or None,
                is_confidential=request.form.get('is_confidential') == 'on'
            )
            
            # Set next appointment if provided
            next_appointment = request.form.get('next_appointment')
            if next_appointment:
                medical_record.next_appointment = datetime.strptime(next_appointment, '%Y-%m-%dT%H:%M')
            
            db.session.add(medical_record)
            
            # Update patient's last visit
            patient.last_visit = datetime.utcnow()
            db.session.commit()
            
            # Log medical record creation
            log_data_access(patient.id, 'create', 'medical', 'medical_care', 'vital_interests')
            
            flash('Medical record added successfully.', 'success')
            return redirect(url_for('hospital.patient_detail', patient_id=patient_id))
            
        except Exception as e:
            db.session.rollback()
            flash('Error adding medical record. Please try again.', 'error')
    
    return render_template('add_medical_record.html', patient=patient)

@bp.route('/data-requests')
@login_required
@hospital_clinic_required
def data_requests():
    """View cross-hospital data sharing requests"""
    outgoing_requests = PatientDataRequest.query.filter_by(
        requesting_clinic_id=current_user.clinic_profile.id
    ).order_by(PatientDataRequest.created_at.desc()).all()
    
    return render_template('data_requests.html', outgoing_requests=outgoing_requests)

@bp.route('/request-patient-data', methods=['GET', 'POST'])
@login_required
@hospital_clinic_required
def request_patient_data():
    """Request patient data from another hospital"""
    if request.method == 'POST':
        try:
            data_request = PatientDataRequest(
                requesting_clinic_id=current_user.clinic_profile.id,
                patient_name=request.form.get('patient_name').strip(),
                previous_hospital_name=request.form.get('previous_hospital_name').strip(),
                request_reason=request.form.get('request_reason').strip(),
                requested_data_types=json.dumps(request.form.getlist('data_types')),
                urgency_level=request.form.get('urgency_level', 'normal'),
                purpose_limitation=request.form.get('purpose_limitation', '').strip() or None
            )
            
            db.session.add(data_request)
            db.session.commit()
            
            flash('Data request submitted successfully. Patient consent is required for approval.', 'success')
            return redirect(url_for('hospital.data_requests'))
            
        except Exception as e:
            db.session.rollback()
            flash('Error submitting data request. Please try again.', 'error')
    
    return render_template('request_patient_data.html')

@bp.route('/search-patient-records')
@login_required
@hospital_clinic_required
def search_patient_records():
    """Search for patient records from other hospitals (patient-authorized only)"""
    patient_name = request.args.get('patient_name', '').strip()
    hospital_name = request.args.get('hospital_name', '').strip()
    
    results = []
    
    if patient_name and hospital_name:
        # Search for patients who have authorized record sharing
        # and specifically authorized this hospital
        results = HospitalPatient.query.join(ClinicProfile).filter(
            HospitalPatient.authorize_record_sharing == True,
            HospitalPatient.first_name.ilike(f'%{patient_name.split()[0]}%'),
            ClinicProfile.clinic_name.ilike(f'%{hospital_name}%')
        ).all()
        
        # Filter results based on patient's authorized hospitals list
        authorized_results = []
        for patient in results:
            if patient.authorized_hospitals:
                try:
                    authorized_list = json.loads(patient.authorized_hospitals)
                    if current_user.clinic_profile.clinic_name in authorized_list:
                        authorized_results.append(patient)
                except:
                    pass
        
        results = authorized_results
        
        # Log search attempt
        log_data_access(None, 'read', 'personal', 'cross_hospital_search', 'legitimate_interests')
    
    return render_template('search_patient_records.html', results=results, 
                         patient_name=patient_name, hospital_name=hospital_name)

@bp.route('/gdpr-compliance')
@login_required
@hospital_clinic_required
def gdpr_compliance():
    """GDPR compliance dashboard"""
    # Get data processing logs for this clinic
    logs = DataProcessingLog.query.filter_by(
        clinic_id=current_user.clinic_profile.id
    ).order_by(DataProcessingLog.timestamp.desc()).limit(100).all()
    
    # Get patients with upcoming data retention expiry
    upcoming_expiry = HospitalPatient.query.filter_by(
        clinic_id=current_user.clinic_profile.id
    ).filter(
        HospitalPatient.data_retention_until <= datetime.utcnow() + timedelta(days=30)
    ).all()
    
    return render_template('gdpr_compliance.html', logs=logs, upcoming_expiry=upcoming_expiry)