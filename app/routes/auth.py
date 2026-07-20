from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash
from app.models.user import User
from app.utils import log_action

auth_bp = Blueprint('auth', __name__)

def redirect_dashboard(user):
    """Helper function to redirect users to their role-specific dashboards."""
    role_name = user.role.name if user.role else ''
    
    if role_name == 'Hospital System Administrator':
        return redirect(url_for('admin.sysadmin_dashboard'))
    elif role_name == 'Administrator':
        return redirect(url_for('admin.admin_dashboard'))
    elif role_name == 'Doctor':
        return redirect(url_for('doctor.doctor_dashboard'))
    elif role_name == 'Receptionist':
        return redirect(url_for('receptionist.receptionist_dashboard'))
        
    return redirect(url_for('main.index'))

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    # If already logged in, send directly to dashboard
    if current_user.is_authenticated:
        return redirect_dashboard(current_user)
        
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, password):
            # Check if user is active (soft delete flag)
            if not user.is_active:
                log_action(
                    action="Login Failed",
                    details=f"Deactivated account login attempt: '{username}'",
                    user_id=user.id
                )
                flash("Your account has been deactivated. Please contact the administrator.", "danger")
                return render_template('auth/login.html')
                
            # Log successful login
            login_user(user)
            log_action(
                action="Login Success", 
                details=f"User '{username}' logged in successfully.",
                user_id=user.id
            )
            
            flash(f"Welcome back, {user.first_name}!", "success")
            
            # Support redirecting back to pre-login page if Next param is present
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect_dashboard(user)
        else:
            # Audit failed attempt
            attempt_user_id = user.id if user else None
            log_action(
                action="Login Failed",
                details=f"Failed login attempt for username: '{username}'",
                user_id=attempt_user_id,
                username_attempted=username if not user else None
            )
            flash("Invalid username or password.", "danger")
            
    return render_template('auth/login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    username = current_user.username
    user_id = current_user.id
    
    # Log logout event
    log_action(
        action="Logout",
        details=f"User '{username}' logged out.",
        user_id=user_id
    )
    
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for('auth.login'))
