from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from app.routes.decorators import role_required
from app.models.appointment import Appointment
from app.models.medical_visit import MedicalVisit
from app import db
from datetime import date

doctor_bp = Blueprint('doctor', __name__, url_prefix='/doctor')

@doctor_bp.route('/dashboard')
@login_required
@role_required('Doctor')
def doctor_dashboard():
    # 1. Today's/Pending scheduled appointments for this doctor
    appointments = Appointment.query.filter_by(
        doctor_id=current_user.id,
        status='Scheduled'
    ).order_by(Appointment.appointment_date.asc()).all()
    
    # 2. Upcoming follow-up reminders recorded by this doctor
    # Shows medical visits where the follow-up date is today or in the future
    pending_follow_ups = MedicalVisit.query.filter(
        MedicalVisit.doctor_id == current_user.id,
        MedicalVisit.follow_up_date >= date.today()
    ).order_by(MedicalVisit.follow_up_date.asc()).all()
    
    return render_template(
        'dashboard/doctor.html',
        appointments=appointments,
        pending_follow_ups=pending_follow_ups
    )

# Placeholders for future phases
@doctor_bp.route('/patients')
@login_required
@role_required('Doctor')
def search_patients():
    return redirect(url_for('main.search_patients'))
