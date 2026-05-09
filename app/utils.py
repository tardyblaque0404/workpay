from functools import wraps
from flask import session, jsonify, request
from app import db
from app.models.models import AuditLog


def login_required(f):
    """Decorator: blocks access if user is not logged in."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Unauthorized. Please log in.'}), 401
        return f(*args, **kwargs)
    return decorated


def roles_required(*roles):
    """Decorator: restricts access to specific roles."""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if 'user_id' not in session:
                return jsonify({'error': 'Unauthorized. Please log in.'}), 401
            if session.get('role') not in roles:
                return jsonify({'error': 'Forbidden. Insufficient permissions.'}), 403
            return f(*args, **kwargs)
        return decorated
    return decorator


def log_activity(user_id, activity):
    """Helper: write an entry to the audit_logs table."""
    try:
        log = AuditLog(
            user_id=user_id,
            activity=activity,
            ip_address=request.remote_addr
        )
        db.session.add(log)
        db.session.commit()
    except Exception:
        db.session.rollback()
