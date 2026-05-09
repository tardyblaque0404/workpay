from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from app import db
from app.models.models import User
from app.utils import log_activity

users_bp = Blueprint('users', __name__)

# Internal helper for role verification
def check_role(*allowed_roles):
    claims = get_jwt()
    if claims.get('role') not in allowed_roles:
        return False
    return True

# ── GET /api/users/ (admin/manager only) ─────────────
@users_bp.route('/', methods=['GET'])
@jwt_required()
def get_all_users():
    if not check_role('admin', 'manager'):
        return jsonify({'error': 'Unauthorized. Admin or Manager role required.'}), 403
        
    users = User.query.all()
    return jsonify({'users': [u.to_dict() for u in users]}), 200


# ── GET /api/users/<id> ───────────────────────────────
@users_bp.route('/<int:user_id>', methods=['GET'])
@jwt_required()
def get_user(user_id):
    current_user_id = get_jwt_identity()
    claims = get_jwt()
    
    # Employees can only view their own profile
    # Note: current_user_id from JWT is usually a string, so we cast to int for comparison
    if claims.get('role') == 'employee' and int(current_user_id) != user_id:
        return jsonify({'error': 'Forbidden.'}), 403

    user = User.query.get_or_404(user_id)
    return jsonify({'user': user.to_dict()}), 200


# ── PUT /api/users/<id> (admin only) ──────────────────
@users_bp.route('/<int:user_id>', methods=['PUT'])
@jwt_required()
def update_user(user_id):
    if not check_role('admin'):
        return jsonify({'error': 'Unauthorized. Admin role required.'}), 403
        
    user = User.query.get_or_404(user_id)
    data = request.get_json()

    if 'email' in data:
        user.email = data['email']
    if 'full_name' in data:
        user.full_name = data['full_name']
    if 'role' in data:
        user.role = data['role']
    if 'basic_salary' in data:
        user.basic_salary = data['basic_salary']
    if 'password' in data:
        user.password_hash = generate_password_hash(data['password'])

    db.session.commit()
    
    current_admin_id = get_jwt_identity()
    log_activity(current_admin_id, f"Updated user ID {user_id}.")
    
    return jsonify({'message': 'User updated.', 'user': user.to_dict()}), 200


# ── DELETE /api/users/<id> (admin only) ───────────────
@users_bp.route('/<int:user_id>', methods=['DELETE'])
@jwt_required()
def delete_user(user_id):
    if not check_role('admin'):
        return jsonify({'error': 'Unauthorized. Admin role required.'}), 403
        
    user = User.query.get_or_404(user_id)
    username_copy = user.username # Save name before deletion for the log
    
    db.session.delete(user)
    db.session.commit()
    
    current_admin_id = get_jwt_identity()
    log_activity(current_admin_id, f"Deleted user ID {user_id} ('{username_copy}').")
    
    return jsonify({'message': f"User '{username_copy}' deleted."}), 200