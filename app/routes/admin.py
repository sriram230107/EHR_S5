from flask import Blueprint, render_template, redirect, url_for, flash, abort, send_file, current_app, make_response, request
from flask_login import login_required, current_user
from app.routes.decorators import role_required
from app.models.user import User
from app.models.role import Role
from app.models.patient import Patient
from app.models.appointment import Appointment
from app.models.medical_visit import MedicalVisit
from app.models.icd_code import ICDCode
from app.models.department import Department
from app.models.audit_log import AuditLog
from app.utils import log_action
from app import db
from datetime import datetime, date, timedelta
import os
import csv
from io import StringIO

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/sysadmin/dashboard')
@login_required
@role_required('Hospital System Administrator')
def sysadmin_dashboard():
    total_patients = Patient.query.filter_by(is_active=True).count()
    total_users = User.query.filter_by(is_active=True).count()
    doctor_role = Role.query.filter_by(name='Doctor').first()
    total_doctors = User.query.filter_by(role_id=doctor_role.id, is_active=True).count() if doctor_role else 0
    today_start = datetime.combine(date.today(), datetime.min.time())
    today_end = datetime.combine(date.today(), datetime.max.time())
    todays_visits = MedicalVisit.query.filter(MedicalVisit.visit_date.between(today_start, today_end)).count()
    pending_appointments = Appointment.query.filter_by(status='Scheduled').count()
    
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

@admin_bp.route('/reports')
@login_required
@role_required(['Administrator', 'Hospital System Administrator'])
def view_reports():
    # 1. Daily Visits Report (last 15 days)
    daily_visits = db.session.query(
        db.func.strftime('%Y-%m-%d', MedicalVisit.visit_date).label('v_date'),
        db.func.count(MedicalVisit.id)
    ).group_by('v_date').order_by(db.desc('v_date')).limit(15).all()
    
    # 2. Most Common Diagnoses Report
    common_diagnoses = db.session.query(
        ICDCode.code,
        ICDCode.description,
        db.func.count(MedicalVisit.id).label('visit_cnt')
    ).join(MedicalVisit).group_by(ICDCode.id).order_by(db.desc('visit_cnt')).limit(10).all()
    
    # 3. Doctor Workload Report
    doctor_workload = db.session.query(
        User.first_name,
        User.last_name,
        Department.name.label('dept_name'),
        db.func.count(MedicalVisit.id).label('v_cnt')
    ).join(Role, User.role_id == Role.id)\
     .outerjoin(Department, User.department_id == Department.id)\
     .join(MedicalVisit, MedicalVisit.doctor_id == User.id)\
     .filter(Role.name == 'Doctor', User.is_active == True)\
     .group_by(User.id).order_by(db.desc('v_cnt')).all()
     
    return render_template(
        'reports/dashboard.html',
        daily_visits=daily_visits,
        common_diagnoses=common_diagnoses,
        doctor_workload=doctor_workload
    )

@admin_bp.route('/reports/export/csv/<report_type>')
@login_required
@role_required(['Administrator', 'Hospital System Administrator'])
def export_report_csv(report_type):
    si = StringIO()
    cw = csv.writer(si)
    filename = f"report_{report_type}_{datetime.now().strftime('%Y%m%d')}.csv"
    
    if report_type == 'daily_visits':
        cw.writerow(['Date', 'Visit Count'])
        results = db.session.query(
            db.func.strftime('%Y-%m-%d', MedicalVisit.visit_date).label('v_date'),
            db.func.count(MedicalVisit.id)
        ).group_by('v_date').order_by(db.desc('v_date')).limit(30).all()
        for r in results:
            cw.writerow([r[0], r[1]])
            
    elif report_type == 'diagnoses':
        cw.writerow(['ICD-10 Code', 'Description', 'Diagnosis Count'])
        results = db.session.query(
            ICDCode.code,
            ICDCode.description,
            db.func.count(MedicalVisit.id).label('visit_cnt')
        ).join(MedicalVisit).group_by(ICDCode.id).order_by(db.desc('visit_cnt')).all()
        for r in results:
            cw.writerow([r[0], r[1], r[2]])
            
    elif report_type == 'doctor_workload':
        cw.writerow(['Doctor Name', 'Department', 'Visits Count'])
        results = db.session.query(
            User.first_name,
            User.last_name,
            Department.name,
            db.func.count(MedicalVisit.id).label('v_cnt')
        ).join(Role, User.role_id == Role.id)\
         .outerjoin(Department, User.department_id == Department.id)\
         .join(MedicalVisit, MedicalVisit.doctor_id == User.id)\
         .filter(Role.name == 'Doctor')\
         .group_by(User.id).order_by(db.desc('v_cnt')).all()
        for r in results:
            cw.writerow([f"Dr. {r[0]} {r[1]}", r[2] or 'N/A', r[3]])
    else:
        abort(400, description="Invalid report type.")
        
    log_action("Report Export", f"Exported {report_type} report to CSV.")
    
    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = f"attachment; filename={filename}"
    output.headers["Content-type"] = "text/csv"
    return output

@admin_bp.route('/reports/print/<report_type>')
@login_required
@role_required(['Administrator', 'Hospital System Administrator'])
def print_report(report_type):
    report_title = ""
    headers = []
    rows = []
    
    if report_type == 'daily_visits':
        report_title = "Daily Consultations Frequency Report"
        headers = ["Date", "Visit Count"]
        results = db.session.query(
            db.func.strftime('%Y-%m-%d', MedicalVisit.visit_date).label('v_date'),
            db.func.count(MedicalVisit.id)
        ).group_by('v_date').order_by(db.desc('v_date')).limit(30).all()
        rows = [[r[0], f"{r[1]} visits"] for r in results]
        
    elif report_type == 'diagnoses':
        report_title = "Top ICD-10 Diagnosis Code Distributions"
        headers = ["ICD-10 Code", "Description", "Occurrences"]
        results = db.session.query(
            ICDCode.code,
            ICDCode.description,
            db.func.count(MedicalVisit.id).label('visit_cnt')
        ).join(MedicalVisit).group_by(ICDCode.id).order_by(db.desc('visit_cnt')).all()
        rows = [[r[0], r[1], f"{r[2]} patients"] for r in results]
        
    elif report_type == 'doctor_workload':
        report_title = "Doctor Workload & Department Statistics"
        headers = ["Doctor Name", "Department Name", "Encounters Recorded"]
        results = db.session.query(
            User.first_name,
            User.last_name,
            Department.name,
            db.func.count(MedicalVisit.id).label('v_cnt')
        ).join(Role, User.role_id == Role.id)\
         .outerjoin(Department, User.department_id == Department.id)\
         .join(MedicalVisit, MedicalVisit.doctor_id == User.id)\
         .filter(Role.name == 'Doctor')\
         .group_by(User.id).order_by(db.desc('v_cnt')).all()
        rows = [[f"Dr. {r[0]} {r[1]}", r[2] or 'N/A', f"{r[3]} visits"] for r in results]
    else:
        abort(400, description="Invalid report type.")
        
    return render_template(
        'reports/print.html',
        report_title=report_title,
        headers=headers,
        rows=rows,
        timestamp=datetime.now().strftime('%B %d, %Y - %I:%M %p')
    )

# Placeholders for future phases
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
    return redirect(url_for('main.search_patients'))

@admin_bp.route('/appointments')
@login_required
@role_required(['Administrator', 'Hospital System Administrator'])
def manage_appointments():
    return "Appointments Management Placeholder"
