from app import db
from datetime import datetime
from sqlalchemy import Text, Boolean

class HospitalPatient(db.Model):
    """Hospital patient management with data isolation"""
    __tablename__ = 'hospital_patients'
    
    id = db.Column(db.Integer, primary_key=True)
    clinic_id = db.Column(db.Integer, db.ForeignKey('clinic_profile.id'), nullable=False)
    
    # Patient Basic Information
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    date_of_birth = db.Column(db.Date, nullable=False)
    gender = db.Column(db.String(10), nullable=False)
    phone = db.Column(db.String(20))
    email = db.Column(db.String(120))
    
    # Address Information
    address = db.Column(Text)
    city = db.Column(db.String(50))
    region = db.Column(db.String(100))
    emergency_contact_name = db.Column(db.String(100))
    emergency_contact_phone = db.Column(db.String(20))
    
    # Medical Information
    blood_type = db.Column(db.String(5))
    allergies = db.Column(Text)
    chronic_conditions = db.Column(Text)
    current_medications = db.Column(Text)
    
    # Administrative
    patient_id = db.Column(db.String(20), unique=True, nullable=False)  # Hospital-specific ID
    registration_date = db.Column(db.DateTime, default=datetime.utcnow)
    last_visit = db.Column(db.DateTime)
    is_active = db.Column(Boolean, default=True)
    
    # GDPR Compliance
    consent_data_processing = db.Column(Boolean, default=False)
    consent_data_sharing = db.Column(Boolean, default=False)
    consent_date = db.Column(db.DateTime)
    data_retention_until = db.Column(db.DateTime)
    
    # Cross-Hospital Access Authorization
    authorize_record_sharing = db.Column(Boolean, default=False)
    authorized_hospitals = db.Column(Text)  # JSON list of hospital names patient has authorized
    
    # Relationships
    clinic = db.relationship('ClinicProfile', backref='patients')
    medical_records = db.relationship('MedicalRecord', backref='patient', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<HospitalPatient {self.patient_id}: {self.first_name} {self.last_name}>'
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    @property
    def age(self):
        from datetime import date
        today = date.today()
        return today.year - self.date_of_birth.year - ((today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day))


class MedicalRecord(db.Model):
    """Medical records for hospital patients"""
    __tablename__ = 'medical_records'
    
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('hospital_patients.id'), nullable=False)
    clinic_id = db.Column(db.Integer, db.ForeignKey('clinic_profile.id'), nullable=False)
    
    # Visit Information
    visit_date = db.Column(db.DateTime, default=datetime.utcnow)
    visit_type = db.Column(db.String(50))  # consultation, emergency, follow_up, etc.
    chief_complaint = db.Column(Text)
    
    # Clinical Information
    symptoms = db.Column(Text)
    diagnosis = db.Column(Text)
    treatment_plan = db.Column(Text)
    prescribed_medications = db.Column(Text)
    lab_results = db.Column(Text)
    
    # Vital Signs
    blood_pressure = db.Column(db.String(20))
    heart_rate = db.Column(db.Integer)
    temperature = db.Column(db.Float)
    weight = db.Column(db.Float)
    height = db.Column(db.Float)
    
    # Follow-up
    next_appointment = db.Column(db.DateTime)
    follow_up_instructions = db.Column(Text)
    doctor_notes = db.Column(Text)
    
    # GDPR and Access Control
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    is_confidential = db.Column(Boolean, default=False)
    shared_with_patient = db.Column(Boolean, default=True)
    
    # Relationships
    clinic = db.relationship('ClinicProfile')
    doctor = db.relationship('User')
    
    def __repr__(self):
        return f'<MedicalRecord {self.id}: Patient {self.patient_id} - {self.visit_date}>'


class PatientDataRequest(db.Model):
    """Track cross-hospital data sharing requests"""
    __tablename__ = 'patient_data_requests'
    
    id = db.Column(db.Integer, primary_key=True)
    requesting_clinic_id = db.Column(db.Integer, db.ForeignKey('clinic_profile.id'), nullable=False)
    patient_name = db.Column(db.String(100), nullable=False)
    previous_hospital_name = db.Column(db.String(100), nullable=False)
    
    # Request Details
    request_reason = db.Column(Text, nullable=False)
    requested_data_types = db.Column(Text)  # JSON list of data types needed
    urgency_level = db.Column(db.String(20), default='normal')  # low, normal, high, emergency
    
    # Status and Approval
    status = db.Column(db.String(20), default='pending')  # pending, approved, denied, completed
    patient_consent = db.Column(Boolean, default=False)
    approval_date = db.Column(db.DateTime)
    completed_date = db.Column(db.DateTime)
    
    # GDPR Compliance
    data_shared = db.Column(Text)  # JSON of shared data summary
    access_expires = db.Column(db.DateTime)  # Temporary access expiration
    purpose_limitation = db.Column(Text)  # Specific purpose for data use
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    requesting_clinic = db.relationship('ClinicProfile')
    
    def __repr__(self):
        return f'<PatientDataRequest {self.id}: {self.patient_name} from {self.previous_hospital_name}>'


class DataProcessingLog(db.Model):
    """GDPR compliance log for all patient data processing activities"""
    __tablename__ = 'data_processing_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('hospital_patients.id'))
    clinic_id = db.Column(db.Integer, db.ForeignKey('clinic_profile.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Processing Details
    action_type = db.Column(db.String(50), nullable=False)  # create, read, update, delete, share
    data_category = db.Column(db.String(50))  # personal, medical, sensitive
    purpose = db.Column(db.String(100), nullable=False)
    legal_basis = db.Column(db.String(50), nullable=False)  # consent, vital_interests, legitimate_interests
    
    # Data Details
    data_fields_accessed = db.Column(Text)  # JSON list of specific fields
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(500))
    
    # Retention and Compliance
    retention_period = db.Column(db.Integer)  # days
    auto_delete_date = db.Column(db.DateTime)
    
    # Timestamps
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    patient = db.relationship('HospitalPatient')
    clinic = db.relationship('ClinicProfile')
    user = db.relationship('User')
    
    def __repr__(self):
        return f'<DataProcessingLog {self.id}: {self.action_type} by User {self.user_id}>'