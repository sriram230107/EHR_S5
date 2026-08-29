from app import db
from datetime import datetime

class Patient(db.Model):
    __tablename__ = 'patients'
    
    id = db.Column(db.Integer, primary_key=True)
    patient_number = db.Column(db.String(50), unique=True, nullable=False)  # format: PAT-YYYY-XXXX
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    dob = db.Column(db.Date, nullable=False)
    gender = db.Column(db.String(20), nullable=False)  # 'Male', 'Female', 'Other'
    phone = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(120))
    address = db.Column(db.String(255))
    emergency_contact_name = db.Column(db.String(100), nullable=False)
    emergency_contact_phone = db.Column(db.String(20), nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    annual_income = db.Column(db.Numeric(12, 2), nullable=True)
    
    # Relationships
    appointments = db.relationship('Appointment', backref='patient', lazy=True)
    medical_visits = db.relationship('MedicalVisit', backref='patient', lazy=True)
    documents = db.relationship('Document', backref='patient', lazy=True)
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def age(self):
        if not self.dob:
            return 0
        today = datetime.today()
        # dob is a datetime.date object. self.dob.year is safe.
        return today.year - self.dob.year - ((today.month, today.day) < (self.dob.month, self.dob.day))

    def __repr__(self):
        return f"<Patient {self.patient_number} - {self.full_name}>"
