import os

class Config:
    # Core settings
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-this'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///users.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Session configuration
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_SECURE = False  # Set to True if using HTTPS
    PERMANENT_SESSION_LIFETIME = 3600  # 1 hour

    # JSON configuration
    JSON_AS_ASCII = False
    JSONIFY_PRETTYPRINT_REGULAR = True

    # Optional settings
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    FLASK_ENV = os.environ.get('FLASK_ENV', 'production')

