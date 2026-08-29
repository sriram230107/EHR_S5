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

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


doctor_bp = Blueprint('doctor', __name__, url_prefix='/doctor')


# ================================================================
# DOCTOR DASHBOARD
# ================================================================

@doctor_bp.route('/dashboard')
@login_required
@role_required('Doctor')
def doctor_dashboard():

    appointments = Appointment.query.filter_by(
        doctor_id=current_user.id,
        status='Scheduled'
    ).order_by(
        Appointment.appointment_date.asc()
    ).all()

    pending_follow_ups = MedicalVisit.query.filter(
        MedicalVisit.doctor_id == current_user.id,
        MedicalVisit.follow_up_date >= date.today()
    ).order_by(
        MedicalVisit.follow_up_date.asc()
    ).all()

    return render_template(
        'dashboard/doctor.html',
        appointments=appointments,
        pending_follow_ups=pending_follow_ups
    )


# ================================================================
# DOCTOR PATIENT SEARCH
# ================================================================

@doctor_bp.route('/patients')
@login_required
@role_required('Doctor')
def search_patients():

    return redirect(
        url_for('main.search_patients')
    )


# ================================================================
# CREATE MEDICAL VISIT
# ================================================================

@doctor_bp.route('/visit/create/<int:patient_id>', methods=['GET', 'POST'])
@login_required
@role_required('Doctor')
def create_medical_visit(patient_id):

    patient = Patient.query.get_or_404(patient_id)

    if not patient.is_active:

        abort(
            403,
            description="Cannot record medical visits for inactive patient records."
        )


    # ============================================================
    # GET REQUEST
    # ============================================================

    if request.method == 'GET':

        return render_template(
            'visit/create.html',
            patient=patient
        )


    # ============================================================
    # BASIC CLINICAL DETAILS
    # ============================================================

    symptoms = request.form.get(
        'symptoms',
        ''
    ).strip()

    vitals_bp = request.form.get(
        'vitals_bp',
        ''
    ).strip()

    vitals_pulse_str = request.form.get(
        'vitals_pulse',
        ''
    ).strip()

    vitals_temp_str = request.form.get(
        'vitals_temp',
        ''
    ).strip()

    vitals_weight_str = request.form.get(
        'vitals_weight',
        ''
    ).strip()

    diagnosis_notes = request.form.get(
        'diagnosis_notes',
        ''
    ).strip()

    clinical_notes = request.form.get(
        'clinical_notes',
        ''
    ).strip()

    follow_up_date_str = request.form.get(
        'follow_up_date',
        ''
    ).strip()


    # ============================================================
    # ICD-10 DETAILS
    # ============================================================

    icd_code_id_str = request.form.get(
        'icd_code_id',
        ''
    ).strip()

    icd_confirmed = request.form.get(
        'icd_confirmed',
        '0'
    ).strip()


    # ============================================================
    # REQUIRED CLINICAL FIELD VALIDATION
    # ============================================================

    if (
        not symptoms
        or not vitals_bp
        or not vitals_pulse_str
        or not vitals_temp_str
        or not vitals_weight_str
        or not diagnosis_notes
    ):

        flash(
            "All fields marked with an asterisk (*) are required.",
            "danger"
        )

        return render_template(
            'visit/create.html',
            patient=patient
        )


    # ============================================================
    # ICD CODE REQUIRED
    # ============================================================

    if not icd_code_id_str:

        flash(
            "Please select an ICD-10 code before saving the consultation.",
            "danger"
        )

        return render_template(
            'visit/create.html',
            patient=patient
        )


    # ============================================================
    # ICD DOCTOR CONFIRMATION REQUIRED
    # ============================================================

    if icd_confirmed != '1':

        flash(
            "The selected ICD-10 code must be reviewed and confirmed by the doctor before saving.",
            "danger"
        )

        return render_template(
            'visit/create.html',
            patient=patient
        )


    # ============================================================
    # CONVERT ICD ID
    # ============================================================

    try:

        icd_code_id = int(
            icd_code_id_str
        )

    except ValueError:

        flash(
            "Invalid ICD-10 code selected.",
            "danger"
        )

        return render_template(
            'visit/create.html',
            patient=patient
        )


    # ============================================================
    # VERIFY ICD CODE EXISTS
    # ============================================================

    selected_icd = ICDCode.query.get(
        icd_code_id
    )

    if not selected_icd:

        flash(
            "The selected ICD-10 code could not be found.",
            "danger"
        )

        return render_template(
            'visit/create.html',
            patient=patient
        )


    # ============================================================
    # CONVERT VITALS
    # ============================================================

    try:

        vitals_pulse = int(
            vitals_pulse_str
        )

        vitals_temp = float(
            vitals_temp_str
        )

        vitals_weight = float(
            vitals_weight_str
        )

    except ValueError:

        flash(
            "Pulse, temperature, and weight must be numerical values.",
            "danger"
        )

        return render_template(
            'visit/create.html',
            patient=patient
        )


    # ============================================================
    # VITAL RANGE VALIDATION
    # ============================================================

    if not 30 <= vitals_pulse <= 250:

        flash(
            "Pulse rate must be between 30 and 250 BPM.",
            "danger"
        )

        return render_template(
            'visit/create.html',
            patient=patient
        )


    if not 90 <= vitals_temp <= 115:

        flash(
            "Temperature must be between 90°F and 115°F.",
            "danger"
        )

        return render_template(
            'visit/create.html',
            patient=patient
        )


    if not 1 <= vitals_weight <= 300:

        flash(
            "Weight must be between 1 and 300 KG.",
            "danger"
        )

        return render_template(
            'visit/create.html',
            patient=patient
        )


    # ============================================================
    # FOLLOW-UP DATE
    # ============================================================

    follow_up_date = None

    if follow_up_date_str:

        try:

            follow_up_date = datetime.strptime(
                follow_up_date_str,
                '%Y-%m-%d'
            ).date()

        except ValueError:

            flash(
                "Invalid follow-up date format.",
                "danger"
            )

            return render_template(
                'visit/create.html',
                patient=patient
            )


    # ============================================================
    # CREATE MEDICAL VISIT
    # ============================================================

    try:

        visit = MedicalVisit(

            patient_id=patient.id,

            doctor_id=current_user.id,

            symptoms=symptoms,

            vitals_bp=vitals_bp,

            vitals_pulse=vitals_pulse,

            vitals_temp=vitals_temp,

            vitals_weight=vitals_weight,

            icd_code_id=selected_icd.id,

            diagnosis_notes=diagnosis_notes,

            clinical_notes=clinical_notes or None,

            follow_up_date=follow_up_date
        )


        db.session.add(
            visit
        )

        db.session.flush()


        # ========================================================
        # PRESCRIPTIONS
        # ========================================================

        med_names = request.form.getlist(
            'medication_name[]'
        )

        dosages = request.form.getlist(
            'dosage[]'
        )

        frequencies = request.form.getlist(
            'frequency[]'
        )

        durations = request.form.getlist(
            'duration[]'
        )

        instructions = request.form.getlist(
            'instructions[]'
        )


        for idx in range(
            len(med_names)
        ):

            med_name = med_names[idx].strip()

            if not med_name:

                continue


            prescription = Prescription(

                visit_id=visit.id,

                medication_name=med_name,

                dosage=(
                    dosages[idx].strip()
                    if idx < len(dosages)
                    else ''
                ),

                frequency=(
                    frequencies[idx].strip()
                    if idx < len(frequencies)
                    else ''
                ),

                duration=(
                    durations[idx].strip()
                    if idx < len(durations)
                    else ''
                ),

                instructions=(
                    instructions[idx].strip()
                    if idx < len(instructions)
                    else ''
                )
            )


            db.session.add(
                prescription
            )


        # ========================================================
        # COMMIT
        # ========================================================

        db.session.commit()


        # ========================================================
        # AUDIT LOG
        # ========================================================

        log_action(

            action="Record Create",

            details=(
                f"Recorded new Medical Visit "
                f"(ID: {visit.id}) for patient "
                f"{patient.full_name} "
                f"({patient.patient_number}). "
                f"ICD-10: {selected_icd.code} "
                f"(Doctor confirmed)."
            )
        )


        flash(
            "Medical visit, confirmed ICD-10 code, and prescriptions saved successfully.",
            "success"
        )


        return redirect(
            url_for(
                'main.view_patient_profile',
                patient_id=patient.id
            )
        )


    except Exception as e:

        db.session.rollback()

        current_app.logger.exception(
            "Error while creating medical visit"
        )

        flash(
            "Unable to save the medical visit. Please try again.",
            "danger"
        )

        return render_template(
            'visit/create.html',
            patient=patient
        )


# ================================================================
# ICD-10 MANUAL SEARCH
# ================================================================

@doctor_bp.route('/icd/search')
@login_required
@role_required('Doctor')
def search_icd_codes():

    q = request.args.get(
        'q',
        ''
    ).strip()

    if not q:

        return jsonify([])


    results = ICDCode.query.filter(

        ICDCode.code.like(
            f"%{q}%"
        )

        |

        ICDCode.description.like(
            f"%{q}%"
        )

        |

        ICDCode.keywords.like(
            f"%{q}%"
        )

    ).limit(10).all()


    return jsonify([

        {
            'id': item.id,
            'code': item.code,
            'description': item.description
        }

        for item in results

    ])


# ================================================================
# AI / ML ICD-10 ASSIST
# ================================================================

@doctor_bp.route('/icd/assist')
@login_required
@role_required('Doctor')
def assist_icd_codes():

    """
    Return ML-ranked ICD-10 suggestions from
    the doctor's clinical text.

    This is an assistive ranking system.
    The doctor must review and explicitly
    select and confirm a suggested code
    before it is saved.
    """

    clinical_text = request.args.get(
        'text',
        ''
    ).strip()


    if len(clinical_text) < 3:

        return jsonify({
            'suggestions': [],
            'message': 'Enter at least a few clinical terms.'
        })


    codes = ICDCode.query.all()


    if not codes:

        return jsonify({
            'suggestions': []
        })


    documents = [

        f"{item.description} {item.keywords}"

        for item in codes

    ]


    vectorizer = TfidfVectorizer(
        stop_words='english',
        ngram_range=(1, 2)
    )


    matrix = vectorizer.fit_transform(
        documents
    )


    query_vector = vectorizer.transform(
        [clinical_text]
    )


    scores = cosine_similarity(
        query_vector,
        matrix
    ).flatten()


    ranked = sorted(
        zip(codes, scores),
        key=lambda pair: pair[1],
        reverse=True
    )[:5]


    suggestions = []


    for item, score in ranked:

        confidence = round(
            min(
                float(score) * 100,
                99.0
            ),
            1
        )


        if confidence <= 0:

            continue


        suggestions.append({

            'id': item.id,

            'code': item.code,

            'description': item.description,

            'match_score': confidence

        })


    return jsonify({
        'suggestions': suggestions
    })


# ================================================================
# UPLOAD PATIENT DOCUMENT
# ================================================================

@doctor_bp.route(
    '/patient/<int:patient_id>/upload',
    methods=['POST']
)
@login_required
@role_required('Doctor')
def upload_patient_document(patient_id):

    patient = Patient.query.get_or_404(
        patient_id
    )


    if not patient.is_active:

        abort(
            403,
            description="Cannot upload documents for inactive patient records."
        )


    if 'file' not in request.files:

        flash(
            "No file part in the upload request.",
            "danger"
        )

        return redirect(
            url_for(
                'main.view_patient_profile',
                patient_id=patient.id
            )
        )


    file = request.files['file']


    file_type = request.form.get(
        'file_type',
        ''
    ).strip()


    if file.filename == '':

        flash(
            "No file selected for upload.",
            "danger"
        )

        return redirect(
            url_for(
                'main.view_patient_profile',
                patient_id=patient.id
            )
        )


    valid_types = {
        'Prescription',
        'Lab Report',
        'Scan Report',
        'X-Ray',
        'Discharge Summary',
        'Other'
    }


    if file_type not in valid_types:

        flash(
            "Invalid document category selected.",
            "danger"
        )

        return redirect(
            url_for(
                'main.view_patient_profile',
                patient_id=patient.id
            )
        )


    # ============================================================
    # FILE EXTENSION
    # ============================================================

    filename = file.filename

    ext = (
        filename.rsplit('.', 1)[1].lower()
        if '.' in filename
        else ''
    )


    allowed_exts = current_app.config[
        'ALLOWED_EXTENSIONS'
    ]


    if ext not in allowed_exts:

        flash(
            "Invalid file extension. Only PDF, JPG, JPEG, and PNG are allowed.",
            "danger"
        )

        return redirect(
            url_for(
                'main.view_patient_profile',
                patient_id=patient.id
            )
        )


    # ============================================================
    # FILE SIZE
    # ============================================================

    file.seek(
        0,
        os.SEEK_END
    )

    size = file.tell()

    file.seek(0)


    max_size = current_app.config[
        'MAX_CONTENT_LENGTH'
    ]


    if size > max_size:

        flash(
            "File size exceeds the 10 MB limit.",
            "danger"
        )

        return redirect(
            url_for(
                'main.view_patient_profile',
                patient_id=patient.id
            )
        )


    # ============================================================
    # CREATE PATIENT DIRECTORY
    # ============================================================

    patient_dir = os.path.join(
        current_app.config['UPLOAD_FOLDER'],
        patient.patient_number
    )


    os.makedirs(
        patient_dir,
        exist_ok=True
    )


    # ============================================================
    # SAVE FILE
    # ============================================================

    from werkzeug.utils import secure_filename


    sec_name = secure_filename(
        filename
    )


    unique_name = (
        f"{int(time.time())}_{sec_name}"
    )


    save_path = os.path.join(
        patient_dir,
        unique_name
    )


    file.save(
        save_path
    )


    # ============================================================
    # SAVE DOCUMENT RECORD
    # ============================================================

    doc_record = Document(

        patient_id=patient.id,

        doctor_id=current_user.id,

        filename=unique_name,

        original_filename=filename,

        file_type=file_type,

        file_path=save_path
    )


    db.session.add(
        doc_record
    )

    db.session.commit()


    # ============================================================
    # AUDIT LOG
    # ============================================================

    log_action(

        action="Document Upload",

        details=(
            f"Uploaded {file_type} document "
            f"'{filename}' for patient "
            f"{patient.full_name} "
            f"({patient.patient_number})."
        )
    )


    flash(
        "Document uploaded successfully.",
        "success"
    )


    return redirect(
        url_for(
            'main.view_patient_profile',
            patient_id=patient.id
        )
    )