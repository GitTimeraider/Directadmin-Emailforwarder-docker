from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from app.models import db
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
            'da_domain': current_user.da_domain or '',
            'has_password': bool(current_user.da_password_encrypted)
        })
    except Exception as e:
        print(f"Error in GET da-config: {e}")
        return jsonify({'error': str(e)}), 500

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

        # Validate required fields
        required_fields = ['da_server', 'da_username', 'da_domain']
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
        data = request.get_json()

        # Use provided or saved credentials
        server = data.get('da_server') or current_user.da_server
        username = data.get('da_username') or current_user.da_username
        password = data.get('da_password') or current_user.get_da_password()

        if not all([server, username, password]):
            return jsonify({'error': 'Missing credentials'}), 400

        # Ensure proper URL format
        if not server.startswith(('http://', 'https://')):
            server = 'https://' + server

        # Test connection
        api = DirectAdminAPI(server, username, password)
        success, message = api.test_connection()

        return jsonify({
            'success': success,
            'message': message
        })

    except Exception as e:
        print(f"Test connection error: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'error': 'An internal error has occurred.', 'success': False}), 200

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
