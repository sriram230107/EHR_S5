from flask import request
from app import db
from app.models.audit_log import AuditLog
from flask_login import current_user

def log_action(action, details, user_id=None, username_attempted=None):
    """
    Utility function to write an entry to the AuditLog database.
    Automatically resolves the current logged-in user and request IP address if not supplied.
    """
    if user_id is None and current_user and current_user.is_authenticated:
        user_id = current_user.id
        
    # Get request IP address
    ip_address = request.remote_addr if request else '127.0.0.1'
    if ip_address == '::1':
        ip_address = '127.0.0.1'
        
    log_entry = AuditLog(
        user_id=user_id,
        username_attempted=username_attempted,
        action=action,
        ip_address=ip_address,
        details=details
    )
    
    try:
        db.session.add(log_entry)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"Error logging action '{action}': {e}")
