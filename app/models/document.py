from app import db
from datetime import datetime

class Document(db.Model):
    __tablename__ = 'documents'
    
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    
    # Predefined category restriction (validated at application level):
    # 'Prescription', 'Lab Report', 'Scan Report', 'X-Ray', 'Discharge Summary', 'Other'
    file_type = db.Column(db.String(50), nullable=False)
    
    file_path = db.Column(db.String(255), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<Document {self.id} - {self.file_type} for Patient {self.patient_id}>"
