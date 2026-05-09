import json
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from app import db
from app.models.models import Report, Attendance, Payroll, User, AuditLog
from app.utils import log_activity

reports_bp = Blueprint('reports', __name__)

# Internal helper for role verification
def check_role(*allowed_roles):
    claims = get_jwt()
    if claims.get('role') not in allowed_roles:
        return False
    return True

# ── GET /api/reports/attendance ───────────────────────
@reports_bp.route('/attendance', methods=['GET'])
@jwt_required()
def attendance_report():
    if not check_role('admin', 'manager'):
        return jsonify({'error': 'Unauthorized. Admin or Manager role required.'}), 403

    """Returns attendance summary for a given month."""
    month = request.args.get('month')  # YYYY-MM
    if not month:
        return jsonify({'error': 'month parameter is required (YYYY-MM).'}), 400

    try:
        year, m = month.split('-')
    except ValueError:
        return jsonify({'error': 'Invalid month format. Use YYYY-MM.'}), 400

    records = Attendance.query.filter(
        db.extract('year',  Attendance.date) == int(year),
        db.extract('month', Attendance.date) == int(m)
    ).all()

    # Group by user
    summary = {}
    for r in records:
        uid = r.user_id
        if uid not in summary:
            user = User.query.get(uid)
            summary[uid] = {
                'user_id':   uid,
                'full_name': user.full_name if user else 'Unknown',
                'present':   0,
                'absent':    0,
                'late':      0,
                'half_day':  0,
                'total':     0
            }
        summary[uid][r.status] = summary[uid].get(r.status, 0) + 1
        summary[uid]['total'] += 1

    # Log the report generation
    current_user_id = get_jwt_identity()
    report = Report(
        report_name  = f'Attendance Report {month}',
        generated_by = current_user_id,
        report_type  = 'attendance',
        parameters   = json.dumps({'month': month})
    )
    db.session.add(report)
    db.session.commit()

    return jsonify({
        'report':  f'Attendance Report - {month}',
        'data':    list(summary.values()),
        'report_id': report.report_id
    }), 200


# ── GET /api/reports/payroll ──────────────────────────
@reports_bp.route('/payroll', methods=['GET'])
@jwt_required()
def payroll_report():
    if not check_role('admin', 'manager'):
        return jsonify({'error': 'Unauthorized. Admin or Manager role required.'}), 403

    """Returns payroll summary for a given month."""
    month = request.args.get('month')
    if not month:
        return jsonify({'error': 'month parameter is required (YYYY-MM).'}), 400

    payrolls = Payroll.query.filter_by(month=month).all()

    total_net = sum(float(p.net_salary) for p in payrolls)
    data = []
    for p in payrolls:
        user = User.query.get(p.user_id)
        row  = p.to_dict()
        row['full_name'] = user.full_name if user else 'Unknown'
        data.append(row)

    current_user_id = get_jwt_identity()
    report = Report(
        report_name  = f'Payroll Report {month}',
        generated_by = current_user_id,
        report_type  = 'payroll',
        parameters   = json.dumps({'month': month})
    )
    db.session.add(report)
    db.session.commit()

    return jsonify({
        'report':    f'Payroll Report - {month}',
        'month':     month,
        'employees': len(data),
        'total_net_salary': total_net,
        'data':      data,
        'report_id': report.report_id
    }), 200


# ── GET /api/reports/audit-logs (admin only) ──────────
@reports_bp.route('/audit-logs', methods=['GET'])
@jwt_required()
def audit_logs():
    if not check_role('admin'):
        return jsonify({'error': 'Unauthorized. Admin role required.'}), 403

    logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(200).all()
    return jsonify({'audit_logs': [l.to_dict() for l in logs]}), 200


# ── GET /api/reports/ (list all generated reports) ────
@reports_bp.route('/', methods=['GET'])
@jwt_required()
def list_reports():
    if not check_role('admin', 'manager'):
        return jsonify({'error': 'Unauthorized.'}), 403

    rpts = Report.query.order_by(Report.generated_on.desc()).all()
    return jsonify({'reports': [r.to_dict() for r in rpts]}), 200