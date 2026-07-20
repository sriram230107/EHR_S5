from app import db
from datetime import datetime

class Appointment(db.Model):
    __tablename__ = 'appointments'
    
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)  # role must be Doctor
    appointment_date = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), default='Scheduled', nullable=False)  # 'Scheduled', 'Completed', 'Cancelled', 'No-Show'
    reason = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<Appointment {self.id} on {self.appointment_date}>"
