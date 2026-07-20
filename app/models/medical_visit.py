from app import db
from datetime import datetime

class MedicalVisit(db.Model):
    __tablename__ = 'medical_visits'
    
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)  # User FK
    visit_date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    symptoms = db.Column(db.Text, nullable=False)
    
    # Vitals
    vitals_bp = db.Column(db.String(20), nullable=False)  # e.g., "120/80"
    vitals_pulse = db.Column(db.Integer, nullable=False)  # bpm
    vitals_temp = db.Column(db.Float, nullable=False)      # °C or °F
    vitals_weight = db.Column(db.Float, nullable=False)    # kg
    
    # ICD Code linkage
    icd_code_id = db.Column(db.Integer, db.ForeignKey('icd_codes.id'), nullable=True)
    
    # Medical Notes
    diagnosis_notes = db.Column(db.Text, nullable=False)
    clinical_notes = db.Column(db.Text)
    
    follow_up_date = db.Column(db.Date, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    prescriptions = db.relationship('Prescription', backref='medical_visit', lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<MedicalVisit {self.id} for Patient {self.patient_id}>"


class Prescription(db.Model):
    __tablename__ = 'prescriptions'
    
    id = db.Column(db.Integer, primary_key=True)
    visit_id = db.Column(db.Integer, db.ForeignKey('medical_visits.id'), nullable=False)
    medication_name = db.Column(db.String(100), nullable=False)
    dosage = db.Column(db.String(50), nullable=False)  # e.g., "500 mg"
    frequency = db.Column(db.String(50), nullable=False)  # e.g., "Twice a day"
    duration = db.Column(db.String(50), nullable=False)  # e.g., "5 days"
    instructions = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<Prescription {self.id} - {self.medication_name}>"
