from flask import Blueprint

receptionist_bp = Blueprint('receptionist', __name__, url_prefix='/receptionist')

@receptionist_bp.route('/')
def index():
    return "Receptionist Placeholder"
