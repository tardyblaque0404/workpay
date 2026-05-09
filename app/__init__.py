from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from config.config import config

db = SQLAlchemy()
jwt = JWTManager()

def create_app(config_name='default'):
    app = Flask(__name__)
    app.config.from_object(config[config_name])

    if not app.config.get('JWT_SECRET_KEY'):
        app.config['JWT_SECRET_KEY'] = app.config.get('SECRET_KEY', 'fallback-secret')

    db.init_app(app)
    jwt.init_app(app)

    from app.routes.auth import auth_bp
    from app.routes.users import users_bp
    from app.routes.attendance import attendance_bp
    from app.routes.payroll import payroll_bp
    from app.routes.reports import reports_bp

    app.register_blueprint(auth_bp,       url_prefix='/api/auth')
    app.register_blueprint(users_bp,      url_prefix='/api/users')
    app.register_blueprint(attendance_bp, url_prefix='/api/attendance')
    app.register_blueprint(payroll_bp,    url_prefix='/api/payroll')
    app.register_blueprint(reports_bp,    url_prefix='/api/reports')

    # Handle preflight OPTIONS requests
    @app.before_request
    def handle_options():
        if request.method == 'OPTIONS':
            response = jsonify({'status': 'ok'})
            response.headers['Access-Control-Allow-Origin'] = 'https://miliki-kasri.vercel.app'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
            response.headers['Access-Control-Allow-Credentials'] = 'true'
            return response, 200

    @app.after_request
    def add_cors_headers(response):
        response.headers['Access-Control-Allow-Origin'] = 'https://miliki-kasri.vercel.app'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        return response

    return app