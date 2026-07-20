from app import db
from datetime import datetime

class AuditLog(db.Model):
    __tablename__ = 'audit_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # Nullable for failed logins
    username_attempted = db.Column(db.String(80), nullable=True)  # For failed login logs
    action = db.Column(db.String(100), nullable=False)  # 'Login Success', 'Login Failed', 'Logout', 'Record Create', etc.
    ip_address = db.Column(db.String(45))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    details = db.Column(db.Text)

    def __repr__(self):
        return f"<AuditLog {self.id} - {self.action} by User {self.user_id or self.username_attempted}>"
