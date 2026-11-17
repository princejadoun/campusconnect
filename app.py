"""
Main entry point and application factory for CampusConnect.
Initializes Flask, SQLAlchemy, Flask-Login, and registers all team Blueprints.
"""

from datetime import datetime, timedelta
from flask import Flask, current_app
from flask_login import LoginManager
from models import Event, Registration, User, db
from routes.auth import auth_bp


def create_app(test_config: dict | None = None) -> Flask:
    """Creates and configures the Flask application instance."""
    app = Flask(__name__)

    app.config["SECRET_KEY"] = "campusconnect-dev-secret-key-2026"
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///campusconnect.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    if test_config:
        app.config.update(test_config)

    # Initialize database
    db.init_app(app)

    # Configure Flask-Login
    login_manager = LoginManager()
    login_manager.login_view = "auth.login"
    login_manager.login_message_category = "warning"
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id: str):
        return db.session.get(User, int(user_id))

    # Helper so base.html safely links to teammate Blueprints once merged
    @app.context_processor
    def inject_helpers():
        def endpoint_exists(endpoint_name: str) -> bool:
            return endpoint_name in current_app.view_functions

        return dict(endpoint_exists=endpoint_exists)

    # Register Member 1 Blueprint (Authentication & Profile)
    app.register_blueprint(auth_bp)

    # Register Member 2 Blueprint (Event Management)
    from routes.events import events_bp
    app.register_blueprint(events_bp)

    # -------------------------------------------------------------------------
    # TEAM HEAD INTEGRATION: Register teammate Blueprints below as PRs are merged
    # -------------------------------------------------------------------------
    # from routes.attendance import attendance_bp
    # app.register_blueprint(attendance_bp)
    #
    # from routes.certificates import certificates_bp
    # app.register_blueprint(certificates_bp)
    #
    # from routes.admin import admin_bp
    # app.register_blueprint(admin_bp)

    with app.app_context():
        db.create_all()
        if not app.config.get("TESTING"):
            seed_initial_data()

    return app


def seed_initial_data() -> None:
    """Seeds demo admin/student accounts and sample events if the database is empty."""
    if User.query.first() is not None:
        return

    admin = User(name="Prof. Admin Coordinator", email="admin@campusconnect.edu", role="admin")
    admin.set_password("admin123")

    student1 = User(name="Aarav Sharma", email="aarav@campusconnect.edu", role="student")
    student1.set_password("student123")

    student2 = User(name="Priya Verma", email="priya@campusconnect.edu", role="student")
    student2.set_password("student123")

    db.session.add_all([admin, student1, student2])
    db.session.flush()

    now = datetime.utcnow()
    event1 = Event(
        title="AI & Python Hackathon 2026",
        description="Build practical AI-powered Python prototypes in teams of up to 4 students.",
        venue="Main Auditorium, Block A",
        event_date=now + timedelta(days=7),
        reg_deadline=now + timedelta(days=5),
        max_seats=120,
        created_by=admin.id,
    )
    event2 = Event(
        title="Cloud & Cybersecurity Workshop",
        description="Hands-on session covering API security, authentication, and deployment.",
        venue="Computer Lab 3, Block C",
        event_date=now + timedelta(days=12),
        reg_deadline=now + timedelta(days=10),
        max_seats=60,
        created_by=admin.id,
    )

    db.session.add_all([event1, event2])
    db.session.flush()

    # Pre-register Aarav for Event 1 so QR & Certificate teammates can test right away
    sample_reg = Registration(user_id=student1.id, event_id=event1.id)
    db.session.add(sample_reg)
    db.session.commit()


if __name__ == "__main__":
    application = create_app()
    application.run(debug=True)