from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from app.routes.decorators import role_required
from app.models.appointment import Appointment
from app.models.patient import Patient
from app import db
from datetime import datetime, date
from flask import request
from app.models.user import User
from app.models.role import Role

receptionist_bp = Blueprint('receptionist', __name__, url_prefix='/receptionist')

@receptionist_bp.route('/dashboard')
@login_required
@role_required('Receptionist')
def receptionist_dashboard():
    # 1. Stats
    total_patients = Patient.query.filter_by(is_active=True).count()
    
    # 2. Today's appointments (for all doctors)
    today_start = datetime.combine(date.today(), datetime.min.time())
    today_end = datetime.combine(date.today(), datetime.max.time())
    today_appointments = Appointment.query.filter(
        Appointment.appointment_date.between(today_start, today_end)
    ).order_by(Appointment.appointment_date.asc()).all()
    
    return render_template(
        'dashboard/receptionist.html',
        total_patients=total_patients,
        today_appointments=today_appointments
    )

# Placeholders for future phases
@receptionist_bp.route('/patients/register')
@login_required
@role_required('Receptionist')
def register_patient():
    return redirect(url_for('main.register_patient'))

@receptionist_bp.route('/appointments', methods=['GET', 'POST'])
@login_required
@role_required('Receptionist')
def manage_appointments():

    # -----------------------------
    # Handle Appointment Booking
    # -----------------------------
    if request.method == 'POST':
        try:
            patient_id = request.form.get('patient_id')
            doctor_id = request.form.get('doctor_id')
            appointment_date = request.form.get('appointment_date')
            reason = request.form.get('reason')

            if not patient_id or not doctor_id or not appointment_date:
                flash('Please fill all required fields.', 'danger')
                return redirect(url_for('receptionist.manage_appointments'))

            appointment = Appointment(
                patient_id=int(patient_id),
                doctor_id=int(doctor_id),
                appointment_date=datetime.strptime(
                    appointment_date,
                    '%Y-%m-%dT%H:%M'
                ),
                reason=reason,
                status='Scheduled'
            )

            db.session.add(appointment)
            db.session.commit()

            flash('Appointment booked successfully.', 'success')

        except Exception as e:
            db.session.rollback()
            flash(f'Error booking appointment: {str(e)}', 'danger')

        return redirect(url_for('receptionist.manage_appointments'))

    # -----------------------------
    # Search
    # -----------------------------
    q = request.args.get('q', '').strip()

    appointments_query = Appointment.query.order_by(
        Appointment.appointment_date.desc()
    )

    if q:
        appointments_query = appointments_query.join(Patient).filter(
            (Patient.first_name.ilike(f"%{q}%")) |
            (Patient.last_name.ilike(f"%{q}%")) |
            (Patient.patient_number.ilike(f"%{q}%"))
        )

    appointments = appointments_query.all()

    patients = Patient.query.filter_by(is_active=True).order_by(
        Patient.first_name
    ).all()

    doctors = User.query.filter(
        User.is_active == True,
        User.specialization.isnot(None)
    ).order_by(User.first_name).all()

    return render_template(
        'appointments/list.html',
        appointments=appointments,
        patients=patients,
        doctors=doctors,
        q=q,
        pagination=None
    )
