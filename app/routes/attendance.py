from datetime import date, datetime
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from app import db
from app.models.models import Attendance, User
from app.utils import log_activity # We'll handle roles differently now

attendance_bp = Blueprint('attendance', __name__)

# Helper to check roles manually since we swapped session for JWT
def check_role(*allowed_roles):
    claims = get_jwt()
    if claims.get('role') not in allowed_roles:
        return False
    return True

# ── POST /api/attendance/checkin ──────────────────────
@attendance_bp.route('/checkin', methods=['POST'])
@jwt_required()
def check_in():
    user_id = get_jwt_identity() # Identity is stored as user_id string
    today   = date.today()

    existing = Attendance.query.filter_by(user_id=user_id, date=today).first()
    if existing:
        return jsonify({'error': 'Already checked in today.'}), 409

    record = Attendance(
        user_id       = user_id,
        date          = today,
        status        = 'present',
        check_in_time = datetime.now().time()
    )
    db.session.add(record)
    db.session.commit()
    log_activity(user_id, f"Checked in at {record.check_in_time}.")
    return jsonify({'message': 'Check-in recorded.', 'record': record.to_dict()}), 201


# ── PUT /api/attendance/checkout ──────────────────────
@attendance_bp.route('/checkout', methods=['PUT'])
@jwt_required()
def check_out():
    user_id = get_jwt_identity()
    today   = date.today()

    record = Attendance.query.filter_by(user_id=user_id, date=today).first()
    if not record:
        return jsonify({'error': 'No check-in found for today.'}), 404
    if record.check_out_time:
        return jsonify({'error': 'Already checked out today.'}), 409

    record.check_out_time = datetime.now().time()
    db.session.commit()
    log_activity(user_id, f"Checked out at {record.check_out_time}.")
    return jsonify({'message': 'Check-out recorded.', 'record': record.to_dict()}), 200


# ── POST /api/attendance/manual (admin/manager) ───────
@attendance_bp.route('/manual', methods=['POST'])
@jwt_required()
def manual_entry():
    if not check_role('admin', 'manager'):
        return jsonify({'error': 'Admins or managers only.'}), 403
        
    data = request.get_json()
    required = ['user_id', 'date', 'status']
    for f in required:
        if not data.get(f):
            return jsonify({'error': f'{f} is required.'}), 400

    user = User.query.get(data['user_id'])
    if not user:
        return jsonify({'error': 'Employee not found.'}), 404

    entry_date = datetime.strptime(data['date'], '%Y-%m-%d').date()
    existing   = Attendance.query.filter_by(user_id=data['user_id'], date=entry_date).first()
    if existing:
        return jsonify({'error': 'Attendance already recorded for this date.'}), 409

    record = Attendance(
        user_id        = data['user_id'],
        date           = entry_date,
        status         = data['status'],
        check_in_time  = data.get('check_in_time'),
        check_out_time = data.get('check_out_time'),
        notes          = data.get('notes')
    )
    db.session.add(record)
    db.session.commit()
    
    current_user_id = get_jwt_identity()
    log_activity(current_user_id, f"Manual attendance entry for user {data['user_id']} on {entry_date}.")
    return jsonify({'message': 'Attendance recorded.', 'record': record.to_dict()}), 201


# ── GET /api/attendance/ ──
@attendance_bp.route('/', methods=['GET'])
@jwt_required()
def get_attendance():
    month   = request.args.get('month')
    user_id_param = request.args.get('user_id', type=int)
    
    current_user_id = get_jwt_identity()
    claims = get_jwt()
    role = claims.get('role')

    query = Attendance.query

    # Logic: Employees only see their own. Admins can filter by user_id param.
    if role == 'employee':
        query = query.filter_by(user_id=current_user_id)
    elif user_id_param:
        query = query.filter_by(user_id=user_id_param)

    if month:
        try:
            year, m = month.split('-')
            query = query.filter(
                db.extract('year',  Attendance.date) == int(year),
                db.extract('month', Attendance.date) == int(m)
            )
        except ValueError:
            return jsonify({'error': 'Invalid month format. Use YYYY-MM.'}), 400

    records = query.order_by(Attendance.date.desc()).all()
    return jsonify({'attendance': [r.to_dict() for r in records]}), 200


# ── DELETE /api/attendance/<id> ──
@attendance_bp.route('/<int:attendance_id>', methods=['DELETE'])
@jwt_required()
def delete_record(attendance_id):
    if not check_role('admin'):
        return jsonify({'error': 'Admins only.'}), 403
        
    record = Attendance.query.get_or_404(attendance_id)
    db.session.delete(record)
    db.session.commit()
    
    current_user_id = get_jwt_identity()
    log_activity(current_user_id, f"Deleted attendance record ID {attendance_id}.")
    return jsonify({'message': 'Record deleted.'}), 200