from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, jsonify, current_app
from flask_login import login_required, current_user
from app.routes.decorators import role_required
from app.models.appointment import Appointment
from app.models.medical_visit import MedicalVisit, Prescription
from app.models.patient import Patient
from app.models.icd_code import ICDCode
from app.models.document import Document
from app.utils import log_action
from app import db
from datetime import date, datetime
import os
import time

doctor_bp = Blueprint('doctor', __name__, url_prefix='/doctor')

@doctor_bp.route('/dashboard')
@login_required
@role_required('Doctor')
def doctor_dashboard():
    # Today's/Pending scheduled appointments for this doctor
    appointments = Appointment.query.filter_by(
        doctor_id=current_user.id,
        status='Scheduled'
    ).order_by(Appointment.appointment_date.asc()).all()
    
    # Upcoming follow-up reminders recorded by this doctor
    pending_follow_ups = MedicalVisit.query.filter(
        MedicalVisit.doctor_id == current_user.id,
        MedicalVisit.follow_up_date >= date.today()
    ).order_by(MedicalVisit.follow_up_date.asc()).all()
    
    return render_template(
        'dashboard/doctor.html',
        appointments=appointments,
        pending_follow_ups=pending_follow_ups
    )

@doctor_bp.route('/patients')
@login_required
@role_required('Doctor')
def search_patients():
    return redirect(url_for('main.search_patients'))

@doctor_bp.route('/visit/create/<int:patient_id>', methods=['GET', 'POST'])
@login_required
@role_required('Doctor')
def create_medical_visit(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    if not patient.is_active:
        abort(403, description="Cannot record medical visits for inactive patient records.")
        
    if request.method == 'POST':
        symptoms = request.form.get('symptoms', '').strip()
        vitals_bp = request.form.get('vitals_bp', '').strip()
        vitals_pulse_str = request.form.get('vitals_pulse', '').strip()
        vitals_temp_str = request.form.get('vitals_temp', '').strip()
        vitals_weight_str = request.form.get('vitals_weight', '').strip()
        
        icd_code_id_str = request.form.get('icd_code_id', '').strip()
        diagnosis_notes = request.form.get('diagnosis_notes', '').strip()
        clinical_notes = request.form.get('clinical_notes', '').strip()
        follow_up_date_str = request.form.get('follow_up_date', '').strip()
        
        # Validation checks
        if not symptoms or not vitals_bp or not vitals_pulse_str or not vitals_temp_str or not vitals_weight_str or not diagnosis_notes:
            flash("All fields marked with an asterisk (*) are required.", "danger")
            return render_template('visit/create.html', patient=patient)
            
        try:
            vitals_pulse = int(vitals_pulse_str)
            vitals_temp = float(vitals_temp_str)
            vitals_weight = float(vitals_weight_str)
        except ValueError:
            flash("Pulse, temperature, and weight must be numerical values.", "danger")
            return render_template('visit/create.html', patient=patient)
            
        icd_code_id = int(icd_code_id_str) if icd_code_id_str else None
        
        follow_up_date = None
        if follow_up_date_str:
            try:
                follow_up_date = datetime.strptime(follow_up_date_str, '%Y-%m-%d').date()
            except ValueError:
                flash("Invalid follow-up date format.", "danger")
                return render_template('visit/create.html', patient=patient)
                
        # Initialize Visit Transaction
        visit = MedicalVisit(
            patient_id=patient.id,
            doctor_id=current_user.id,
            symptoms=symptoms,
            vitals_bp=vitals_bp,
            vitals_pulse=vitals_pulse,
            vitals_temp=vitals_temp,
            vitals_weight=vitals_weight,
            icd_code_id=icd_code_id,
            diagnosis_notes=diagnosis_notes,
            clinical_notes=clinical_notes or None,
            follow_up_date=follow_up_date
        )
        
        db.session.add(visit)
        db.session.flush()  # Extract visit.id for the prescriptions relationship
        
        # Retrieve tabular lists of medications
        med_names = request.form.getlist('medication_name[]')
        dosages = request.form.getlist('dosage[]')
        frequencies = request.form.getlist('frequency[]')
        durations = request.form.getlist('duration[]')
        instructions = request.form.getlist('instructions[]')
        
        for idx in range(len(med_names)):
            med_name = med_names[idx].strip()
            if med_name:  # Only save rows where a medication is specified
                pres = Prescription(
                    visit_id=visit.id,
                    medication_name=med_name,
                    dosage=dosages[idx].strip() if idx < len(dosages) else '',
                    frequency=frequencies[idx].strip() if idx < len(frequencies) else '',
                    duration=durations[idx].strip() if idx < len(durations) else '',
                    instructions=instructions[idx].strip() if idx < len(instructions) else ''
                )
                db.session.add(pres)
                
        # Auto-complete today's scheduled appointment for this patient and doctor
        today_start = datetime.combine(date.today(), datetime.min.time())
        today_end = datetime.combine(date.today(), datetime.max.time())
        appt = Appointment.query.filter(
            Appointment.patient_id == patient.id,
            Appointment.doctor_id == current_user.id,
            Appointment.status == 'Scheduled',
            Appointment.appointment_date.between(today_start, today_end)
        ).first()
        if appt:
            appt.status = 'Completed'

        db.session.commit()
        
        log_action(
            action="Record Create",
            details=f"Recorded new Medical Visit (ID: {visit.id}) for patient {patient.full_name} ({patient.patient_number})."
        )
        
        flash("Medical visit and prescriptions saved successfully.", "success")
        return redirect(url_for('main.view_patient_profile', patient_id=patient.id))
        
    return render_template('visit/create.html', patient=patient)

@doctor_bp.route('/icd/search')
@login_required
@role_required('Doctor')
def search_icd_codes():
    q = request.args.get('q', '').strip()
    if not q:
        return jsonify([])
        
    results = ICDCode.query.filter(
        ICDCode.code.like(f"%{q}%") |
        ICDCode.description.like(f"%{q}%") |
        ICDCode.keywords.like(f"%{q}%")
    ).limit(10).all()
    
    return jsonify([{
        'id': item.id,
        'code': item.code,
        'description': item.description
    } for item in results])

@doctor_bp.route('/patient/<int:patient_id>/upload', methods=['POST'])
@login_required
@role_required('Doctor')
def upload_patient_document(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    if not patient.is_active:
        abort(403, description="Cannot upload documents for inactive patient records.")
        
    if 'file' not in request.files:
        flash("No file part in the upload request.", "danger")
        return redirect(url_for('main.view_patient_profile', patient_id=patient.id))
        
    file = request.files['file']
    file_type = request.form.get('file_type', '').strip()
    
    if file.filename == '':
        flash("No file selected for upload.", "danger")
        return redirect(url_for('main.view_patient_profile', patient_id=patient.id))
        
    valid_types = {'Prescription', 'Lab Report', 'Scan Report', 'X-Ray', 'Discharge Summary', 'Other'}
    if file_type not in valid_types:
        flash("Invalid document category selected.", "danger")
        return redirect(url_for('main.view_patient_profile', patient_id=patient.id))
        
    # Validate extension
    filename = file.filename
    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    allowed_exts = current_app.config['ALLOWED_EXTENSIONS']
    if ext not in allowed_exts:
        flash("Invalid file extension. Only PDF, JPG, JPEG, and PNG are allowed.", "danger")
        return redirect(url_for('main.view_patient_profile', patient_id=patient.id))
        
    # Validate size (done in server-side file stream check)
    file.seek(0, os.SEEK_END)
    size = file.tell()
    file.seek(0)  # Reset pointer
    
    max_size = current_app.config['MAX_CONTENT_LENGTH']
    if size > max_size:
        flash("File size exceeds the 10 MB limit.", "danger")
        return redirect(url_for('main.view_patient_profile', patient_id=patient.id))
        
    # Build structured directory: uploads/patients/PAT-YYYY-XXXX/
    patient_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], patient.patient_number)
    os.makedirs(patient_dir, exist_ok=True)
    
    # Save file with unique secure timestamp prefix
    from werkzeug.utils import secure_filename
    sec_name = secure_filename(filename)
    unique_name = f"{int(time.time())}_{sec_name}"
    save_path = os.path.join(patient_dir, unique_name)
    file.save(save_path)
    
    # Save Document entry
    doc_record = Document(
        patient_id=patient.id,
        doctor_id=current_user.id,
        filename=unique_name,
        original_filename=filename,
        file_type=file_type,
        file_path=save_path
    )
    db.session.add(doc_record)
    db.session.commit()
    
    log_action(
        action="Document Upload",
        details=f"Uploaded {file_type} document '{filename}' for patient {patient.full_name} ({patient.patient_number})."
    )
    
    flash("Document uploaded successfully.", "success")
    return redirect(url_for('main.view_patient_profile', patient_id=patient.id))
