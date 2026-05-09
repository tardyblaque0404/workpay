from datetime import datetime
from app import db


# ─────────────────────────────────────────
# 1. USERS TABLE
# ─────────────────────────────────────────
class User(db.Model):
    __tablename__ = 'users'

    user_id    = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username   = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    email      = db.Column(db.String(100), unique=True, nullable=False)
    full_name  = db.Column(db.String(100), nullable=False)
    role       = db.Column(db.Enum('admin', 'manager', 'employee'), default='employee', nullable=False)
    basic_salary = db.Column(db.Numeric(10, 2), default=0.00)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    attendance  = db.relationship('Attendance', backref='user', lazy=True)
    payrolls    = db.relationship('Payroll', backref='user', lazy=True)
    reports     = db.relationship('Report', backref='generated_by_user', lazy=True)
    audit_logs  = db.relationship('AuditLog', backref='user', lazy=True)

    def to_dict(self):
        return {
            'user_id':   self.user_id,
            'username':  self.username,
            'email':     self.email,
            'full_name': self.full_name,
            'role':      self.role,
            'basic_salary': float(self.basic_salary),
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f'<User {self.username} ({self.role})>'


# ─────────────────────────────────────────
# 2. ATTENDANCE TABLE
# ─────────────────────────────────────────
class Attendance(db.Model):
    __tablename__ = 'attendance'

    attendance_id  = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id        = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    date           = db.Column(db.Date, nullable=False)
    status         = db.Column(db.Enum('present', 'absent', 'late', 'half_day'), default='present')
    check_in_time  = db.Column(db.Time, nullable=True)
    check_out_time = db.Column(db.Time, nullable=True)
    notes          = db.Column(db.String(255), nullable=True)

    def to_dict(self):
        return {
            'attendance_id':  self.attendance_id,
            'user_id':        self.user_id,
            'date':           self.date.isoformat() if self.date else None,
            'status':         self.status,
            'check_in_time':  str(self.check_in_time) if self.check_in_time else None,
            'check_out_time': str(self.check_out_time) if self.check_out_time else None,
            'notes':          self.notes,
        }

    def __repr__(self):
        return f'<Attendance user={self.user_id} date={self.date} status={self.status}>'


# ─────────────────────────────────────────
# 3. PAYROLLS TABLE
# ─────────────────────────────────────────
class Payroll(db.Model):
    __tablename__ = 'payrolls'

    payroll_id     = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id        = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    month          = db.Column(db.String(20), nullable=False)   # e.g. "2025-03"
    basic_salary   = db.Column(db.Numeric(10, 2), nullable=False)
    overtime_pay   = db.Column(db.Numeric(10, 2), default=0.00)
    bonuses        = db.Column(db.Numeric(10, 2), default=0.00)
    deductions     = db.Column(db.Numeric(10, 2), default=0.00)
    net_salary     = db.Column(db.Numeric(10, 2), nullable=False)
    days_worked    = db.Column(db.Integer, default=0)
    status         = db.Column(db.Enum('draft', 'approved', 'paid'), default='draft')
    date_generated = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'payroll_id':     self.payroll_id,
            'user_id':        self.user_id,
            'month':          self.month,
            'basic_salary':   float(self.basic_salary),
            'overtime_pay':   float(self.overtime_pay),
            'bonuses':        float(self.bonuses),
            'deductions':     float(self.deductions),
            'net_salary':     float(self.net_salary),
            'days_worked':    self.days_worked,
            'status':         self.status,
            'date_generated': self.date_generated.isoformat() if self.date_generated else None,
        }

    def __repr__(self):
        return f'<Payroll user={self.user_id} month={self.month} net={self.net_salary}>'


# ─────────────────────────────────────────
# 4. REPORTS TABLE
# ─────────────────────────────────────────
class Report(db.Model):
    __tablename__ = 'reports'

    report_id    = db.Column(db.Integer, primary_key=True, autoincrement=True)
    report_name  = db.Column(db.String(100), nullable=False)
    generated_by = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    generated_on = db.Column(db.DateTime, default=datetime.utcnow)
    report_type  = db.Column(db.Enum('attendance', 'payroll', 'summary'), nullable=False)
    parameters   = db.Column(db.Text, nullable=True)   # JSON string of filters used

    def to_dict(self):
        return {
            'report_id':    self.report_id,
            'report_name':  self.report_name,
            'generated_by': self.generated_by,
            'generated_on': self.generated_on.isoformat() if self.generated_on else None,
            'report_type':  self.report_type,
            'parameters':   self.parameters,
        }

    def __repr__(self):
        return f'<Report {self.report_name} type={self.report_type}>'


# ─────────────────────────────────────────
# 5. AUDIT LOGS TABLE
# ─────────────────────────────────────────
class AuditLog(db.Model):
    __tablename__ = 'audit_logs'

    log_id    = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id   = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=True)
    activity  = db.Column(db.String(255), nullable=False)
    ip_address = db.Column(db.String(45), nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'log_id':     self.log_id,
            'user_id':    self.user_id,
            'activity':   self.activity,
            'ip_address': self.ip_address,
            'timestamp':  self.timestamp.isoformat() if self.timestamp else None,
        }

    def __repr__(self):
        return f'<AuditLog user={self.user_id} activity={self.activity}>'
