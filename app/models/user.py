from app import db
from flask_login import UserMixin
from datetime import datetime

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=False)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    phone = db.Column(db.String(20))
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Doctor specific fields (nullable, only populated for Doctors)
    specialization = db.Column(db.String(100), nullable=True)
    license_number = db.Column(db.String(50), unique=True, nullable=True)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=True)
    
    # Relationships
    appointments = db.relationship('Appointment', backref='doctor', lazy=True, foreign_keys='Appointment.doctor_id')
    medical_visits = db.relationship('MedicalVisit', backref='doctor', lazy=True)
    documents = db.relationship('Document', backref='doctor', lazy=True)
    audit_logs = db.relationship('AuditLog', backref='user', lazy=True)

    @property
    def full_name(self):
        if self.role and self.role.name == 'Doctor':
            return f"Dr. {self.first_name} {self.last_name}"
        return f"{self.first_name} {self.last_name}"

    def __repr__(self):
        return f"<User {self.username} ({self.role.name if self.role else 'No Role'})>"
