from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from functools import wraps
from app.models import db, User
from werkzeug.security import generate_password_hash
import secrets

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

def admin_required(f):
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin:
            flash('You need administrator privileges to access this page.', 'error')
            return redirect(url_for('main.dashboard'))
        return f(*args, **kwargs)
    return decorated_function

@admin_bp.route('/users')
@admin_required
def users():
    return render_template('admin/users.html')

@admin_bp.route('/api/users')
@admin_required
def get_users():
    users = User.query.all()
    return jsonify([user.to_dict() for user in users])

@admin_bp.route('/api/users', methods=['POST'])
@admin_required
def create_user():
    data = request.json

    # Validate input
    if not data.get('username') or not data.get('password'):
        return jsonify({'error': 'Username and password are required'}), 400

    # Check if username exists
    if User.query.filter_by(username=data['username']).first():
        return jsonify({'error': 'Username already exists'}), 400

    # Create new user
    user = User(
        username=data['username'],
        is_admin=data.get('is_admin', False)
    )
    user.set_password(data['password'])

    db.session.add(user)
    db.session.commit()

    return jsonify({
        'success': True,
        'user': user.to_dict()
    })

@admin_bp.route('/api/users/<int:user_id>', methods=['PUT'])
@admin_required
def update_user(user_id):
    user = User.query.get_or_404(user_id)
    data = request.json

    # Prevent removing last admin
    if user.is_admin and not data.get('is_admin', False):
        admin_count = User.query.filter_by(is_admin=True).count()
        if admin_count <= 1:
            return jsonify({'error': 'Cannot remove last administrator'}), 400

    # Update username if provided and different
    if data.get('username') and data['username'] != user.username:
        if User.query.filter_by(username=data['username']).first():
            return jsonify({'error': 'Username already exists'}), 400
        user.username = data['username']

    # Update password if provided
    if data.get('password'):
        user.set_password(data['password'])

    # Update admin status
    if 'is_admin' in data:
        user.is_admin = data['is_admin']

    # Reset 2FA if requested
    if data.get('reset_2fa'):
        user.totp_enabled = False
        user.totp_secret = None

    db.session.commit()

    return jsonify({
        'success': True,
        'user': user.to_dict()
    })

@admin_bp.route('/api/users/<int:user_id>', methods=['DELETE'])
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)

    # Prevent self-deletion
    if user.id == current_user.id:
        return jsonify({'error': 'Cannot delete your own account'}), 400

    # Prevent removing last admin
    if user.is_admin:
        admin_count = User.query.filter_by(is_admin=True).count()
        if admin_count <= 1:
            return jsonify({'error': 'Cannot delete last administrator'}), 400

    db.session.delete(user)
    db.session.commit()

    return jsonify({'success': True})

@admin_bp.route('/api/users/<int:user_id>/generate-password')
@admin_required
def generate_password(user_id):
    # Generate a secure random password
    password = secrets.token_urlsafe(12)
    return jsonify({'password': password})
