#!/usr/bin/env python3
from app.main import create_app
from app.models import db, User

app = create_app()

with app.app_context():
    print("\n=== User Debug Info ===")
    users = User.query.all()

    for user in users:
        print(f"\nUser: {user.username}")
        print(f"  ID: {user.id}")
        print(f"  Admin: {user.is_admin}")
        print(f"  Has encryption key: {bool(user.encryption_key)}")
        print(f"  DA Server: {user.da_server}")
        print(f"  DA Username: {user.da_username}")
        print(f"  Has DA Password: {bool(user.da_password_encrypted)}")
        print(f"  DA Domain: {user.da_domain}")

        # Fix missing encryption keys
        if not user.encryption_key:
            print("  [!] Generating missing encryption key...")
            user.generate_encryption_key()
            db.session.commit()
            print("  [✓] Encryption key generated")

print("\n=== Debug complete ===")
