from app import db

class ICDCode(db.Model):
    __tablename__ = 'icd_codes'
    
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False)  # e.g., 'I10'
    description = db.Column(db.String(255), nullable=False)
    keywords = db.Column(db.Text, nullable=False)  # Comma-separated search tokens for simple keyword search
    
    # Relationships
    medical_visits = db.relationship('MedicalVisit', backref='icd_code', lazy=True)

    def __repr__(self):
        return f"<ICDCode {self.code} - {self.description[:30]}...>"
