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
    try:
        # Ensure we have JSON data
        if not request.is_json:
            return jsonify({'error': 'Content-Type must be application/json'}), 400

        data = request.json
        print(f"Received settings update: {data}")  # Debug log

        # Validate required fields
        required_fields = ['da_server', 'da_username', 'da_domain']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field} is required'}), 400

        # Ensure user has encryption key
        if not current_user.encryption_key:
            current_user.generate_encryption_key()

        # Update DirectAdmin settings
        current_user.da_server = data['da_server'].rstrip('/')
        current_user.da_username = data['da_username']
        current_user.da_domain = data['da_domain']

        # Only update password if provided
        if data.get('da_password'):
            print("Setting new DA password")  # Debug log
            current_user.set_da_password(data['da_password'])

        db.session.commit()
        print("Settings saved successfully")  # Debug log

        return jsonify({'success': True, 'message': 'DirectAdmin settings updated successfully'})

    except Exception as e:
        print(f"Error updating settings: {str(e)}")  # Debug log
        print(traceback.format_exc())  # Full traceback
        db.session.rollback()
        return jsonify({'error': f'Failed to save settings: {str(e)}'}), 500
        
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

@settings_bp.route('/api/test-connection', methods=['POST'])
@login_required
def test_connection():
    """Test DirectAdmin connection with provided credentials"""
    try:
        # Ensure we have JSON data
        if not request.is_json:
            return jsonify({'error': 'Content-Type must be application/json'}), 400

        data = request.json
        print(f"Testing connection with: {data.get('da_server')}")  # Debug log

        # Use provided credentials or current user's
        server = data.get('da_server') or current_user.da_server
        username = data.get('da_username') or current_user.da_username
        password = data.get('da_password') or current_user.get_da_password()

        if not all([server, username, password]):
            return jsonify({'error': 'Missing credentials'}), 400

        # Ensure server URL is properly formatted
        if not server.startswith(('http://', 'https://')):
            server = 'https://' + server

        # Test connection
        api = DirectAdminAPI(server, username, password)
        success, message = api.test_connection()

        if success:
            return jsonify({'success': True, 'message': message})
        else:
            return jsonify({'error': message}), 400

    except Exception as e:
        print(f"Test connection error: {str(e)}")  # Debug log
        print(traceback.format_exc())  # Full traceback
        return jsonify({'error': str(e)}), 500
