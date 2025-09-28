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

    @app.route('/api/domains', methods=['GET'])
    @login_required
    def get_user_domains():
        """Get all domains for the current user"""
        try:
            domains = current_user.get_domains()
            return jsonify({
                'success': True,
                'domains': domains
            })
        except Exception as e:
            print(f"Error in /api/domains: {str(e)}")
            traceback.print_exc()
            return jsonify({
                'error': 'Failed to fetch domains',
                'domains': []
            }), 500

    @app.route('/api/email-accounts', methods=['GET'])
    @login_required
    def get_email_accounts():
        """Get all email accounts for the specified domain"""
        if not current_user.has_da_config():
            return jsonify({
                'error': 'DirectAdmin not configured',
                'accounts': []
            }), 400

        try:
            # Get domain from query parameter or use first domain
            domain = request.args.get('domain')
            if not domain:
                domain = current_user.get_first_domain()
            
            if not domain:
                return jsonify({
                    'error': 'No domain specified',
                    'accounts': []
                }), 400

            # Verify user has access to this domain
            user_domains = current_user.get_domains()
            if domain not in user_domains:
                return jsonify({
                    'error': 'Access denied to domain',
                    'accounts': []
                }), 403

            # Create API instance
            api = DirectAdminAPI(
                current_user.da_server,
                current_user.da_username,
                current_user.get_da_password(),
                domain
            )

            # Get email accounts
            accounts = api.get_email_accounts()

            # Ensure it's a list
            if not isinstance(accounts, list):
                accounts = []

            print(f"API returning {len(accounts)} email accounts for domain {domain}")

            return jsonify({
                'success': True,
                'accounts': accounts,
                'domain': domain
            })

        except Exception as e:
            print(f"Error in /api/email-accounts: {str(e)}")
            traceback.print_exc()
            return jsonify({
                'error': 'Failed to fetch email accounts',
                'accounts': []
            }), 500

    @app.route('/api/forwarders', methods=['GET'])
    @login_required
    def get_forwarders():
        """Get all email forwarders for the specified domain"""
        if not current_user.has_da_config():
            return jsonify({
                'error': 'DirectAdmin not configured',
                'forwarders': []
            }), 400

        try:
            # Get domain from query parameter or use first domain
            domain = request.args.get('domain')
            if not domain:
                domain = current_user.get_first_domain()
            
            if not domain:
                return jsonify({
                    'error': 'No domain specified',
                    'forwarders': []
                }), 400

            # Verify user has access to this domain
            user_domains = current_user.get_domains()
            if domain not in user_domains:
                return jsonify({
                    'error': 'Access denied to domain',
                    'forwarders': []
                }), 403

            # Create API instance
            api = DirectAdminAPI(
                current_user.da_server,
                current_user.da_username,
                current_user.get_da_password(),
                domain
            )

            # Get forwarders
            forwarders = api.get_forwarders()

            # Ensure it's a list
            if not isinstance(forwarders, list):
                forwarders = []

            print(f"API returning {len(forwarders)} forwarders for domain {domain}")

            return jsonify({
                'success': True,
                'forwarders': forwarders,
                'domain': domain
            })

        except Exception as e:
            print(f"Error in /api/forwarders: {str(e)}")
            traceback.print_exc()
            return jsonify({
                'error': 'Failed to fetch forwarders',
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
            domain = data.get('domain', '').strip()

            # Validate inputs
            if not address:
                return jsonify({'error': 'Email address is required'}), 400

            if not destination:
                return jsonify({'error': 'Destination email is required'}), 400

            # Get domain or use first domain
            if not domain:
                domain = current_user.get_first_domain()
            
            if not domain:
                return jsonify({'error': 'No domain specified'}), 400

            # Verify user has access to this domain
            user_domains = current_user.get_domains()
            if domain not in user_domains:
                return jsonify({'error': 'Access denied to domain'}), 403

            # Create API instance
            api = DirectAdminAPI(
                current_user.da_server,
                current_user.da_username,
                current_user.get_da_password(),
                domain
            )

            # Create the forwarder
            success, message = api.create_forwarder(address, destination)

            if success:
                return jsonify({
                    'success': True,
                    'message': message,
                    'domain': domain
                })
            else:
                return jsonify({
                    'error': 'Failed to create forwarder'
                }), 400

        except Exception as e:
            print(f"Error creating forwarder: {str(e)}")
            traceback.print_exc()
            return jsonify({
                'error': 'Failed to create forwarder'
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
            domain = data.get('domain', '').strip()

            if not address:
                return jsonify({'error': 'Email address is required'}), 400

            # Extract domain from address if not provided
            if not domain and '@' in address:
                domain = address.split('@')[1]
            elif not domain:
                domain = current_user.get_first_domain()
            
            if not domain:
                return jsonify({'error': 'No domain specified'}), 400

            # Verify user has access to this domain
            user_domains = current_user.get_domains()
            if domain not in user_domains:
                return jsonify({'error': 'Access denied to domain'}), 403

            # Create API instance
            api = DirectAdminAPI(
                current_user.da_server,
                current_user.da_username,
                current_user.get_da_password(),
                domain
            )

            # Delete the forwarder
            success, message = api.delete_forwarder(address)

            if success:
                return jsonify({
                    'success': True,
                    'message': message,
                    'domain': domain
                })
            else:
                return jsonify({
                    'error': message
                }), 400

        except Exception as e:
            print(f"Error deleting forwarder: {str(e)}")
            traceback.print_exc()
            return jsonify({
                'error': 'Failed to delete forwarder'
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

        # Ensure DB initialization only once (important with multi-worker if --preload not used)\n    if not app.config.get('_DB_INITIALIZED', False):\n        with app.app_context():\n            print(f\"Initializing database at URI: {app.config['SQLALCHEMY_DATABASE_URI']}\")\n            db.create_all()\n\n            # Migrate existing users from single domain to multi-domain\n            print(\"Checking for users to migrate to multi-domain...\")\n            users_to_migrate = User.query.filter(\n                User.da_domain.isnot(None),\n                ~User.domains.any()\n            ).all()\n            \n            for user in users_to_migrate:\n                print(f\"Migrating user {user.username} with domain {user.da_domain}\")\n                success, message = user.add_domain(user.da_domain)\n                if success:\n                    print(f\"  ✓ Migrated {user.username}: {message}\")\n                else:\n                    print(f\"  ✗ Failed to migrate {user.username}: {message}\")\n            \n            if users_to_migrate:\n                try:\n                    db.session.commit()\n                    print(f\"Successfully migrated {len(users_to_migrate)} users to multi-domain.\")\n                except Exception as e:\n                    print(f\"Error during migration: {e}\")\n                    db.session.rollback()\n\n            # Create default admin user only if no administrators exist\n            admin_count = User.query.filter_by(is_admin=True).count()\n            if admin_count == 0:\n                # No administrators exist, create default admin user\n                admin_user = User(username='admin', is_admin=True)\n                admin_user.set_password('changeme')  # Default password\n                db.session.add(admin_user)\n                try:\n                    db.session.commit()\n                    print(\"=\" * 50)\n                    print(\"Default admin user created!\")\n                    print(\"Username: admin\")\n                    print(\"Password: changeme\")\n                    print(\"PLEASE CHANGE THIS PASSWORD IMMEDIATELY!\")\n                    print(\"=\" * 50)\n                except Exception as e:\n                    print(f\"Error creating admin user: {e}\")\n                    db.session.rollback()\n            else:\n                print(f\"Found {admin_count} administrator(s) - skipping default admin creation\")\n\n            app.config['_DB_INITIALIZED'] = True

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
    app.run(host='0.0.0.0', port=5000)
