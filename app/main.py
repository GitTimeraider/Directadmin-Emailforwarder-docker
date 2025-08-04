from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_login import LoginManager, login_required, current_user
from app.models import db, User
from app.config import Config
from app.directadmin_api import DirectAdminAPI

def create_app():
    app = Flask(__name__, 
                template_folder='templates',
                static_folder='../static')

    app.config.from_object(Config)

    # Initialize extensions
    db.init_app(app)

    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Register blueprints
    from app.auth import auth_bp
    from app.admin import admin_bp
    from app.settings import settings_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(settings_bp)

    # Main routes
    @app.route('/')
    @login_required
    def index():
        return redirect(url_for('dashboard'))

    @app.route('/dashboard')
    @login_required
    def dashboard():
        if not current_user.has_da_config():
            return redirect(url_for('settings.index'))
        return render_template('dashboard.html')

    @app.route('/api/forwarders', methods=['GET'])
    @login_required
    def get_forwarders():
        """Get all forwarders - NO EXTRA ARGUMENTS"""
        if not current_user.has_da_config():
            return jsonify({'error': 'DirectAdmin not configured'}), 400

        try:
            api = DirectAdminAPI(
                current_user.da_server,
                current_user.da_username,
                current_user.get_da_password(),
                current_user.da_domain
            )

            # Call without extra arguments!
            forwarders = api.get_forwarders()  # ← No arguments here!

            return jsonify({'forwarders': forwarders})

        except Exception as e:
            print(f"Error getting forwarders: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/forwarders', methods=['POST'])
    @login_required
    def create_forwarder():
        """Create a new forwarder"""
        if not current_user.has_da_config():
            return jsonify({'error': 'DirectAdmin not configured'}), 400

        try:
            data = request.get_json()
            address = data.get('address')
            destination = data.get('destination')

            if not address or not destination:
                return jsonify({'error': 'Address and destination required'}), 400

            api = DirectAdminAPI(
                current_user.da_server,
                current_user.da_username,
                current_user.get_da_password(),
                current_user.da_domain
            )

            success, message = api.create_forwarder(address, destination)

            if success:
                return jsonify({'success': True, 'message': message})
            else:
                return jsonify({'error': message}), 400

        except Exception as e:
            print(f"Error creating forwarder: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/forwarders', methods=['DELETE'])
    @login_required
    def delete_forwarder():
        """Delete a forwarder"""
        if not current_user.has_da_config():
            return jsonify({'error': 'DirectAdmin not configured'}), 400

        try:
            data = request.get_json()
            address = data.get('address')

            if not address:
                return jsonify({'error': 'Address required'}), 400

            api = DirectAdminAPI(
                current_user.da_server,
                current_user.da_username,
                current_user.get_da_password(),
                current_user.da_domain
            )

            success, message = api.delete_forwarder(address)

            if success:
                return jsonify({'success': True, 'message': message})
            else:
                return jsonify({'error': message}), 400

        except Exception as e:
            print(f"Error deleting forwarder: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/email-accounts', methods=['GET'])
    @login_required
    def get_email_accounts():
        """Get all email accounts - NO EXTRA ARGUMENTS"""
        if not current_user.has_da_config():
            return jsonify({'error': 'DirectAdmin not configured'}), 400

        try:
            api = DirectAdminAPI(
                current_user.da_server,
                current_user.da_username,
                current_user.get_da_password(),
                current_user.da_domain
            )

            # Call without extra arguments!
            accounts = api.get_email_accounts()  # ← No arguments here!

            return jsonify({'accounts': accounts})

        except Exception as e:
            print(f"Error getting email accounts: {e}")
            return jsonify({'error': str(e)}), 500

    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return render_template('404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template('500.html'), 500

    # Create tables
    with app.app_context():
        db.create_all()

        # Create admin user if doesn't exist
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            admin = User(username='admin', is_admin=True)
            admin.set_password('admin')  # Change this!
            db.session.add(admin)
            db.session.commit()
            print("Admin user created with password: admin")

    return app
