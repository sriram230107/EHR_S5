import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    # Secret key for session management
    SECRET_KEY = os.environ.get('SECRET_KEY', 'ehr-dev-secret-key-9f2b8c7d6e5f4a')
    
    # Database configuration (SQLite in instance folder)
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL', 
        f'sqlite:///{os.path.join(BASE_DIR, "instance", "ehr_portal.db")}'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Document Upload configurations
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads', 'patients')
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10 MB limit
    ALLOWED_EXTENSIONS = {'pdf', 'jpg', 'jpeg', 'png'}
