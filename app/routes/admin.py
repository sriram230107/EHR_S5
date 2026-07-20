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
from werkzeug.security import generate_password_hash
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
    daily_visits = db.session.query(
        db.func.strftime('%Y-%m-%d', MedicalVisit.visit_date).label('v_date'),
        db.func.count(MedicalVisit.id)
    ).group_by('v_date').order_by(db.desc('v_date')).limit(15).all()
    
    common_diagnoses = db.session.query(
        ICDCode.code,
        ICDCode.description,
        db.func.count(MedicalVisit.id).label('visit_cnt')
    ).join(MedicalVisit).group_by(ICDCode.id).order_by(db.desc('visit_cnt')).limit(10).all()
    
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

@admin_bp.route('/users')
@login_required
@role_required(['Administrator', 'Hospital System Administrator'])
def manage_users():
    role_filter = request.args.get('role', '').strip()
    role_name = current_user.role.name
    
    user_query = User.query
    
    # RBAC restriction: Administrators can only view Doctors and Receptionists
    if role_name == 'Administrator':
        doctor_role = Role.query.filter_by(name='Doctor').first()
        rec_role = Role.query.filter_by(name='Receptionist').first()
        allowed_role_ids = [r.id for r in [doctor_role, rec_role] if r]
        user_query = user_query.filter(User.role_id.in_(allowed_role_ids))
        
    if role_filter:
        target_role = Role.query.filter_by(name=role_filter).first()
        if target_role:
            user_query = user_query.filter_by(role_id=target_role.id)
            
    users = user_query.order_by(User.username.asc()).all()
    return render_template('admin/users.html', users=users, role_filter=role_filter)

@admin_bp.route('/users/create', methods=['GET', 'POST'])
@login_required
@role_required(['Administrator', 'Hospital System Administrator'])
def create_user():
    role_name = current_user.role.name
    roles = Role.query.all()
    departments = Department.query.order_by(Department.name.asc()).all()
    
    # Admins can only create Doctors or Receptionists
    if role_name == 'Administrator':
        roles = [r for r in roles if r.name in ['Doctor', 'Receptionist']]
        
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        role_id_str = request.form.get('role_id', '')
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        phone = request.form.get('phone', '').strip()
        
        # Doctor Specifics
        specialization = request.form.get('specialization', '').strip()
        license_number = request.form.get('license_number', '').strip()
        department_id_str = request.form.get('department_id', '')
        
        if not username or not email or not password or not role_id_str or not first_name or not last_name:
            flash("Please complete all required fields.", "danger")
            return render_template('admin/user_create.html', roles=roles, departments=departments)
            
        role_id = int(role_id_str)
        selected_role = Role.query.get(role_id)
        
        # Enforce RBAC constraints on selected roles
        if role_name == 'Administrator' and selected_role.name not in ['Doctor', 'Receptionist']:
            abort(403, description="Cannot assign higher privileges.")
            
        if User.query.filter_by(username=username).first():
            flash("Username already exists.", "danger")
            return render_template('admin/user_create.html', roles=roles, departments=departments)
            
        if User.query.filter_by(email=email).first():
            flash("Email address already exists.", "danger")
            return render_template('admin/user_create.html', roles=roles, departments=departments)
            
        password_hash = generate_password_hash(password)
        
        new_user = User(
            username=username,
            email=email,
            password_hash=password_hash,
            role_id=role_id,
            first_name=first_name,
            last_name=last_name,
            phone=phone or None,
            is_active=True
        )
        
        if selected_role.name == 'Doctor':
            if not license_number:
                flash("Medical license number is required for doctors.", "danger")
                return render_template('admin/user_create.html', roles=roles, departments=departments)
            if User.query.filter_by(license_number=license_number).first():
                flash("License number already registered.", "danger")
                return render_template('admin/user_create.html', roles=roles, departments=departments)
                
            new_user.specialization = specialization or None
            new_user.license_number = license_number
            new_user.department_id = int(department_id_str) if department_id_str else None
            
        db.session.add(new_user)
        db.session.commit()
        
        log_action("User Create", f"Created staff user account '{username}' with role '{selected_role.name}'.")
        flash(f"Staff account '{username}' successfully created.", "success")
        return redirect(url_for('admin.manage_users'))
        
    return render_template('admin/user_create.html', roles=roles, departments=departments)

@admin_bp.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required(['Administrator', 'Hospital System Administrator'])
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    role_name = current_user.role.name
    
    # Enforce RBAC edit boundaries
    if role_name == 'Administrator' and user.role.name not in ['Doctor', 'Receptionist']:
        abort(403, description="Cannot modify this user profile.")
        
    roles = Role.query.all()
    departments = Department.query.order_by(Department.name.asc()).all()
    
    if role_name == 'Administrator':
        roles = [r for r in roles if r.name in ['Doctor', 'Receptionist']]
        
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        phone = request.form.get('phone', '').strip()
        role_id_str = request.form.get('role_id', '')
        is_active = request.form.get('is_active') == '1'
        
        # Doctor Specifics
        specialization = request.form.get('specialization', '').strip()
        license_number = request.form.get('license_number', '').strip()
        department_id_str = request.form.get('department_id', '')
        
        if not email or not first_name or not last_name or not role_id_str:
            flash("Required fields cannot be empty.", "danger")
            return render_template('admin/user_edit.html', user=user, roles=roles, departments=departments)
            
        existing_email_user = User.query.filter_by(email=email).first()
        if existing_email_user and existing_email_user.id != user.id:
            flash("Email address is already in use.", "danger")
            return render_template('admin/user_edit.html', user=user, roles=roles, departments=departments)
            
        role_id = int(role_id_str)
        selected_role = Role.query.get(role_id)
        
        # Prevent admins from upgrading edit target to system levels
        if role_name == 'Administrator' and selected_role.name not in ['Doctor', 'Receptionist']:
            abort(403, description="Invalid role assignment.")
            
        # Update basics
        user.email = email
        user.first_name = first_name
        user.last_name = last_name
        user.phone = phone or None
        user.role_id = role_id
        
        # Only allow deactivation if they are not deactivating themselves!
        if user.id != current_user.id:
            user.is_active = is_active
            
        if selected_role.name == 'Doctor':
            if not license_number:
                flash("Medical license number is required for Doctors.", "danger")
                return render_template('admin/user_edit.html', user=user, roles=roles, departments=departments)
                
            existing_lic = User.query.filter_by(license_number=license_number).first()
            if existing_lic and existing_lic.id != user.id:
                flash("License number already registered.", "danger")
                return render_template('admin/user_edit.html', user=user, roles=roles, departments=departments)
                
            user.specialization = specialization or None
            user.license_number = license_number
            user.department_id = int(department_id_str) if department_id_str else None
        else:
            # Clear doctor fields if role changed
            user.specialization = None
            user.license_number = None
            user.department_id = None
            
        db.session.commit()
        
        log_action("User Update", f"Updated details for user account '{user.username}' (Active: {user.is_active}).")
        flash(f"Staff account '{user.username}' successfully updated.", "success")
        return redirect(url_for('admin.manage_users'))
        
    return render_template('admin/user_edit.html', user=user, roles=roles, departments=departments)

@admin_bp.route('/users/<int:user_id>/reset-password', methods=['POST'])
@login_required
@role_required(['Administrator', 'Hospital System Administrator'])
def reset_password(user_id):
    user = User.query.get_or_404(user_id)
    role_name = current_user.role.name
    
    if role_name == 'Administrator' and user.role.name not in ['Doctor', 'Receptionist']:
        abort(403, description="Cannot reset password for this user.")
        
    new_password = request.form.get('new_password', '')
    if not new_password or len(new_password) < 6:
        flash("Password must be at least 6 characters long.", "danger")
        return redirect(url_for('admin.manage_users'))
        
    user.password_hash = generate_password_hash(new_password)
    db.session.commit()
    
    log_action("Password Reset", f"Reset password hash for user '{user.username}'.")
    flash(f"Password for user '{user.username}' successfully reset.", "success")
    return redirect(url_for('admin.manage_users'))

@admin_bp.route('/audit-logs')
@login_required
@role_required('Hospital System Administrator')
def view_audit_logs():
    q = request.args.get('q', '').strip()
    page = request.args.get('page', 1, type=int)
    
    logs_query = AuditLog.query
    if q:
        logs_query = logs_query.outerjoin(User).filter(
            AuditLog.action.like(f"%{q}%") |
            AuditLog.details.like(f"%{q}%") |
            AuditLog.ip_address.like(f"%{q}%") |
            AuditLog.username_attempted.like(f"%{q}%") |
            User.username.like(f"%{q}%")
        )
        
    pagination = logs_query.order_by(AuditLog.timestamp.desc()).paginate(page=page, per_page=15, error_out=False)
    logs = pagination.items
    
    return render_template('admin/audit_logs.html', logs=logs, pagination=pagination, q=q)

@admin_bp.route('/doctors')
@login_required
@role_required('Administrator')
def manage_doctors():
    return redirect(url_for('admin.manage_users') + '?role=Doctor')

@admin_bp.route('/receptionists')
@login_required
@role_required('Administrator')
def manage_receptionists():
    return redirect(url_for('admin.manage_users') + '?role=Receptionist')

@admin_bp.route('/patients')
@login_required
@role_required(['Administrator', 'Hospital System Administrator'])
def manage_patients():
    return redirect(url_for('main.search_patients'))

@admin_bp.route('/appointments')
@login_required
@role_required(['Administrator', 'Hospital System Administrator'])
def manage_appointments():
    return redirect(url_for('main.manage_appointments'))
