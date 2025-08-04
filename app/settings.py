from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from app.models import db
from app.directadmin_api import DirectAdminAPI

settings_bp = Blueprint('settings', __name__, url_prefix='/settings')

@settings_bp.route('/')
@login_required
def index():
    return render_template('settings.html')

@settings_bp.route('/api/da-config', methods=['GET'])
@login_required
def get_da_config():
    return jsonify({
        'da_server': current_user.da_server or '',
        'da_username': current_user.da_username or '',
        'da_domain': current_user.da_domain or '',
        'has_password': bool(current_user.da_password_encrypted)
    })

@settings_bp.route('/api/da-config', methods=['POST'])
@login_required
def update_da_config():
    data = request.json

    # Validate required fields
    required_fields = ['da_server', 'da_username', 'da_domain']
    for field in required_fields:
        if not data.get(field):
            return jsonify({'error': f'{field} is required'}), 400

    # Update DirectAdmin settings
    current_user.da_server = data['da_server'].rstrip('/')
    current_user.da_username = data['da_username']
    current_user.da_domain = data['da_domain']

    # Only update password if provided
    if data.get('da_password'):
        current_user.set_da_password(data['da_password'])

    db.session.commit()

    return jsonify({'success': True, 'message': 'DirectAdmin settings updated successfully'})

@settings_bp.route('/api/test-connection', methods=['POST'])
@login_required
def test_connection():
    """Test DirectAdmin connection with provided credentials"""
    data = request.json

    try:
        # Use provided credentials or current user's
        server = data.get('da_server') or current_user.da_server
        username = data.get('da_username') or current_user.da_username
        password = data.get('da_password') or current_user.get_da_password()

        if not all([server, username, password]):
            return jsonify({'error': 'Missing credentials'}), 400

        # Test connection
        api = DirectAdminAPI(server, username, password)
        # Try to get domains as a test
        response = api._make_request('API_SHOW_DOMAINS')

        if response.status_code == 200:
            return jsonify({'success': True, 'message': 'Connection successful!'})
        else:
            return jsonify({'error': 'Connection failed'}), 400

    except Exception as e:
        return jsonify({'error': str(e)}), 500
