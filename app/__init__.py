from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager # Added this
from flask_cors import CORS # Highly recommended for React/Flask setups
from config.config import config

db = SQLAlchemy()
jwt = JWTManager() # Added this

def create_app(config_name='default'):
    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # Ensure JWT_SECRET_KEY exists, fallback to SECRET_KEY if not
    if not app.config.get('JWT_SECRET_KEY'):
        app.config['JWT_SECRET_KEY'] = app.config.get('SECRET_KEY', 'fallback-very-secret-key')

    # Init extensions
    db.init_app(app)
    jwt.init_app(app) # Added this
    
    # Enable CORS so your React Vite app can talk to Flask without port errors
    CORS(app)

    # Register blueprints
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

    return app