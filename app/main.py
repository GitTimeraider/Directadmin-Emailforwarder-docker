from flask import Flask, render_template, request, jsonify, redirect, url_for, send_from_directory
from flask_login import LoginManager, login_required, current_user
from datetime import datetime
from app.models import db, User
from app.auth import auth_bp
from app.admin import admin_bp
from app.settings import settings_bp
from app.directadmin_api import DirectAdminAPI
from app.config import Config
import os

def create_app():
    app = Flask(__name__, 
                static_folder='../static',
                template_folder='templates')
    app.config.from_object(Config)

    # Ensure data directory exists
    data_dir = '/app/data' if os.path.exists('/app') else './data'
    os.makedirs(data_dir, exist_ok=True)

    # Update database path
    if 'sqlite' in app.config.get('SQLALCHEMY_DATABASE_URI', ''):
        app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{data_dir}/users.db'

    db.init_app(app)

    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(settings_bp)  # Register settings blueprint

    # Initialize database
    with app.app_context():
        try:
            db.create_all()
            # Create default admin user if none exists
            if User.query.count() == 0:
                user = User(username='admin', is_admin=True)
                user.set_password('changeme')
                db.session.add(user)
                db.session.commit()
                print("Created default admin user")
        except Exception as e:
            print(f"Database initialization error: {e}")

    @app.route('/static/<path:filename>')
    def serve_static(filename):
        return send_from_directory(app.static_folder, filename)

    @app.route('/')
    @login_required
    def index():
        # Check if user has configured DirectAdmin settings
        if not current_user.has_da_config():
            return redirect(url_for('settings.index'))
        return redirect(url_for('dashboard'))

    @app.route('/dashboard')
    @login_required
    def dashboard():
        # Check if user has configured DirectAdmin settings
        if not current_user.has_da_config():
            flash('Please configure your DirectAdmin settings first.', 'warning')
            return redirect(url_for('settings.index'))

        # Update last login
        current_user.last_login = datetime.utcnow()
        db.session.commit()
        return render_template('dashboard.html', domain=current_user.da_domain)

    @app.route('/api/email-accounts')
    @login_required
    def get_email_accounts():
        if not current_user.has_da_config():
            return jsonify({'error': 'DirectAdmin not configured'}), 400

        try:
            api = DirectAdminAPI(
                current_user.da_server,
                current_user.da_username,
                current_user.get_da_password()
            )
            accounts = api.get_email_accounts(current_user.da_domain)
            return jsonify(accounts)
        except Exception as e:
            print(f"Error getting email accounts: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/forwarders')
    @login_required
    def get_forwarders():
        if not current_user.has_da_config():
            return jsonify({'error': 'DirectAdmin not configured'}), 400

        try:
            api = DirectAdminAPI(
                current_user.da_server,
                current_user.da_username,
                current_user.get_da_password()
            )
            forwarders = api.get_forwarders(current_user.da_domain)
            return jsonify(forwarders)
        except Exception as e:
            print(f"Error getting forwarders: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/forwarders', methods=['POST'])
    @login_required
    def create_forwarder():
        if not current_user.has_da_config():
            return jsonify({'error': 'DirectAdmin not configured'}), 400

        try:
            data = request.json
            api = DirectAdminAPI(
                current_user.da_server,
                current_user.da_username,
                current_user.get_da_password()
            )
            success = api.create_forwarder(current_user.da_domain, data['alias'], data['destination'])
            return jsonify({'success': success})
        except Exception as e:
            print(f"Error creating forwarder: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/forwarders/<alias>', methods=['DELETE'])
    @login_required
    def delete_forwarder(alias):
        if not current_user.has_da_config():
            return jsonify({'error': 'DirectAdmin not configured'}), 400

        try:
            api = DirectAdminAPI(
                current_user.da_server,
                current_user.da_username,
                current_user.get_da_password()
            )
            success = api.delete_forwarder(current_user.da_domain, alias)
            return jsonify({'success': success})
        except Exception as e:
            print(f"Error deleting forwarder: {e}")
            return jsonify({'error': str(e)}), 500

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0')
