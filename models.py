from datetime import datetime
from app import db
from flask_login import UserMixin

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # patient, clinic, admin
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    phone = db.Column(db.String(20))
    address = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    missions = db.relationship('Mission', backref='user', lazy=True)
    
    def __repr__(self):
        return f'<User {self.email}>'
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

class ClinicProfile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, unique=True)
    clinic_name = db.Column(db.String(100), nullable=False)
    license_number = db.Column(db.String(50), unique=True, nullable=False)
    specialties = db.Column(db.Text)  # JSON string of specialties
    description = db.Column(db.Text)
    
    # Location details
    address = db.Column(db.Text, nullable=False)
    city = db.Column(db.String(50), nullable=False)
    state = db.Column(db.String(50), nullable=False)
    zip_code = db.Column(db.String(10), nullable=False)
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    
    # Service details
    service_radius = db.Column(db.Integer, default=50)  # km
    operating_hours = db.Column(db.Text)  # JSON string
    emergency_contact = db.Column(db.String(20))
    website = db.Column(db.String(200))
    
    # Status
    is_verified = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref=db.backref('clinic_profile', uselist=False))
    
    def __repr__(self):
        return f'<ClinicProfile {self.clinic_name}>'
    
    @property
    def full_address(self):
        return f"{self.address}, {self.city}, {self.state} {self.zip_code}"

class Drone(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    model = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(20), default='available')  # available, in_flight, maintenance, offline
    battery_level = db.Column(db.Integer, default=100)
    location_lat = db.Column(db.Float)
    location_lon = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_maintenance = db.Column(db.DateTime)
    
    # Relationships
    missions = db.relationship('Mission', backref='drone', lazy=True)
    
    def __repr__(self):
        return f'<Drone {self.name}>'

class Mission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    drone_id = db.Column(db.Integer, db.ForeignKey('drone.id'))
    
    # Mission details
    payload_type = db.Column(db.String(100), nullable=False)
    payload_weight = db.Column(db.Float)
    pickup_address = db.Column(db.Text, nullable=False)
    delivery_address = db.Column(db.Text, nullable=False)
    pickup_lat = db.Column(db.Float)
    pickup_lon = db.Column(db.Float)
    delivery_lat = db.Column(db.Float)
    delivery_lon = db.Column(db.Float)
    
    # Mission status and timing
    status = db.Column(db.String(20), default='pending')  # pending, accepted, rejected, in_flight, completed, cancelled
    priority = db.Column(db.String(10), default='normal')  # low, normal, high, emergency
    estimated_duration = db.Column(db.Integer)  # in minutes
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    accepted_at = db.Column(db.DateTime)
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    
    # Additional details
    notes = db.Column(db.Text)
    special_instructions = db.Column(db.Text)
    
    # Relationships
    telemetry_logs = db.relationship('TelemetryLog', backref='mission', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Mission {self.id} - {self.status}>'
    
    @property
    def duration_str(self):
        if self.started_at and self.completed_at:
            duration = self.completed_at - self.started_at
            return str(duration).split('.')[0]  # Remove microseconds
        return "N/A"

class TelemetryLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    mission_id = db.Column(db.Integer, db.ForeignKey('mission.id'), nullable=False)
    
    # GPS and navigation data
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    altitude = db.Column(db.Float, nullable=False)
    heading = db.Column(db.Float)  # degrees
    speed = db.Column(db.Float)  # m/s
    
    # System status
    battery_level = db.Column(db.Integer, nullable=False)
    signal_strength = db.Column(db.Integer)  # percentage
    flight_mode = db.Column(db.String(20))  # auto, manual, loiter, etc.
    
    # Environmental data
    temperature = db.Column(db.Float)
    wind_speed = db.Column(db.Float)
    wind_direction = db.Column(db.Float)
    
    # Timestamps
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<TelemetryLog {self.id} - Mission {self.mission_id}>'
    
    def to_dict(self):
        """Convert telemetry data to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'mission_id': self.mission_id,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'altitude': self.altitude,
            'heading': self.heading,
            'speed': self.speed,
            'battery_level': self.battery_level,
            'signal_strength': self.signal_strength,
            'flight_mode': self.flight_mode,
            'temperature': self.temperature,
            'wind_speed': self.wind_speed,
            'wind_direction': self.wind_direction,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None
        }
