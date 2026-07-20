from flask import Blueprint

doctor_bp = Blueprint('doctor', __name__, url_prefix='/doctor')

@doctor_bp.route('/')
def index():
    return "Doctor Placeholder"
