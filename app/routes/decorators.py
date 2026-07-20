from functools import wraps
from flask import abort
from flask_login import current_user

def role_required(allowed_roles):
    """
    Decorator to restrict access to routes based on user roles.
    Allowed roles should be a list or a single string of role names.
    Example: @role_required(['Doctor', 'Administrator'])
    """
    if isinstance(allowed_roles, str):
        allowed_roles = [allowed_roles]
        
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Check if user is logged in
            if not current_user or not current_user.is_authenticated:
                abort(401)
            
            # Check if user's role is in the allowed list
            if not current_user.role or current_user.role.name not in allowed_roles:
                abort(403)
                
            return f(*args, **kwargs)
        return decorated_function
    return decorator
