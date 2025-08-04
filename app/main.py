from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_login import LoginManager, login_required, current_user
from app.models import db, User
from app.config import Config
from app.directadmin_api import DirectAdminAPI
import traceback

def create_app():
    """Create and configure the Flask application"""
    app = Flask(__name__, 
                template_folder='templates',
                static_folder='../static')

    # Load configuration
    app.config.from_object(Config)

    # Initialize database
    db.init_app(app)

    # Initialize login manager
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please login to access this page.'

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

    # ===== Main Routes =====

    @app.route('/')
    @login_required
    def index():
        """Redirect to dashboard"""
        return redirect(url_for('dashboard'))

    @app.route('/dashboard')
    @login_required
    def dashboard():
        """Main dashboard page"""
        if not current_user.has_da_config():
            # Redirect to settings if DirectAdmin not configured
            return redirect(url_for('settings.index'))
        return render_template('dashboard.html')

    # ===== API Routes =====

    @app.route('/api/email-accounts', methods=['GET'])
    @login_required
    def get_email_accounts():
        """Get all email accounts for the configured domain"""
        if not current_user.has_da_config():
            return jsonify({
                'error': 'DirectAdmin not configured',
                'accounts': []
            }), 400

        try:
            # Create API instance
            api = DirectAdminAPI(
                current_user.da_server,
                current_user.da_username,
                current_user.get_da_password(),
                current_user.da_domain
            )

            # Get email accounts
            accounts = api.get_email_accounts()

            # Ensure it's a list
            if not isinstance(accounts, list):
                accounts = []

            print(f"API returning {len(accounts)} email accounts")

            return jsonify({
                'success': True,
                'accounts': accounts
            })

        except Exception as e:
            print(f"Error in /api/email-accounts: {str(e)}")
            traceback.print_exc()
            return jsonify({
                'error': 'Failed to fetch email accounts',
                'details': str(e),
                'accounts': []
            }), 500

    @app.route('/api/forwarders', methods=['GET'])
    @login_required
    def get_forwarders():
        """Get all email forwarders"""
        if not current_user.has_da_config():
            return jsonify({
                'error': 'DirectAdmin not configured',
                'forwarders': []
            }), 400

        try:
            # Create API instance
            api = DirectAdminAPI(
                current_user.da_server,
                current_user.da_username,
                current_user.get_da_password(),
                current_user.da_domain
            )

            # Get forwarders
            forwarders = api.get_forwarders()

            # Ensure it's a list
            if not isinstance(forwarders, list):
                forwarders = []

            print(f"API returning {len(forwarders)} forwarders")

            return jsonify({
                'success': True,
                'forwarders': forwarders
            })

        except Exception as e:
            print(f"Error in /api/forwarders: {str(e)}")
            traceback.print_exc()
            return jsonify({
                'error': 'Failed to fetch forwarders',
                'details': str(e),
                'forwarders': []
            }), 500

    @app.route('/api/forwarders', methods=['POST'])
    @login_required
    def create_forwarder():
        """Create a new email forwarder"""
        if not current_user.has_da_config():
            return jsonify({'error': 'DirectAdmin not configured'}), 400

        try:
            # Get request data
            data = request.get_json()
            if not data:
                return jsonify({'error': 'No data provided'}), 400

            address = data.get('address', '').strip()
            destination = data.get('destination', '').strip()

            # Validate inputs
            if not address:
                return jsonify({'error': 'Email address is required'}), 400

            if not destination:
                return jsonify({'error': 'Destination email is required'}), 400

            # Create API instance
            api = DirectAdminAPI(
                current_user.da_server,
                current_user.da_username,
                current_user.get_da_password(),
                current_user.da_domain
            )

            # Create the forwarder
            success, message = api.create_forwarder(address, destination)

            if success:
                return jsonify({
                    'success': True,
                    'message': message
                })
            else:
                return jsonify({
                    'error': message
                }), 400

        except Exception as e:
            print(f"Error creating forwarder: {str(e)}")
            traceback.print_exc()
            return jsonify({
                'error': 'Failed to create forwarder',
                'details': str(e)
            }), 500

    @app.route('/api/forwarders', methods=['DELETE'])
    @login_required
    def delete_forwarder():
        """Delete an email forwarder"""
        if not current_user.has_da_config():
            return jsonify({'error': 'DirectAdmin not configured'}), 400

        try:
            # Get request data
            data = request.get_json()
            if not data:
                return jsonify({'error': 'No data provided'}), 400

            address = data.get('address', '').strip()

            if not address:
                return jsonify({'error': 'Email address is required'}), 400

            # Create API instance
            api = DirectAdminAPI(
                current_user.da_server,
                current_user.da_username,
                current_user.get_da_password(),
                current_user.da_domain
            )

            # Delete the forwarder
            success, message = api.delete_forwarder(address)

            if success:
                return jsonify({
                    'success': True,
                    'message': message
                })
            else:
                return jsonify({
                    'error': message
                }), 400

        except Exception as e:
            print(f"Error deleting forwarder: {str(e)}")
            traceback.print_exc()
            return jsonify({
                'error': 'Failed to delete forwarder',
                'details': str(e)
            }), 500

    # ===== Error Handlers =====

    @app.errorhandler(404)
    def not_found(error):
        """Handle 404 errors"""
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Endpoint not found'}), 404
        return render_template('404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        """Handle 500 errors"""
        # Rollback database session
        db.session.rollback()

        if request.path.startswith('/api/'):
            return jsonify({'error': 'Internal server error'}), 500
        return render_template('500.html'), 500

    @app.errorhandler(Exception)
    def handle_exception(error):
        """Handle uncaught exceptions"""
        print(f"Uncaught exception: {str(error)}")
        traceback.print_exc()

        # Rollback database session
        db.session.rollback()

        if request.path.startswith('/api/'):
            return jsonify({
                'error': 'An unexpected error occurred',
                'details': str(error) if app.config.get('DEBUG') else None
            }), 500
        return render_template('500.html'), 500

    # ===== Database Initialization =====

    with app.app_context():
        # Create all tables
        db.create_all()

        # Create default admin user if it doesn't exist
        admin_user = User.query.filter_by(username='admin').first()
        if not admin_user:
            admin_user = User(username='admin', is_admin=True)
            admin_user.set_password('admin')  # CHANGE THIS IN PRODUCTION!
            db.session.add(admin_user)
            try:
                db.session.commit()
                print("=" * 50)
                print("Admin user created!")
                print("Username: admin")
                print("Password: admin")
                print("PLEASE CHANGE THIS PASSWORD IMMEDIATELY!")
                print("=" * 50)
            except Exception as e:
                print(f"Error creating admin user: {e}")
                db.session.rollback()

    # ===== Additional App Configuration =====

    @app.before_request
    def before_request():
        """Run before each request"""
        # Ensure database session is fresh
        db.session.expire_all()

    @app.teardown_appcontext
    def shutdown_session(exception=None):
        """Clean up database session"""
        db.session.remove()

    # ===== Template Filters =====

    @app.template_filter('datetime')
    def datetime_filter(value, format='%Y-%m-%d %H:%M'):
        """Format datetime for templates"""
        if value is None:
            return ''
        return value.strftime(format)

    @app.context_processor
    def inject_globals():
        """Inject global variables into templates"""
        return {
            'app_name': 'DirectAdmin Email Forwarder',
            'version': '1.0.0'
        }

    # ===== CLI Commands (optional) =====

    @app.cli.command()
    def init_db():
        """Initialize the database"""
        db.create_all()
        print("Database initialized!")

    @app.cli.command()
    def create_admin():
        """Create an admin user"""
        import getpass
        username = input("Enter admin username: ")
        password = getpass.getpass("Enter admin password: ")

        user = User(username=username, is_admin=True)
        user.set_password(password)
        db.session.add(user)

        try:
            db.session.commit()
            print(f"Admin user '{username}' created successfully!")
        except Exception as e:
            print(f"Error creating admin user: {e}")
            db.session.rollback()

    return app


# Create app instance for running
app = create_app()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
