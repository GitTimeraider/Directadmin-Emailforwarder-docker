from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash
from app.models import db, User
import pyotp
import qrcode
import io
import base64

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        totp_token = request.form.get('totp_token', '')

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            if user.totp_enabled and not user.verify_totp(totp_token):
                flash('Invalid 2FA token', 'error')
                return redirect(url_for('auth.login'))

            login_user(user)
            return redirect(url_for('main.dashboard'))

        flash('Invalid credentials', 'error')

    return render_template('login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))

@auth_bp.route('/setup-2fa', methods=['GET', 'POST'])
@login_required
def setup_2fa():
    if request.method == 'POST':
        if 'enable' in request.form:
            secret = current_user.generate_totp_secret()
            current_user.totp_enabled = True
            db.session.commit()

            # Generate QR code
            qr = qrcode.QRCode(version=1, box_size=10, border=5)
            qr.add_data(current_user.get_totp_uri())
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")

            buf = io.BytesIO()
            img.save(buf, format='PNG')
            qr_code = base64.b64encode(buf.getvalue()).decode()

            return {'qr_code': qr_code, 'secret': secret}

        elif 'disable' in request.form:
            current_user.totp_enabled = False
            current_user.totp_secret = None
            db.session.commit()

    return redirect(url_for('main.dashboard'))
