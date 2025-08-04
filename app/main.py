from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_login import LoginManager, login_required, current_user
from app.models import db, User
from app.auth import auth_bp
from app.directadmin_api import DirectAdminAPI
from app.config import Config
import os

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)

    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    app.register_blueprint(auth_bp)

    with app.app_context():
        db.create_all()
        # Create default user if none exists
        if User.query.count() == 0:
            user = User(username='admin')
            user.set_password('changeme')
            db.session.add(user)
            db.session.commit()

    @app.route('/')
    @login_required
    def index():
        return redirect(url_for('dashboard'))

    @app.route('/dashboard')
    @login_required
    def dashboard():
        return render_template('dashboard.html', domain=Config.DA_DOMAIN)

    @app.route('/api/email-accounts')
    @login_required
    def get_email_accounts():
        api = DirectAdminAPI(Config.DA_SERVER, Config.DA_USERNAME, Config.DA_PASSWORD)
        accounts = api.get_email_accounts(Config.DA_DOMAIN)
        return jsonify(accounts)

    @app.route('/api/forwarders')
    @login_required
    def get_forwarders():
        api = DirectAdminAPI(Config.DA_SERVER, Config.DA_USERNAME, Config.DA_PASSWORD)
        forwarders = api.get_forwarders(Config.DA_DOMAIN)
        return jsonify(forwarders)

    @app.route('/api/forwarders', methods=['POST'])
    @login_required
    def create_forwarder():
        data = request.json
        api = DirectAdminAPI(Config.DA_SERVER, Config.DA_USERNAME, Config.DA_PASSWORD)
        success = api.create_forwarder(Config.DA_DOMAIN, data['alias'], data['destination'])
        return jsonify({'success': success})

    @app.route('/api/forwarders/<alias>', methods=['DELETE'])
    @login_required
    def delete_forwarder(alias):
        api = DirectAdminAPI(Config.DA_SERVER, Config.DA_USERNAME, Config.DA_PASSWORD)
        success = api.delete_forwarder(Config.DA_DOMAIN, alias)
        return jsonify({'success': success})

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)
