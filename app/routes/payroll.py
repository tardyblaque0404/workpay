from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from app import db
from app.models.models import Payroll, Attendance, User
from app.utils import log_activity
from datetime import datetime

payroll_bp = Blueprint('payroll', __name__)

# Internal helper to handle the role checks previously done by roles_required
def check_role(*allowed_roles):
    claims = get_jwt()
    if claims.get('role') not in allowed_roles:
        return False
    return True

def calculate_net_salary(basic_salary, days_worked, working_days_in_month,
                        overtime_pay=0, bonuses=0, deductions=0):
    daily_rate  = float(basic_salary) / working_days_in_month if working_days_in_month else 0
    earned      = daily_rate * days_worked
    net_salary  = earned + float(overtime_pay) + float(bonuses) - float(deductions)
    return round(net_salary, 2)


# ── POST /api/payroll/generate (admin only) ───────────
@payroll_bp.route('/generate', methods=['POST'])
@jwt_required()
def generate_payroll():
    if not check_role('admin', 'manager'):
        return jsonify({'error': 'Unauthorized. Admin or Manager role required.'}), 403

    data = request.get_json()
    required = ['user_id', 'month']
    for f in required:
        if not data.get(f):
            return jsonify({'error': f'{f} is required.'}), 400

    user = User.query.get(data['user_id'])
    if not user:
        return jsonify({'error': 'Employee not found.'}), 404

    month = data['month']  # YYYY-MM

    existing = Payroll.query.filter_by(user_id=data['user_id'], month=month).first()
    if existing:
        return jsonify({'error': f'Payroll for {month} already exists for this employee.'}), 409

    try:
        year, m = month.split('-')
    except ValueError:
        return jsonify({'error': 'Invalid month format. Use YYYY-MM.'}), 400

    attendance_records = Attendance.query.filter(
        Attendance.user_id == data['user_id'],
        db.extract('year',  Attendance.date) == int(year),
        db.extract('month', Attendance.date) == int(m),
        Attendance.status.in_(['present', 'late', 'half_day'])
    ).all()

    days_worked = sum(0.5 if r.status == 'half_day' else 1 for r in attendance_records)

    working_days   = int(data.get('working_days', 26))
    overtime_pay   = float(data.get('overtime_pay', 0))
    bonuses        = float(data.get('bonuses', 0))
    deductions     = float(data.get('deductions', 0))
    basic_salary   = float(data.get('basic_salary', user.basic_salary))

    net_salary = calculate_net_salary(
        basic_salary, days_worked, working_days,
        overtime_pay, bonuses, deductions
    )

    payroll = Payroll(
        user_id      = data['user_id'],
        month        = month,
        basic_salary = basic_salary,
        overtime_pay = overtime_pay,
        bonuses      = bonuses,
        deductions   = deductions,
        net_salary   = net_salary,
        days_worked  = days_worked,
        status       = 'draft'
    )
    db.session.add(payroll)
    db.session.commit()

    current_user_id = get_jwt_identity()
    log_activity(current_user_id, f"Generated payroll for user {data['user_id']} for {month}.")
    return jsonify({'message': 'Payroll generated.', 'payroll': payroll.to_dict()}), 201


# ── POST /api/payroll/generate-all (admin only) ───────
@payroll_bp.route('/generate-all', methods=['POST'])
@jwt_required()
def generate_all_payrolls():
    if not check_role('admin'):
        return jsonify({'error': 'Unauthorized. Admin role required.'}), 403

    data = request.get_json()
    month = data.get('month')
    if not month:
        return jsonify({'error': 'month is required.'}), 400

    employees = User.query.filter(User.role == 'employee').all()
    generated, skipped = [], []

    for emp in employees:
        existing = Payroll.query.filter_by(user_id=emp.user_id, month=month).first()
        if existing:
            skipped.append(emp.user_id)
            continue

        try:
            year, m = month.split('-')
        except ValueError:
            return jsonify({'error': 'Invalid month format. Use YYYY-MM.'}), 400

        records = Attendance.query.filter(
            Attendance.user_id == emp.user_id,
            db.extract('year',  Attendance.date) == int(year),
            db.extract('month', Attendance.date) == int(m),
            Attendance.status.in_(['present', 'late', 'half_day'])
        ).all()

        days_worked = sum(0.5 if r.status == 'half_day' else 1 for r in records)
        working_days = int(data.get('working_days', 26))

        net_salary = calculate_net_salary(emp.basic_salary, days_worked, working_days)

        payroll = Payroll(
            user_id      = emp.user_id,
            month        = month,
            basic_salary = float(emp.basic_salary),
            net_salary   = net_salary,
            days_worked  = days_worked,
            status       = 'draft'
        )
        db.session.add(payroll)
        generated.append(emp.user_id)

    db.session.commit()
    current_user_id = get_jwt_identity()
    log_activity(current_user_id, f"Bulk payroll generated for {month}. Generated: {len(generated)}, Skipped: {len(skipped)}.")

    return jsonify({
        'message': f'Payroll generation complete for {month}.',
        'generated': generated,
        'skipped':   skipped
    }), 201


# ── GET /api/payroll/ ──
@payroll_bp.route('/', methods=['GET'])
@jwt_required()
def get_payrolls():
    month   = request.args.get('month')
    user_id_param = request.args.get('user_id', type=int)

    current_user_id = get_jwt_identity()
    claims = get_jwt()
    role = claims.get('role')

    query = Payroll.query

    if role == 'employee':
        query = query.filter_by(user_id=current_user_id)
    elif user_id_param:
        query = query.filter_by(user_id=user_id_param)

    if month:
        query = query.filter_by(month=month)

    payrolls = query.order_by(Payroll.date_generated.desc()).all()
    return jsonify({'payrolls': [p.to_dict() for p in payrolls]}), 200


# ── PUT /api/payroll/<id>/status ──
@payroll_bp.route('/<int:payroll_id>/status', methods=['PUT'])
@jwt_required()
def update_status(payroll_id):
    if not check_role('admin'):
        return jsonify({'error': 'Unauthorized.'}), 403

    payroll = Payroll.query.get_or_404(payroll_id)
    data    = request.get_json()
    status  = data.get('status')

    if status not in ('draft', 'approved', 'paid'):
        return jsonify({'error': 'Status must be draft, approved, or paid.'}), 400

    payroll.status = status
    db.session.commit()
    
    current_user_id = get_jwt_identity()
    log_activity(current_user_id, f"Payroll ID {payroll_id} status updated to '{status}'.")
    return jsonify({'message': f'Payroll marked as {status}.', 'payroll': payroll.to_dict()}), 200


# ── DELETE /api/payroll/<id> ──
@payroll_bp.route('/<int:payroll_id>', methods=['DELETE'])
@jwt_required()
def delete_payroll(payroll_id):
    if not check_role('admin'):
        return jsonify({'error': 'Unauthorized.'}), 403

    payroll = Payroll.query.get_or_404(payroll_id)
    db.session.delete(payroll)
    db.session.commit()
    
    current_user_id = get_jwt_identity()
    log_activity(current_user_id, f"Deleted payroll ID {payroll_id}.")
    return jsonify({'message': 'Payroll deleted.'}), 200