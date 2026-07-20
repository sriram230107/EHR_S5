from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from app.routes.decorators import role_required
from app.models.appointment import Appointment
from app.models.patient import Patient
from app import db
from datetime import datetime, date

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

@receptionist_bp.route('/appointments')
@login_required
@role_required('Receptionist')
def manage_appointments():
    return "Receptionist Appointments Booking Placeholder"
