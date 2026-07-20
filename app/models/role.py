from app import db

class Role(db.Model):
    __tablename__ = 'roles'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)  # 'Hospital System Administrator', 'Administrator', 'Doctor', 'Receptionist'
    description = db.Column(db.String(255))
    
    # Relationships
    users = db.relationship('User', backref='role', lazy=True)

    def __repr__(self):
        return f"<Role {self.name}>"
