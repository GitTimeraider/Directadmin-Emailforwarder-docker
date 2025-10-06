from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from app.models import db, UserDomain
from app.directadmin_api import DirectAdminAPI
import traceback

settings_bp = Blueprint('settings', __name__, url_prefix='/settings')

@settings_bp.route('/')
@login_required
def index():
    return render_template('settings.html')

# SEPARATE routes for GET and POST
@settings_bp.route('/api/da-config', methods=['GET'])
@login_required  
def get_da_config():
    """GET endpoint to retrieve current config"""
    try:
        return jsonify({
            'da_server': current_user.da_server or '',
            'da_username': current_user.da_username or '',
            'da_domain': current_user.da_domain or '',  # Keep for backward compatibility
            'domains': current_user.get_domains(),
            'has_password': bool(current_user.da_password_encrypted),
            'theme_preference': current_user.theme_preference or 'light'
        })
    except Exception as e:
        print(f"Error in GET da-config: {e}")
        print(traceback.format_exc())
        return jsonify({'error': 'An internal error has occurred. Please try again later.'}), 500

@settings_bp.route('/api/da-config', methods=['POST'])
@login_required
def update_da_config():
    """POST endpoint to update config"""
    print(f"POST to da-config from user: {current_user.username}")

    try:
        # Get JSON data
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        print(f"Received data: {data}")

        # Validate required fields (domain no longer required here)
        required_fields = ['da_server', 'da_username']
        missing_fields = [field for field in required_fields if not data.get(field, '').strip()]

        if missing_fields:
            return jsonify({
                'error': f'Missing required fields: {", ".join(missing_fields)}',
                'missing_fields': missing_fields
            }), 400

        # Ensure user has encryption key
        if not current_user.encryption_key:
            current_user.generate_encryption_key()

        # Clean and save the server URL
        server_url = data['da_server'].strip()
        if not server_url.startswith(('http://', 'https://')):
            server_url = 'https://' + server_url

        # Update settings
        current_user.da_server = server_url.rstrip('/')
        current_user.da_username = data['da_username'].strip()
        
        # Keep da_domain for backward compatibility with first domain
        if data.get('da_domain'):
            current_user.da_domain = data['da_domain'].strip()

        # Update password if provided
        if data.get('da_password'):
            current_user.set_da_password(data['da_password'])
        elif not current_user.da_password_encrypted:
            return jsonify({
                'error': 'Password is required for initial setup',
                'missing_fields': ['da_password']
            }), 400

        # Commit to database
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Settings saved successfully!'
        })

    except Exception as e:
        print(f"Error in POST da-config: {str(e)}")
        print(traceback.format_exc())
        db.session.rollback()
        return jsonify({'error': 'An internal error has occurred. Please try again later.'}), 500

# Keep test-connection separate
@settings_bp.route('/api/test-connection', methods=['POST'])
@login_required
def test_connection():
    """Test DirectAdmin connection"""
    try:
        print(f"\n=== Test Connection Request Received ===")
        data = request.get_json()
        print(f"Request data: {data}")

        # Use provided or saved credentials
        server = data.get('da_server') or current_user.da_server
        username = data.get('da_username') or current_user.da_username
        password = data.get('da_password') or current_user.get_da_password()
        
        # Get the first configured domain for testing, if any
        user_domains = current_user.get_domains()
        domain = user_domains[0] if user_domains else None

        print(f"Test connection with server: {server}, username: {username}, domain: {domain}")

        if not all([server, username, password]):
            print(f"Missing credentials - server: {bool(server)}, username: {bool(username)}, password: {bool(password)}")
            return jsonify({'error': 'Missing credentials', 'success': False}), 200

        # Ensure proper URL format
        if not server.startswith(('http://', 'https://')):
            server = 'https://' + server

        # Test connection with domain if available
        print(f"Creating DirectAdminAPI instance...")
        api = DirectAdminAPI(server, username, password, domain)
        
        print(f"Calling test_connection()...")
        success, message = api.test_connection()
        print(f"Test connection result: success={success}, message={message}")

        if not success:
            # Log the detailed error server-side
            print(f"Sanitized error: {message}")
            # Provide generic error for user
            user_message = "Connection test failed. Please check your details and try again or contact support."
            return jsonify({'success': False, 'message': user_message})

        # Only allow pre-approved success messages to be sent back to the user
        allowed_success_prefixes = [
            "Successfully connected",
            "Connected, but domain",
            "Connected, but domain",
        ]
        user_message = "Successfully connected to DirectAdmin."
        for prefix in allowed_success_prefixes:
            if message.startswith(prefix):
                user_message = message
                break
        result = {
            'success': True,
            'message': user_message
        }
        print(f"Sending response: {result}")
        return jsonify(result)

    except Exception as e:
        print(f"Test connection error: {str(e)}")
        print(traceback.format_exc())
        
        # Provide more specific error messages to the user, do not return exception messages
        user_error_msg = None
        error_str = str(e).lower()
        if 'timeout' in error_str:
            user_error_msg = 'Connection timed out. Please check your DirectAdmin server URL and network connection.'
        elif 'connection' in error_str:
            user_error_msg = 'Unable to connect to DirectAdmin server. Please verify the server URL is correct.'
        elif 'ssl' in error_str or 'certificate' in error_str:
            user_error_msg = 'SSL certificate error. Try using HTTP instead of HTTPS, or check your certificate configuration.'
        else:
            user_error_msg = 'Connection test failed. Please contact support or try again later.'
        return jsonify({'error': user_error_msg, 'success': False}), 200

@settings_bp.route('/api/domains', methods=['GET'])
@login_required
def get_domains():
    """Get all domains for the current user"""
    try:
        domains = current_user.get_domains()
        return jsonify({
            'success': True,
            'domains': domains
        })
    except Exception as e:
        print(f"Error getting domains: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'error': 'An internal error has occurred.'}), 500

@settings_bp.route('/api/domains', methods=['POST'])
@login_required
def add_domain():
    """Add a new domain for the current user"""
    try:
        data = request.get_json()
        if not data or not data.get('domain'):
            return jsonify({'error': 'Domain is required'}), 400

        domain = data['domain'].strip()
        if not domain:
            return jsonify({'error': 'Domain cannot be empty'}), 400

        # Basic domain validation
        if not '.' in domain or ' ' in domain:
            return jsonify({'error': 'Invalid domain format'}), 400

        success, message = current_user.add_domain(domain)
        
        if success:
            # Update da_domain if this is the first domain (backward compatibility)
            if not current_user.da_domain:
                current_user.da_domain = domain
            
            db.session.commit()
            return jsonify({
                'success': True,
                'message': message,
                'domains': current_user.get_domains()
            })
        else:
            return jsonify({'error': message}), 400

    except Exception as e:
        print(f"Error adding domain: {str(e)}")
        print(traceback.format_exc())
        db.session.rollback()
        return jsonify({'error': 'An internal error has occurred.'}), 500

@settings_bp.route('/api/domains', methods=['DELETE'])
@login_required
def remove_domain():
    """Remove a domain for the current user"""
    try:
        data = request.get_json()
        if not data or not data.get('domain'):
            return jsonify({'error': 'Domain is required'}), 400

        domain = data['domain'].strip()
        success, message = current_user.remove_domain(domain)
        
        if success:
            # Update da_domain if we removed the current one
            if current_user.da_domain == domain:
                first_domain = current_user.get_first_domain()
                current_user.da_domain = first_domain
            
            db.session.commit()
            return jsonify({
                'success': True,
                'message': message,
                'domains': current_user.get_domains()
            })
        else:
            return jsonify({'error': message}), 400

    except Exception as e:
        print(f"Error removing domain: {str(e)}")
        print(traceback.format_exc())
        db.session.rollback()
        return jsonify({'error': 'An internal error has occurred.'}), 500

@settings_bp.route('/api/domains/reorder', methods=['POST'])
@login_required
def reorder_domains():
    """Reorder domains for the current user"""
    try:
        data = request.get_json()
        if not data or not data.get('domains'):
            return jsonify({'error': 'Domains list is required'}), 400

        domains = data['domains']
        if not isinstance(domains, list):
            return jsonify({'error': 'Domains must be a list'}), 400

        success, message = current_user.reorder_domains(domains)
        
        if success:
            # Update da_domain to the first domain (backward compatibility)
            if domains:
                current_user.da_domain = domains[0]
            
            db.session.commit()
            return jsonify({
                'success': True,
                'message': message,
                'domains': current_user.get_domains()
            })
        else:
            return jsonify({'error': message}), 400

    except Exception as e:
        print(f"Error reordering domains: {str(e)}")
        print(traceback.format_exc())
        db.session.rollback()
        return jsonify({'error': 'An internal error has occurred.'}), 500

@settings_bp.route('/api/theme', methods=['POST'])
@login_required
def update_theme():
    """Update user theme preference"""
    try:
        data = request.get_json()
        if not data or 'theme' not in data:
            return jsonify({'error': 'Theme not provided'}), 400

        theme = data['theme']
        if theme not in ['light', 'dark']:
            return jsonify({'error': 'Invalid theme value'}), 400

        current_user.theme_preference = theme
        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'Theme updated to {theme}',
            'theme': theme
        })

    except Exception as e:
        print(f"Error updating theme: {str(e)}")
        print(traceback.format_exc())
        db.session.rollback()
        return jsonify({'error': 'An internal error has occurred.'}), 500

# Debug route to check available routes
@settings_bp.route('/api/debug-routes', methods=['GET'])
@login_required
def debug_routes():
    """Show all registered routes for debugging"""
    from flask import current_app
    routes = []
    for rule in current_app.url_map.iter_rules():
        if '/settings/' in rule.rule:
            routes.append({
                'endpoint': rule.endpoint,
                'methods': list(rule.methods),
                'path': rule.rule
            })
    return jsonify(routes)
