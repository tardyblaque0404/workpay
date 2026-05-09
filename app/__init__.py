from flask import Flask, app
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager # Added this
from flask_cors import CORS 
from config.config import config

db = SQLAlchemy()
jwt = JWTManager() 

def create_app(config_name='default'):
    app = Flask(__name__)
    app.config.from_object(config[config_name])

    CORS(app, 
        resources={r"/api/*": {"origins": ["http://localhost:5173", "https://miliki-kasri.vercel.app"]}},
        supports_credentials=True,
        allow_headers=["Content-Type", "Authorization"],
        methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    )


    if not app.config.get('JWT_SECRET_KEY'):
        app.config['JWT_SECRET_KEY'] = app.config.get('SECRET_KEY', 'fallback-very-secret-key')

    
    db.init_app(app)
    jwt.init_app(app) 
    

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

    @app.after_request
    def after_request(response):
        response.headers.add('Access-Control-Allow-Origin', 'https://miliki-kasri.vercel.app')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        response.headers.add('Access-Control-Allow-Credentials', 'true')
        return response

    return app