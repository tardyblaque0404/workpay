import os

db_url = os.environ.get('DATABASE_URL', '')
if db_url.startswith('postgres://'):
    os.environ['DATABASE_URL'] = db_url.replace('postgres://', 'postgresql://', 1)

from app import create_app, db
from app.models.models import User
from werkzeug.security import generate_password_hash

app = create_app('development')

# This runs when gunicorn imports the module
with app.app_context():
    db.create_all()
    if not User.query.first():
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

if __name__ == '__main__':
    app.run(debug=False)