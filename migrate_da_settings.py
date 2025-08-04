from app.main import create_app
from app.models import db, User
from app.config import Config

app = create_app()

with app.app_context():
    # Add new columns to existing users
    users = User.query.all()

    # If global settings exist, migrate them to admin user
    admin = User.query.filter_by(username='admin').first()
    if admin and hasattr(Config, 'DA_SERVER'):
        print("Migrating global DirectAdmin settings to admin user...")
        admin.da_server = Config.DA_SERVER
        admin.da_username = Config.DA_USERNAME
        admin.da_domain = Config.DA_DOMAIN

        # Generate encryption key if not exists
        if not admin.encryption_key:
            from cryptography.fernet import Fernet
            admin.encryption_key = Fernet.generate_key().decode()

        # Encrypt and store password
        if hasattr(Config, 'DA_PASSWORD'):
            admin.set_da_password(Config.DA_PASSWORD)

    db.session.commit()
    print("Migration completed!")
