from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, send_file
from flask_login import login_required, current_user
from app.routes.decorators import role_required
from app import db
from app.models.patient import Patient
from app.models.appointment import Appointment
from app.models.user import User
from app.models.role import Role
from app.models.document import Document
from app.models.medical_visit import MedicalVisit
from app.utils import log_action
from datetime import datetime, date
import os

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
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

@main_bp.route('/patients')
@login_required
def search_patients():
    query_str = request.args.get('query', '').strip()
    show_inactive = request.args.get('show_inactive', '0') == '1'
    page = request.args.get('page', 1, type=int)
    sort_by = request.args.get('sort_by', 'patient_number')
    sort_order = request.args.get('sort_order', 'asc')
    
    role_name = current_user.role.name if current_user.role else ''
    can_see_inactive = role_name in ['Administrator', 'Hospital System Administrator']
    show_deleted = show_inactive and can_see_inactive
    
    patient_query = Patient.query
    if not show_deleted:
        patient_query = patient_query.filter_by(is_active=True)
        
    if query_str:
        search_filter = (
            Patient.first_name.like(f"%{query_str}%") |
            Patient.last_name.like(f"%{query_str}%") |
            Patient.patient_number.like(f"%{query_str}%") |
            Patient.phone.like(f"%{query_str}%") |
            Patient.email.like(f"%{query_str}%")
        )
        try:
            dob_parsed = datetime.strptime(query_str, '%Y-%m-%d').date()
            search_filter = search_filter | (Patient.dob == dob_parsed)
        except ValueError:
            pass
        patient_query = patient_query.filter(search_filter)
        
    if sort_by == 'first_name':
        order_col = Patient.first_name
    elif sort_by == 'dob':
        order_col = Patient.dob
    else:
        order_col = Patient.patient_number
        
    if sort_order == 'desc':
        patient_query = patient_query.order_by(order_col.desc())
    else:
        patient_query = patient_query.order_by(order_col.asc())
        
    pagination = patient_query.paginate(page=page, per_page=10, error_out=False)
    patients = pagination.items
    
    return render_template(
        'patient/search.html',
        patients=patients,
        pagination=pagination,
        query=query_str,
        show_inactive=show_deleted,
        can_see_inactive=can_see_inactive,
        sort_by=sort_by,
        sort_order=sort_order
    )

@main_bp.route('/patients/register', methods=['GET', 'POST'])
@login_required
@role_required(['Receptionist', 'Administrator', 'Hospital System Administrator'])
def register_patient():
    if request.method == 'POST':
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        dob_str = request.form.get('dob', '')
        gender = request.form.get('gender', '')
        phone = request.form.get('phone', '').strip()
        email = request.form.get('email', '').strip()
        address = request.form.get('address', '').strip()
        emergency_contact_name = request.form.get('emergency_name', '').strip()
        emergency_contact_phone = request.form.get('emergency_phone', '').strip()
        
        if not first_name or not last_name or not dob_str or not gender or not phone or not emergency_contact_name or not emergency_contact_phone:
            flash("All fields marked with an asterisk (*) are required.", "danger")
            return render_template('patient/register.html')
            
        try:
            dob = datetime.strptime(dob_str, '%Y-%m-%d').date()
        except ValueError:
            flash("Invalid date of birth format.", "danger")
            return render_template('patient/register.html')
            
        current_year = datetime.now().year
        prefix = f"PAT-{current_year}-"
        same_year_patients = Patient.query.filter(Patient.patient_number.like(f"{prefix}%")).all()
        
        if same_year_patients:
            counters = []
            for p in same_year_patients:
                try:
                    counter = int(p.patient_number.split('-')[-1])
                    counters.append(counter)
                except ValueError:
                    pass
            next_counter = max(counters) + 1 if counters else 1
        else:
            next_counter = 1
            
        patient_number = f"PAT-{current_year}-{str(next_counter).zfill(4)}"
        
        new_patient = Patient(
            patient_number=patient_number,
            first_name=first_name,
            last_name=last_name,
            dob=dob,
            gender=gender,
            phone=phone,
            email=email or None,
            address=address or None,
            emergency_contact_name=emergency_contact_name,
            emergency_contact_phone=emergency_contact_phone,
            is_active=True
        )
        
        db.session.add(new_patient)
        db.session.commit()
        
        log_action(
            action="Record Create",
            details=f"Registered patient {new_patient.full_name} with MRN: {patient_number}."
        )
        
        flash(f"Patient {new_patient.full_name} successfully registered. MRN: {patient_number}", "success")
        return redirect(url_for('main.view_patient_profile', patient_id=new_patient.id))
        
    return render_template('patient/register.html')

@main_bp.route('/patients/<int:patient_id>')
@login_required
def view_patient_profile(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    role_name = current_user.role.name if current_user.role else ''
    
    if not patient.is_active and role_name not in ['Administrator', 'Hospital System Administrator']:
        abort(403, description="This patient record is currently inactive.")
        
    appointments = Appointment.query.filter_by(patient_id=patient.id).order_by(Appointment.appointment_date.desc()).all()
    has_clinical_access = role_name in ['Doctor', 'Administrator', 'Hospital System Administrator']
    
    if has_clinical_access:
        visits = MedicalVisit.query.filter_by(patient_id=patient.id).order_by(MedicalVisit.visit_date.desc()).all()
        documents = Document.query.filter_by(patient_id=patient.id).order_by(Document.uploaded_at.desc()).all()
        return render_template(
            'patient/profile.html',
            patient=patient,
            appointments=appointments,
            visits=visits,
            documents=documents,
            has_clinical_access=True,
            date=date
        )
    else:
        return render_template(
            'patient/profile.html',
            patient=patient,
            appointments=appointments,
            visits=[],
            documents=[],
            has_clinical_access=False,
            date=date
        )

@main_bp.route('/patients/<int:patient_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required(['Receptionist', 'Administrator', 'Hospital System Administrator'])
def edit_patient(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    if not patient.is_active:
        abort(403, description="Cannot edit an inactive patient record.")
        
    if request.method == 'POST':
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        dob_str = request.form.get('dob', '')
        gender = request.form.get('gender', '')
        phone = request.form.get('phone', '').strip()
        email = request.form.get('email', '').strip()
        address = request.form.get('address', '').strip()
        emergency_contact_name = request.form.get('emergency_name', '').strip()
        emergency_contact_phone = request.form.get('emergency_phone', '').strip()
        
        if not first_name or not last_name or not dob_str or not gender or not phone or not emergency_contact_name or not emergency_contact_phone:
            flash("All fields marked with an asterisk (*) are required.", "danger")
            return render_template('patient/edit.html', patient=patient)
            
        try:
            dob = datetime.strptime(dob_str, '%Y-%m-%d').date()
        except ValueError:
            flash("Invalid date of birth format.", "danger")
            return render_template('patient/edit.html', patient=patient)
            
        patient.first_name = first_name
        patient.last_name = last_name
        patient.dob = dob
        patient.gender = gender
        patient.phone = phone
        patient.email = email or None
        patient.address = address or None
        patient.emergency_contact_name = emergency_contact_name
        patient.emergency_contact_phone = emergency_contact_phone
        
        db.session.commit()
        
        log_action(
            action="Record Update",
            details=f"Updated demographics details for patient {patient.full_name} ({patient.patient_number})."
        )
        
        flash("Patient demographic details updated successfully.", "success")
        return redirect(url_for('main.view_patient_profile', patient_id=patient.id))
        
    return render_template('patient/edit.html', patient=patient)

@main_bp.route('/patients/<int:patient_id>/toggle-active', methods=['POST'])
@login_required
@role_required(['Administrator', 'Hospital System Administrator'])
def toggle_patient_active(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    new_status = not patient.is_active
    patient.is_active = new_status
    db.session.commit()
    
    status_text = "activated" if new_status else "deactivated (soft delete)"
    log_action(
        action="Record Update",
        details=f"Patient {patient.full_name} ({patient.patient_number}) was {status_text}."
    )
    
    flash(f"Patient {patient.full_name} has been successfully {status_text}.", "success")
    return redirect(url_for('main.view_patient_profile', patient_id=patient.id))

@main_bp.route('/patients/documents/download/<int:doc_id>')
@login_required
def download_document(doc_id):
    role_name = current_user.role.name if current_user.role else ''
    if role_name not in ['Doctor', 'Administrator', 'Hospital System Administrator']:
        abort(403, description="Unauthorized document access.")
        
    doc = Document.query.get_or_404(doc_id)
    if os.path.exists(doc.file_path):
        log_action("Document Download", f"Downloaded file '{doc.original_filename}' for patient {doc.patient.patient_number}.")
        return send_file(doc.file_path, as_attachment=True, download_name=doc.original_filename)
        
    abort(404, description="File not found on server.")

@main_bp.route('/appointments', methods=['GET', 'POST'])
@login_required
@role_required(['Receptionist', 'Administrator', 'Hospital System Administrator'])
def manage_appointments():
    if request.method == 'POST':
        patient_id_str = request.form.get('patient_id', '')
        doctor_id_str = request.form.get('doctor_id', '')
        appt_date_str = request.form.get('appointment_date', '')
        reason = request.form.get('reason', '').strip()
        return_to_profile = request.form.get('return_to_profile') == '1'
        
        if not patient_id_str or not doctor_id_str or not appt_date_str:
            flash("All fields are required to schedule an appointment.", "danger")
            return redirect(url_for('main.manage_appointments'))
            
        appt_date = None
        # Try parsing without seconds first
        try:
            appt_date = datetime.strptime(appt_date_str, '%Y-%m-%dT%H:%M')
        except ValueError:
            # Try parsing with seconds
            try:
                appt_date = datetime.strptime(appt_date_str, '%Y-%m-%dT%H:%M:%S')
            except ValueError:
                pass
                
        if not appt_date:
            flash("Invalid date and time format. Please choose a valid consultation time.", "danger")
            return redirect(url_for('main.manage_appointments'))
            
        patient_id = int(patient_id_str)
        doctor_id = int(doctor_id_str)
        
        # Verify doctor is active
        doctor = User.query.get(doctor_id)
        if not doctor or not doctor.is_active or doctor.role.name != 'Doctor':
            flash("Invalid doctor selected.", "danger")
            return redirect(url_for('main.manage_appointments'))
            
        # Verify patient is active
        patient = Patient.query.get(patient_id)
        if not patient or not patient.is_active:
            flash("Invalid patient selected.", "danger")
            return redirect(url_for('main.manage_appointments'))
            
        appt = Appointment(
            patient_id=patient_id,
            doctor_id=doctor_id,
            appointment_date=appt_date,
            status='Scheduled',
            reason=reason
        )
        db.session.add(appt)
        db.session.commit()
        
        log_action(
            action="Appointment Create",
            details=f"Scheduled appointment for patient {patient.full_name} ({patient.patient_number}) with {doctor.full_name} on {appt_date.strftime('%Y-%m-%d %H:%M')}."
        )
        flash("Appointment scheduled successfully.", "success")
        
        if return_to_profile:
            return redirect(url_for('main.view_patient_profile', patient_id=patient_id))
        return redirect(url_for('main.manage_appointments'))
        
    page = request.args.get('page', 1, type=int)
    q = request.args.get('q', '').strip()
    selected_patient_id = request.args.get('patient_id', type=int)
    
    appt_query = Appointment.query
    if q:
        appt_query = appt_query.join(Patient).filter(
            Patient.first_name.like(f"%{q}%") | 
            Patient.last_name.like(f"%{q}%") | 
            Patient.patient_number.like(f"%{q}%")
        )
        
    pagination = appt_query.order_by(Appointment.appointment_date.desc()).paginate(page=page, per_page=10, error_out=False)
    appointments = pagination.items
    
    # Load patient and doctor dropdown lists
    patients = Patient.query.filter_by(is_active=True).order_by(Patient.first_name.asc()).all()
    doctor_role = Role.query.filter_by(name='Doctor').first()
    doctors = User.query.filter_by(role_id=doctor_role.id, is_active=True).order_by(User.first_name.asc()).all() if doctor_role else []
    
    return render_template(
        'appointments/list.html',
        appointments=appointments,
        pagination=pagination,
        patients=patients,
        doctors=doctors,
        q=q,
        selected_patient_id=selected_patient_id
    )

@main_bp.route('/appointments/<int:appt_id>/status', methods=['POST'])
@login_required
@role_required(['Receptionist', 'Administrator', 'Hospital System Administrator'])
def update_appointment_status(appt_id):
    appt = Appointment.query.get_or_404(appt_id)
    status = request.form.get('status', '').strip()
    
    if status in ['Scheduled', 'Completed', 'Cancelled', 'No-Show']:
        old_status = appt.status
        appt.status = status
        db.session.commit()
        
        log_action(
            action="Appointment Update",
            details=f"Updated appointment ID {appt.id} status for patient {appt.patient.full_name} from '{old_status}' to '{status}'."
        )
        flash(f"Appointment status updated to '{status}'.", "success")
    else:
        flash("Invalid status code.", "danger")
        
    return redirect(request.referrer or url_for('main.manage_appointments'))
