from flask import Flask
from flask_login import LoginManager
from .models import db, User
from config import Config

login_manager = LoginManager()


def brl(value):
    """Format value as Brazilian Real: R$ 1.234,56"""
    try:
        v = float(value)
        # Format with dot as thousands separator and comma as decimal
        formatted = f"{abs(v):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
        sign = '-' if v < 0 else ''
        return f"R$ {sign}{formatted}"
    except (TypeError, ValueError):
        return "R$ 0,00"


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Por favor, faca login para continuar.'
    login_manager.login_message_category = 'warning'

    # Register BRL Jinja2 filter
    app.jinja_env.filters['brl'] = brl

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    from .routes.auth import auth_bp
    from .routes.dashboard import dashboard_bp
    from .routes.transactions import transactions_bp
    from .routes.budget import budget_bp
    from .routes.bills import bills_bp
    from .routes.reports import reports_bp
    from .routes.categories import categories_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(transactions_bp)
    app.register_blueprint(budget_bp)
    app.register_blueprint(bills_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(categories_bp)

    with app.app_context():
        db.create_all()

    return app
