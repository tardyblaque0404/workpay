from app import create_app, db

from app.models.models import User, Attendance, Payroll, Report, AuditLog

from werkzeug.security import generate_password_hash

from flask import Flask

from flask_cors import CORS

import os



app = create_app('development')

CORS(app, resources={r"/api/*": {"origins": ["http://localhost:5173"]}}, supports_credentials=True)



db_url = os.environ.get('DATABASE_URL', '')

if db_url.startswith('postgres://'):

    os.environ['DATABASE_URL'] = db_url.replace('postgres://', 'postgresql://', 1)



from app import create_app, db

from app.models.models import User

from werkzeug.security import generate_password_hash



app = create_app('development')



@app.cli.command('init-db')

def init_db():

    """Create all database tables and seed a default admin user."""

    with app.app_context():

        db.create_all()

        print("✅ Tables created.")



        # Seed default admin if no users exist

        if not User.query.first():

            admin = User(

                username      = 'admin',

                password_hash = generate_password_hash('admin123'),

                email         = 'admin@milikikasri.com',

                full_name     = 'System Administrator',

                role          = 'admin',

                basic_salary  = 0.00

            )

            db.session.add(admin)

            db.session.commit()

            print("✅ Default admin created: username='admin', password='admin123'")

        else:

            print("ℹ️  Users already exist. Skipping seed.")





if __name__ == '__main__':

    app.run(debug=True, port=5000)