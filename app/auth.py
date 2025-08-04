from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify, session
from flask_login import login_user, logout_user, login_required, current_user
from app.models import db, User
import pyotp
import qrcode
import io
import base64
from datetime import datetime

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        totp_code = request.form.get('totp_code', '')

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            # Check TOTP if enabled
            if user.totp_enabled:
                if not totp_code:
                    flash('2FA code required', 'error')
                    return render_template('login.html', require_totp=True, username=username)

                if not user.verify_totp(totp_code):
                    flash('Invalid 2FA code', 'error')
                    return render_template('login.html', require_totp=True, username=username)

            # Update last login
            user.last_login = datetime.utcnow()
            db.session.commit()

            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('index'))
        else:
            flash('Invalid username or password', 'error')

    return render_template('login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))

@auth_bp.route('/profile')
@login_required
def profile():
    return render_template('profile.html', user=current_user)

@auth_bp.route('/setup-2fa', methods=['GET', 'POST'])
@login_required
def setup_2fa():
    """Setup 2FA for user"""
    try:
        print(f"Setup 2FA called for user: {current_user.username}")

        if request.method == 'POST':
            # Verify the TOTP code
            token = request.form.get('token')
            print(f"Verifying token: {token}")

            if not token:
                flash('Please enter the verification code', 'error')
                return redirect(url_for('auth.setup_2fa'))

            # Verify the token
            if current_user.verify_totp(token):
                current_user.totp_enabled = True
                db.session.commit()
                flash('2FA has been enabled successfully!', 'success')
                print(f"2FA enabled for user: {current_user.username}")
                return redirect(url_for('auth.profile'))
            else:
                flash('Invalid verification code. Please try again.', 'error')
                print(f"Invalid token for user: {current_user.username}")

        # Generate new secret if needed
        if not current_user.totp_secret:
            print("Generating new TOTP secret")
            current_user.generate_totp_secret()
            db.session.commit()

        # Generate QR code
        print("Generating QR code")
        qr_code = generate_qr_code(current_user)

        return render_template('setup_2fa.html', qr_code=qr_code, user=current_user)

    except Exception as e:
        print(f"ERROR in setup_2fa: {str(e)}")
        import traceback
        traceback.print_exc()
        flash('An error occurred while setting up 2FA', 'error')
        return redirect(url_for('auth.profile'))

@auth_bp.route('/disable-2fa', methods=['POST'])
@login_required
def disable_2fa():
    """Disable 2FA for user"""
    try:
        print(f"Disabling 2FA for user: {current_user.username}")

        current_user.totp_enabled = False
        current_user.totp_secret = None
        db.session.commit()

        flash('2FA has been disabled', 'success')
        return redirect(url_for('auth.profile'))

    except Exception as e:
        print(f"ERROR in disable_2fa: {str(e)}")
        flash('An error occurred while disabling 2FA', 'error')
        return redirect(url_for('auth.profile'))

def generate_qr_code(user):
    """Generate QR code for TOTP setup"""
    try:
        # Get the provisioning URI
        uri = user.get_totp_uri()
        print(f"TOTP URI: {uri}")

        # Generate QR code
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(uri)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")

        # Convert to base64
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        buf.seek(0)

        qr_code = base64.b64encode(buf.getvalue()).decode()
        return f"data:image/png;base64,{qr_code}"

    except Exception as e:
        print(f"ERROR generating QR code: {str(e)}")
        raise
