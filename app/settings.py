from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from app.models import db
from app.directadmin_api import DirectAdminAPI
import traceback

settings_bp = Blueprint('settings', __name__, url_prefix='/settings')

@settings_bp.route('/')
@login_required
def index():
    return render_template('settings.html')

@settings_bp.route('/api/da-config', methods=['GET'])
@login_required  
def get_da_config():
    try:
        return jsonify({
            'da_server': current_user.da_server or '',
            'da_username': current_user.da_username or '',
            'da_domain': current_user.da_domain or '',
            'has_password': bool(current_user.da_password_encrypted)
        })
    except Exception as e:
        print(f"Error getting DA config: {e}")
        return jsonify({'error': str(e)}), 500

@settings_bp.route('/api/da-config', methods=['POST'])
@login_required
def update_da_config():
    """Save DirectAdmin settings WITHOUT testing connection"""
    try:
        # Ensure we have JSON data
        if not request.is_json:
            return jsonify({'error': 'Content-Type must be application/json'}), 400

        data = request.json
        print(f"Saving settings for user: {current_user.username}")

        # Basic validation - just check if fields are provided
        required_fields = ['da_server', 'da_username', 'da_domain']
        missing_fields = []

        for field in required_fields:
            if not data.get(field, '').strip():
                missing_fields.append(field)

        if missing_fields:
            return jsonify({
                'error': f'Missing required fields: {", ".join(missing_fields)}',
                'missing_fields': missing_fields
            }), 400

        # Ensure user has encryption key
        if not current_user.encryption_key:
            print("Generating encryption key for user")
            current_user.generate_encryption_key()

        # Clean and save the server URL
        server_url = data['da_server'].strip()
        # Ensure it has a protocol
        if not server_url.startswith(('http://', 'https://')):
            server_url = 'https://' + server_url

        # Update DirectAdmin settings
        current_user.da_server = server_url.rstrip('/')
        current_user.da_username = data['da_username'].strip()
        current_user.da_domain = data['da_domain'].strip()

        # Only update password if provided
        if data.get('da_password'):
            print("Updating DA password")
            current_user.set_da_password(data['da_password'])
        elif not current_user.da_password_encrypted:
            # No existing password and none provided
            return jsonify({
                'error': 'Password is required for initial setup',
                'missing_fields': ['da_password']
            }), 400

        # Save to database
        db.session.commit()
        print("Settings saved successfully")

        return jsonify({
            'success': True, 
            'message': 'Settings saved successfully! (Connection not tested)',
            'saved_data': {
                'da_server': current_user.da_server,
                'da_username': current_user.da_username,
                'da_domain': current_user.da_domain
            }
        })

    except Exception as e:
        print(f"Error saving settings: {str(e)}")
        print(traceback.format_exc())
        db.session.rollback()
        return jsonify({
            'error': f'Failed to save settings: {str(e)}',
            'details': 'Check server logs for more information'
        }), 500

@settings_bp.route('/api/test-connection', methods=['POST'])
@login_required
def test_connection():
    """Test DirectAdmin connection - completely separate from saving"""
    try:
        data = request.json
        print(f"Testing connection for user: {current_user.username}")

        # Use provided credentials or current user's saved ones
        server = data.get('da_server') or current_user.da_server
        username = data.get('da_username') or current_user.da_username
        password = data.get('da_password') or current_user.get_da_password()

        if not all([server, username, password]):
            missing = []
            if not server: missing.append('server')
            if not username: missing.append('username')
            if not password: missing.append('password')

            return jsonify({
                'error': f'Missing credentials: {", ".join(missing)}',
                'missing': missing
            }), 400

        # Ensure server URL is properly formatted
        if not server.startswith(('http://', 'https://')):
            server = 'https://' + server

        # Test connection
        api = DirectAdminAPI(server, username, password)
        success, message = api.test_connection()

        if success:
            return jsonify({'success': True, 'message': message})
        else:
            return jsonify({'error': message, 'success': False}), 200  # Return 200 even on test failure

    except Exception as e:
        print(f"Test connection error: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'error': str(e), 'success': False}), 200  # Return 200 to avoid confusion

@settings_bp.route('/api/debug')
@login_required
def debug_info():
    """Debug endpoint to check user state"""
    return jsonify({
        'user': current_user.username,
        'has_encryption_key': bool(current_user.encryption_key),
        'has_da_config': current_user.has_da_config(),
        'da_server_configured': bool(current_user.da_server),
        'da_username_configured': bool(current_user.da_username),
        'da_password_configured': bool(current_user.da_password_encrypted),
        'da_domain_configured': bool(current_user.da_domain)
    })
