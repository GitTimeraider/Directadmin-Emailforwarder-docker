from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from app.models import db
from app.directadmin_api import DirectAdminAPI
import traceback
import json

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
    """Save DirectAdmin settings"""
    print(f"\n=== SAVE ENDPOINT CALLED ===")
    print(f"Request method: {request.method}")
    print(f"Content-Type: {request.content_type}")
    print(f"Request headers: {dict(request.headers)}")

    # Check if request has JSON content type
    if not request.content_type or 'application/json' not in request.content_type:
        print(f"ERROR: Wrong content type: {request.content_type}")
        return jsonify({
            'error': 'Content-Type must be application/json',
            'received_content_type': request.content_type
        }), 400

    try:
        # Try to get JSON data
        try:
            data = request.get_json(force=True)  # Force parsing even if content-type is wrong
            if not data:
                print("ERROR: No JSON data in request body")
                return jsonify({'error': 'No JSON data provided'}), 400
        except Exception as json_error:
            print(f"ERROR: Failed to parse JSON: {json_error}")
            print(f"Request data: {request.data}")
            return jsonify({
                'error': 'Invalid JSON in request body',
                'details': str(json_error)
            }), 400

        print(f"Received data: {data}")
        print(f"Current user: {current_user.username}")

        # Validate required fields
        required_fields = ['da_server', 'da_username', 'da_domain']
        missing_fields = []

        for field in required_fields:
            if not data.get(field, '').strip():
                missing_fields.append(field)

        if missing_fields:
            print(f"Missing fields: {missing_fields}")
            return jsonify({
                'error': f'Missing required fields: {", ".join(missing_fields)}',
                'missing_fields': missing_fields
            }), 400

        # Ensure user has encryption key
        if not current_user.encryption_key:
            print("Generating encryption key")
            current_user.generate_encryption_key()

        # Clean and save the server URL
        server_url = data['da_server'].strip()
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
        try:
            db.session.commit()
            print("✓ Settings saved successfully")

            return jsonify({
                'success': True, 
                'message': 'Settings saved successfully!',
                'saved_data': {
                    'da_server': current_user.da_server,
                    'da_username': current_user.da_username,
                    'da_domain': current_user.da_domain
                }
            })

        except Exception as db_error:
            print(f"Database error: {db_error}")
            db.session.rollback()
            return jsonify({
                'error': 'Database error while saving',
                'details': str(db_error)
            }), 500

    except Exception as e:
        print(f"ERROR in update_da_config: {str(e)}")
        print(traceback.format_exc())
        db.session.rollback()
        return jsonify({
            'error': f'Failed to save settings: {str(e)}',
            'exception_type': type(e).__name__
        }), 500
