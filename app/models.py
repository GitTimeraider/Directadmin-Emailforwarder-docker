from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import pyotp
import base64
import os

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    totp_secret = db.Column(db.String(32), nullable=True)
    totp_enabled = db.Column(db.Boolean, default=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

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
