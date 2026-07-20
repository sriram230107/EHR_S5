from flask import Blueprint, redirect, url_for
from flask_login import current_user

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    """
    Root URL router. Redirects authenticated staff members to their respective 
    dashboards, and unauthenticated visitors to the login screen.
    """
    if current_user.is_authenticated:
        role_name = current_user.role.name if current_user.role else ''
        
        if role_name == 'Hospital System Administrator':
            return redirect(url_for('admin.sysadmin_dashboard'))
        elif role_name == 'Administrator':
            return redirect(url_for('admin.admin_dashboard'))
        elif role_name == 'Doctor':
            return redirect(url_for('doctor.doctor_dashboard'))
        elif role_name == 'Receptionist':
            return redirect(url_for('receptionist.receptionist_dashboard'))
            
    return redirect(url_for('auth.login'))
