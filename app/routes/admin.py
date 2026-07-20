from flask import Blueprint, render_template, redirect, url_for, flash, abort, send_file, current_app
from flask_login import login_required, current_user
from app.routes.decorators import role_required
from app.models.user import User
from app.models.role import Role
from app.models.patient import Patient
from app.models.appointment import Appointment
from app.models.medical_visit import MedicalVisit
from app.models.audit_log import AuditLog
from app.utils import log_action
from app import db
from datetime import datetime, date
import os

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/sysadmin/dashboard')
@login_required
@role_required('Hospital System Administrator')
def sysadmin_dashboard():
    # 1. Total Patients
    total_patients = Patient.query.filter_by(is_active=True).count()
    # 2. Total Users (Staff)
    total_users = User.query.filter_by(is_active=True).count()
    # 3. Total Doctors
    doctor_role = Role.query.filter_by(name='Doctor').first()
    total_doctors = User.query.filter_by(role_id=doctor_role.id, is_active=True).count() if doctor_role else 0
    # 4. Today's Visits
    today_start = datetime.combine(date.today(), datetime.min.time())
    today_end = datetime.combine(date.today(), datetime.max.time())
    todays_visits = MedicalVisit.query.filter(MedicalVisit.visit_date.between(today_start, today_end)).count()
    # 5. Pending Appointments
    pending_appointments = Appointment.query.filter_by(status='Scheduled').count()
    
    # Audit trail details
    recent_activities = AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(5).all()
    recent_logins = AuditLog.query.filter(AuditLog.action.in_(['Login Success', 'Login Failed'])).order_by(AuditLog.timestamp.desc()).limit(5).all()
    
    return render_template(
        'dashboard/sysadmin.html',
        total_patients=total_patients,
        total_users=total_users,
        total_doctors=total_doctors,
        todays_visits=todays_visits,
        pending_appointments=pending_appointments,
        recent_activities=recent_activities,
        recent_logins=recent_logins
    )

@admin_bp.route('/dashboard')
@login_required
@role_required('Administrator')
def admin_dashboard():
    total_patients = Patient.query.filter_by(is_active=True).count()
    
    doctor_role = Role.query.filter_by(name='Doctor').first()
    total_doctors = User.query.filter_by(role_id=doctor_role.id, is_active=True).count() if doctor_role else 0
    
    receptionist_role = Role.query.filter_by(name='Receptionist').first()
    total_receptionists = User.query.filter_by(role_id=receptionist_role.id, is_active=True).count() if receptionist_role else 0
    
    pending_appointments = Appointment.query.filter_by(status='Scheduled').order_by(Appointment.appointment_date.asc()).limit(5).all()
    
    return render_template(
        'dashboard/admin.html',
        total_patients=total_patients,
        total_doctors=total_doctors,
        total_receptionists=total_receptionists,
        pending_appointments=pending_appointments
    )

@admin_bp.route('/backup/download')
@login_required
@role_required('Hospital System Administrator')
def backup_download_view():
    db_uri = current_app.config.get('SQLALCHEMY_DATABASE_URI', '')
    if db_uri.startswith('sqlite:///'):
        db_path = db_uri.split('sqlite:///')[1]
        if os.path.exists(db_path):
            log_action("DB Backup Download", f"Hospital System Administrator downloaded database backup.")
            return send_file(
                db_path, 
                as_attachment=True, 
                download_name=f"ehr_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
            )
            
    flash("Database backup failed. SQLite DB file not found.", "danger")
    return redirect(url_for('admin.sysadmin_dashboard'))

# Placeholders for future phases to make sidebars fully responsive without 404s
@admin_bp.route('/users')
@login_required
@role_required('Hospital System Administrator')
def manage_users():
    return "User Management Placeholder - Phase 10"

@admin_bp.route('/audit-logs')
@login_required
@role_required('Hospital System Administrator')
def view_audit_logs():
    return "Audit Logs Viewer Placeholder - Phase 10"

@admin_bp.route('/doctors')
@login_required
@role_required('Administrator')
def manage_doctors():
    return "Doctors Management Placeholder - Phase 10"

@admin_bp.route('/receptionists')
@login_required
@role_required('Administrator')
def manage_receptionists():
    return "Receptionists Management Placeholder - Phase 10"

@admin_bp.route('/patients')
@login_required
@role_required(['Administrator', 'Hospital System Administrator'])
def manage_patients():
    return "Patients List Placeholder"

@admin_bp.route('/appointments')
@login_required
@role_required(['Administrator', 'Hospital System Administrator'])
def manage_appointments():
    return "Appointments Management Placeholder"
