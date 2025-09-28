from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from cryptography.fernet import Fernet
import pyotp
import base64
import os
from datetime import datetime

db = SQLAlchemy()

class UserDomain(db.Model):
    """Model for storing multiple domains per user"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    domain = db.Column(db.String(255), nullable=False)
    order_index = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship back to user
    user = db.relationship('User', backref=db.backref('domains', lazy=True, order_by='UserDomain.order_index'))
    
    def __repr__(self):
        return f'<UserDomain {self.domain} for user {self.user_id}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'domain': self.domain,
            'order_index': self.order_index,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

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

    # User preferences
    theme_preference = db.Column(db.String(20), default='light', nullable=True)

    # Unique encryption key per user for DA password
    encryption_key = db.Column(db.String(255), nullable=True)

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
            self.da_password_encrypted
        ]) and len(self.get_domains()) > 0

    # ===== Domain Management =====
    
    def get_domains(self):
        """Get all domains for this user in order"""
        return [d.domain for d in self.domains]
    
    def get_first_domain(self):
        """Get the first domain (default) for this user"""
        domains = self.get_domains()
        return domains[0] if domains else None
    
    def add_domain(self, domain):
        """Add a new domain for this user"""
        # Check if domain already exists
        existing = UserDomain.query.filter_by(user_id=self.id, domain=domain).first()
        if existing:
            return False, "Domain already exists"
        
        # Get next order index
        max_order = db.session.query(db.func.max(UserDomain.order_index)).filter_by(user_id=self.id).scalar()
        next_order = (max_order or -1) + 1
        
        # Create new domain
        user_domain = UserDomain(
            user_id=self.id,
            domain=domain,
            order_index=next_order
        )
        
        db.session.add(user_domain)
        return True, "Domain added successfully"
    
    def remove_domain(self, domain):
        """Remove a domain for this user"""
        user_domain = UserDomain.query.filter_by(user_id=self.id, domain=domain).first()
        if not user_domain:
            return False, "Domain not found"
        
        db.session.delete(user_domain)
        
        # Reorder remaining domains
        remaining_domains = UserDomain.query.filter_by(user_id=self.id).filter(
            UserDomain.order_index > user_domain.order_index
        ).all()
        
        for domain_obj in remaining_domains:
            domain_obj.order_index -= 1
        
        return True, "Domain removed successfully"
    
    def reorder_domains(self, domain_list):
        """Reorder domains based on provided list"""
        for i, domain in enumerate(domain_list):
            user_domain = UserDomain.query.filter_by(user_id=self.id, domain=domain).first()
            if user_domain:
                user_domain.order_index = i
        
        return True, "Domains reordered successfully"

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
            'da_domain': self.da_domain,  # Keep for backward compatibility
            'domains': self.get_domains()
            # Never include passwords or secrets in dict!
        }

    def update_last_login(self):
        """Update last login timestamp"""
        self.last_login = datetime.utcnow()

    def reset_totp(self):
        """Reset/disable TOTP for this user"""
        self.totp_enabled = False
        self.totp_secret = None
