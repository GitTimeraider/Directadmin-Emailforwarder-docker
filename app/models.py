from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from cryptography.fernet import Fernet
import pyotp
import base64
import os
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    # Primary fields
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)

    # 2FA/TOTP fields
    totp_secret = db.Column(db.String(32), nullable=True)
    totp_enabled = db.Column(db.Boolean, default=False)

    # Admin and metadata
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)

    # DirectAdmin Settings (per-user)
    da_server = db.Column(db.String(255), nullable=True)
    da_username = db.Column(db.String(255), nullable=True)
    da_password_encrypted = db.Column(db.Text, nullable=True)
    da_domain = db.Column(db.String(255), nullable=True)

    # User preferences (added in migration - may not exist in older databases)
    theme_preference = db.Column(db.String(20), default='light', nullable=True)  # 'light' or 'dark'

    # Unique encryption key per user for DA password
    encryption_key = db.Column(db.String(255), nullable=True)

    def get_theme_preference(self):
        """Safely get theme preference, handling missing column"""
        try:
            return self.theme_preference or 'light'
        except Exception:
            # Column doesn't exist yet, return default
            return 'light'
    
    def set_theme_preference(self, theme):
        """Safely set theme preference, handling missing column"""
        try:
            if theme in ['light', 'dark']:
                self.theme_preference = theme
                return True
        except Exception:
            # Column doesn't exist yet, ignore
            pass
        return False

    def __init__(self, **kwargs):
        """Initialize user with encryption key"""
        super(User, self).__init__(**kwargs)
        # Generate encryption key for this user if not provided
        if not self.encryption_key:
            self.generate_encryption_key()

    def __repr__(self):
        return f'<User {self.username}>'

    # ===== Encryption Key Management =====

    def generate_encryption_key(self):
        """Generate a new encryption key for this user"""
        self.encryption_key = Fernet.generate_key().decode()

    # ===== Password Management =====

    def set_password(self, password):
        """Hash and store user login password"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Verify user login password"""
        return check_password_hash(self.password_hash, password)

    # ===== DirectAdmin Password Management =====

    def set_da_password(self, password):
        """Encrypt and store DirectAdmin password"""
        if not self.encryption_key:
            self.generate_encryption_key()

        if password:
            try:
                f = Fernet(self.encryption_key.encode())
                self.da_password_encrypted = f.encrypt(password.encode()).decode()
            except Exception as e:
                print(f"Error encrypting DA password: {e}")
                raise
        else:
            self.da_password_encrypted = None

    def get_da_password(self):
        """Decrypt and return DirectAdmin password"""
        if self.da_password_encrypted and self.encryption_key:
            try:
                f = Fernet(self.encryption_key.encode())
                return f.decrypt(self.da_password_encrypted.encode()).decode()
            except Exception as e:
                print(f"Error decrypting DA password: {e}")
                return None
        return None

    def has_da_config(self):
        """Check if user has configured DirectAdmin settings"""
        return all([
            self.da_server, 
            self.da_username, 
            self.da_password_encrypted, 
            self.da_domain
        ])

    # ===== TOTP/2FA Management =====

    def generate_totp_secret(self):
        """Generate a new TOTP secret for 2FA"""
        # Use pyotp's random_base32 for proper secret generation
        secret = pyotp.random_base32()
        self.totp_secret = secret
        print(f"Generated TOTP secret for user {self.username}")
        return secret

    def verify_totp(self, token):
        """Verify a TOTP token"""
        if not self.totp_enabled or not self.totp_secret:
            return True  # If 2FA not enabled, always pass

        if not token:
            return False

        try:
            totp = pyotp.TOTP(self.totp_secret)
            # Allow 1 window before/after (30 seconds tolerance)
            valid = totp.verify(token, valid_window=1)
            print(f"TOTP verification for {self.username}: {valid}")
            return valid
        except Exception as e:
            print(f"TOTP verification error for {self.username}: {e}")
            return False

    def get_totp_uri(self):
        """Get provisioning URI for QR code generation"""
        if not self.totp_secret:
            raise ValueError("No TOTP secret set")

        return pyotp.totp.TOTP(self.totp_secret).provisioning_uri(
            name=self.username,
            issuer_name='DirectAdmin Email Forwarder'
        )

    def get_totp_qr_uri(self):
        """Alias for get_totp_uri for compatibility"""
        return self.get_totp_uri()

    # ===== Utility Methods =====

    def to_dict(self):
        """Convert user to dictionary (for API responses)"""
        return {
            'id': self.id,
            'username': self.username,
            'is_admin': self.is_admin,
            'totp_enabled': self.totp_enabled,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'has_da_config': self.has_da_config(),
            'da_server': self.da_server,
            'da_username': self.da_username,
            'da_domain': self.da_domain
            # Never include passwords or secrets in dict!
        }

    def update_last_login(self):
        """Update last login timestamp"""
        self.last_login = datetime.utcnow()

    def reset_totp(self):
        """Reset/disable TOTP for this user"""
        self.totp_enabled = False
        self.totp_secret = None
