import os
from datetime import timedelta

# Resolve project paths
BASE_APP_DIR = os.path.abspath(os.path.dirname(__file__))          # /app/app
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_APP_DIR, '..'))   # /app

# Data directory (where the sqlite db will live by default)
DEFAULT_DATA_DIR = os.path.join(PROJECT_ROOT, 'data')
DATA_DIR = os.environ.get('DATA_DIR', DEFAULT_DATA_DIR)
os.makedirs(DATA_DIR, exist_ok=True)

def _bool(env_name: str, default: bool) -> bool:
    val = os.environ.get(env_name)
    if val is None:
        return default
    return val.strip().lower() in ('1', 'true', 'yes', 'on')

class Config:
    # Core settings
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-this'

    # Default SQLite DB under /app/data (volume mount) unless DATABASE_URL provided
    _default_sqlite_path = os.path.join(DATA_DIR, 'users.db')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or f'sqlite:///{_default_sqlite_path}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Session configuration
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = os.environ.get('SESSION_COOKIE_SAMESITE', 'Lax')
    # Allow overriding secure flag for local HTTP testing (set SESSION_COOKIE_SECURE=false)
    SESSION_COOKIE_SECURE = _bool('SESSION_COOKIE_SECURE', default=False)
    
    # Session lifetime configuration - defaults to 12 hours for better user experience
    _session_hours = int(os.environ.get('SESSION_LIFETIME_HOURS', '12'))
    PERMANENT_SESSION_LIFETIME = timedelta(hours=_session_hours)
    
    # Ensure session cookies persist across browser restarts
    SESSION_COOKIE_NAME = 'da_emailforwarder_session'
    SESSION_COOKIE_MAX_AGE = _session_hours * 3600  # Convert hours to seconds
    
    # Refresh session on each request to prevent timeout during active use
    SESSION_REFRESH_EACH_REQUEST = True

    # JSON configuration
    JSON_AS_ASCII = False
    JSONIFY_PRETTYPRINT_REGULAR = True

    # Optional settings / environment
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    FLASK_ENV = os.environ.get('FLASK_ENV', 'production')

    # Expose data dir path for other modules if needed
    DATA_DIR = DATA_DIR

