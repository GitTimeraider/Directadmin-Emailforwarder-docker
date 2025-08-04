from app.main import create_app
from app.models import db, User

app = create_app()

with app.app_context():
    # Add is_admin column to existing users
    users = User.query.all()
    for user in users:
        if not hasattr(user, 'is_admin'):
            user.is_admin = user.username == 'admin'  # Make 'admin' user an admin

    db.session.commit()
    print("Migration completed. Admin flags added to users.")
