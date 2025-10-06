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
        try:
            if not current_user.has_da_config():
                # Redirect to settings if DirectAdmin not configured
                return redirect(url_for('settings.index'))
            return render_template('dashboard.html')
        except Exception as e:
            print(f"Error in dashboard route: {e}")
            # If there's an error (likely due to missing table), redirect to settings
            return redirect(url_for('settings.index'))

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

    @app.route('/api/migration-status', methods=['GET'])
    @login_required
    def get_migration_status():
        """Get migration status for debugging"""
        try:
            from app.models import UserDomain
            
            status = {
                'user_id': current_user.id,
                'username': current_user.username,
                'legacy_domain': current_user.da_domain,
                'has_da_config': current_user.has_da_config()
            }
            
            try:
                # Check if UserDomain table exists
                domain_count = UserDomain.query.filter_by(user_id=current_user.id).count()
                user_domains = [d.domain for d in UserDomain.query.filter_by(user_id=current_user.id).all()]
                
                status.update({
                    'table_exists': True,
                    'domain_count': domain_count,
                    'domains': user_domains,
                    'migration_needed': current_user.da_domain and domain_count == 0
                })
            except Exception as e:
                status.update({
                    'table_exists': False,
                    'table_error': str(e),
                    'migration_needed': True
                })
            
            return jsonify({
                'success': True,
                'status': status
            })
            
        except Exception as e:
            print(f"Error in /api/migration-status: {str(e)}")
            traceback.print_exc()
            return jsonify({
                'error': 'An internal error occurred while checking migration status.',
                'success': False
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

            # Validate domain access first
            domain_valid, domain_message = api.validate_domain_access()
            if not domain_valid:
                return jsonify({
                    'error': f'Domain access validation failed: {domain_message}',
                    'accounts': []
                }), 403

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

            # Validate domain access first
            domain_valid, domain_message = api.validate_domain_access()
            if not domain_valid:
                return jsonify({
                    'error': f'Domain access validation failed: {domain_message}',
                    'forwarders': []
                }), 403

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

    # Ensure DB initialization only once (important with multi-worker if --preload not used)
    if not app.config.get('_DB_INITIALIZED', False):
        with app.app_context():
            print(f"Initializing database at URI: {app.config['SQLALCHEMY_DATABASE_URI']}")
            
            # Import models to ensure they're registered
            from app.models import User, UserDomain
            
            # Check if we need to handle schema migration
            needs_migration = False
            try:
                # Test if UserDomain table exists by trying a simple query
                db.session.execute(db.text("SELECT COUNT(*) FROM user_domain")).scalar()
                print("UserDomain table exists")
            except Exception as e:
                print(f"UserDomain table doesn't exist: {e}")
                needs_migration = True
            
            # Always call create_all() to ensure all tables exist
            db.create_all()
            print("Database tables created/updated")
            
            # If we needed migration, migrate existing users
            if needs_migration:
                print("Performing automatic migration to multi-domain...")
                
                # Find all users with da_domain set
                try:
                    users_with_domains = User.query.filter(User.da_domain.isnot(None)).all()
                    print(f"Found {len(users_with_domains)} users with domains to migrate")
                    
                    for user in users_with_domains:
                        print(f"Migrating user {user.username} with domain {user.da_domain}")
                        try:
                            # Create UserDomain entry directly to avoid circular dependency
                            existing_domain = UserDomain.query.filter_by(
                                user_id=user.id, 
                                domain=user.da_domain
                            ).first()
                            
                            if not existing_domain:
                                user_domain = UserDomain(
                                    user_id=user.id,
                                    domain=user.da_domain,
                                    order_index=0
                                )
                                db.session.add(user_domain)
                                print(f"  ✓ Created domain entry for {user.username}: {user.da_domain}")
                            else:
                                print(f"  - Domain already exists for {user.username}: {user.da_domain}")
                                
                        except Exception as e:
                            print(f"  ✗ Error migrating {user.username}: {e}")
                    
                    # Commit migration changes
                    try:
                        db.session.commit()
                        print(f"✓ Successfully migrated {len(users_with_domains)} users to multi-domain.")
                    except Exception as e:
                        print(f"✗ Error during migration commit: {e}")
                        db.session.rollback()
                        
                except Exception as e:
                    print(f"Error during user migration: {e}")
                    db.session.rollback()
            else:
                # Check for users that have da_domain but no UserDomain entries
                try:
                    users_to_migrate = User.query.filter(
                        User.da_domain.isnot(None),
                        ~User.domains.any()
                    ).all()
                    
                    if users_to_migrate:
                        print(f"Found {len(users_to_migrate)} users needing domain migration...")
                        
                        for user in users_to_migrate:
                            print(f"Migrating user {user.username} with domain {user.da_domain}")
                            try:
                                user_domain = UserDomain(
                                    user_id=user.id,
                                    domain=user.da_domain,
                                    order_index=0
                                )
                                db.session.add(user_domain)
                                print(f"  ✓ Created domain entry for {user.username}: {user.da_domain}")
                            except Exception as e:
                                print(f"  ✗ Error migrating {user.username}: {e}")
                        
                        try:
                            db.session.commit()
                            print(f"✓ Successfully migrated {len(users_to_migrate)} users to multi-domain.")
                        except Exception as e:
                            print(f"✗ Error during migration commit: {e}")
                            db.session.rollback()
                            
                except Exception as e:
                    print(f"Error checking for migration: {e}")

            # Create default admin user only if no administrators exist
            admin_count = User.query.filter_by(is_admin=True).count()
            if admin_count == 0:
                # No administrators exist, create default admin user
                admin_user = User(username='admin', is_admin=True)
                admin_user.set_password('changeme')  # Default password
                db.session.add(admin_user)
                try:
                    db.session.commit()
                    print("=" * 50)
                    print("Default admin user created!")
                    print("Username: admin")
                    print("Password: changeme")
                    print("PLEASE CHANGE THIS PASSWORD IMMEDIATELY!")
                    print("=" * 50)
                except Exception as e:
                    print(f"Error creating admin user: {e}")
                    db.session.rollback()
            else:
                print(f"Found {admin_count} administrator(s) - skipping default admin creation")

            app.config['_DB_INITIALIZED'] = True

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
