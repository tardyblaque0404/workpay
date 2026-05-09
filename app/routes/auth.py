from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from app import db
from app.models.models import User
from app.utils import log_activity 
from app import jwt

auth_bp = Blueprint('auth', __name__)

@jwt.additional_claims_loader
def add_claims_to_access_token(identity):
    user = User.query.get(identity)
    if user:
        return {"role": user.role}
    return {"role": "employee"}

# ── POST /api/auth/login ──────────────────────────────
@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()

    if not data or not data.get('username') or not data.get('password'):
        return jsonify({'error': 'Username and password are required.'}), 400

    user = User.query.filter_by(username=data['username']).first()

    if not user or not check_password_hash(user.password_hash, data['password']):
        return jsonify({'error': 'Invalid username or password.'}), 401

    # The identity is the user_id. The additional_claims_loader above 
    # will automatically add the role to this token.
    access_token = create_access_token(identity=str(user.user_id))

    log_activity(user.user_id, f"User '{user.username}' logged in.")

    return jsonify({
        'message': 'Login successful.',
        'access_token': access_token,
        'user': user.to_dict()
    }), 200

# ── POST /api/auth/logout ─────────────────────────────
@auth_bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    log_activity(user_id, f"User '{user.username if user else 'Unknown'}' logged out.")
    return jsonify({'message': 'Logged out successfully.'}), 200

# ── GET /api/auth/me ──────────────────────────────────
@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def me():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found.'}), 404
    return jsonify({'user': user.to_dict()}), 200

# ── POST /api/auth/register ───────────────────────────
@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    required = ['username', 'password', 'email', 'full_name']
    for field in required:
        if not data.get(field):
            return jsonify({'error': f'{field} is required.'}), 400

    if User.query.filter_by(username=data['username']).first():
        return jsonify({'error': 'Username already exists.'}), 409

    new_user = User(
        username      = data['username'],
        password_hash = generate_password_hash(data['password']),
        email         = data['email'],
        full_name     = data['full_name'],
        role          = data.get('role', 'employee'),
        basic_salary  = data.get('basic_salary', 0.00)
    )


    db.session.add(new_user)
    db.session.commit()
    log_activity(new_user.user_id, f"New user '{new_user.username}' registered.")

    return jsonify({
        'message': 'User registered successfully.',
        'user': new_user.to_dict()
    }), 201

@auth_bp.route('/setup', methods=['GET'])
def setup():
    """Temporary route to seed admin user - delete after use"""
    from werkzeug.security import generate_password_hash
    from app import db
    from app.models.models import User
    
    if User.query.first():
        return jsonify({'message': 'Users already exist'}), 200
    
    admin = User(
        username='admin',
        password_hash=generate_password_hash('admin123'),
        email='admin@milikikasri.com',
        full_name='System Administrator',
        role='admin',
        basic_salary=0.00
    )
    db.session.add(admin)
    db.session.commit()
    return jsonify({'message': 'Admin created successfully!'}), 201  

@auth_bp.route('/reset-admin', methods=['GET'])
def reset_admin():
    from werkzeug.security import generate_password_hash
    user = User.query.filter_by(username='admin').first()
    if not user:
        return jsonify({'error': 'Admin not found'}), 404
    user.password_hash = generate_password_hash('admin123')
    db.session.commit()
    return jsonify({'message': 'Admin password reset to admin123'}), 200