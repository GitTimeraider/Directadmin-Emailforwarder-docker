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
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    totp_secret = db.Column(db.String(32), nullable=True)
    totp_enabled = db.Column(db.Boolean, default=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)

    # DirectAdmin Settings (encrypted)
    da_server = db.Column(db.String(255), nullable=True)
    da_username = db.Column(db.String(255), nullable=True)
    da_password_encrypted = db.Column(db.Text, nullable=True)
    da_domain = db.Column(db.String(255), nullable=True)

    # Encryption key for DA password (unique per user)
    encryption_key = db.Column(db.String(255), nullable=True)

    def __init__(self, **kwargs):
        super(User, self).__init__(**kwargs)
        # Generate encryption key for this user
        if not self.encryption_key:
            self.encryption_key = Fernet.generate_key().decode()

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def set_da_password(self, password):
        """Encrypt and store DirectAdmin password"""
        if password:
            f = Fernet(self.encryption_key.encode())
            self.da_password_encrypted = f.encrypt(password.encode()).decode()
        else:
            self.da_password_encrypted = None

    def get_da_password(self):
        """Decrypt and return DirectAdmin password"""
        if self.da_password_encrypted and self.encryption_key:
            try:
                f = Fernet(self.encryption_key.encode())
                return f.decrypt(self.da_password_encrypted.encode()).decode()
            except:
                return None
        return None

    def has_da_config(self):
        """Check if user has configured DirectAdmin settings"""
        return all([self.da_server, self.da_username, self.da_password_encrypted, self.da_domain])

    def generate_totp_secret(self):
        secret = base64.b32encode(os.urandom(10)).decode('utf-8')
        self.totp_secret = secret
        return secret

    def verify_totp(self, token):
        if not self.totp_enabled or not self.totp_secret:
            return True
        totp = pyotp.TOTP(self.totp_secret)
        return totp.verify(token, valid_window=1)

    def get_totp_uri(self):
        return pyotp.totp.TOTP(self.totp_secret).provisioning_uri(
            name=self.username,
            issuer_name='DirectAdmin Email Forwarder'
        )

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'is_admin': self.is_admin,
            'totp_enabled': self.totp_enabled,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'has_da_config': self.has_da_config()
        }
