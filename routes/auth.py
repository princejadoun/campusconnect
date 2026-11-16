"""
Authentication, profile management, and student notification routes.
Owned by Member 1 (Team Head).
"""

from datetime import datetime
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy.exc import SQLAlchemyError
from models import Event, Registration, User, db

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/")
def index():
    """Landing page showing upcoming campus events preview."""
    upcoming_events = (
        Event.query.filter(Event.event_date >= datetime.utcnow())
        .order_by(Event.event_date.asc())
        .limit(3)
        .all()
    )
    return render_template("auth/profile.html", upcoming_events=upcoming_events)


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    """Handles new student account registration."""
    if current_user.is_authenticated:
        return redirect(url_for("auth.profile"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not name or not email or not password:
            flash("All fields are required.", "danger")
            return render_template("auth/register.html")

        if len(password) < 6:
            flash("Password must be at least 6 characters long.", "danger")
            return render_template("auth/register.html")

        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash("An account with this email already exists.", "warning")
            return render_template("auth/register.html")

        try:
            new_student = User(name=name, email=email, role="student")
            new_student.set_password(password)
            db.session.add(new_student)
            db.session.commit()

            flash("Account created successfully! Please log in.", "success")
            return redirect(url_for("auth.login"))
        except SQLAlchemyError:
            db.session.rollback()
            flash("Database error during registration. Please try again.", "danger")

    return render_template("auth/register.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """Authenticates students and administrators."""
    if current_user.is_authenticated:
        return redirect(url_for("auth.profile"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user)
            flash(f"Welcome back, {user.name}!", "success")
            next_page = request.args.get("next")
            return redirect(next_page or url_for("auth.profile"))

        flash("Invalid email or password.", "danger")

    return render_template("auth/login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    """Logs out the current user."""
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))


@auth_bp.route("/profile")
@login_required
def profile():
    """Displays user dashboard, registered events, and reminders/notifications."""
    my_registrations = (
        Registration.query.filter_by(user_id=current_user.id)
        .order_by(Registration.registered_at.desc())
        .all()
    )
    upcoming_events = (
        Event.query.filter(Event.event_date >= datetime.utcnow())
        .order_by(Event.event_date.asc())
        .limit(4)
        .all()
    )
    return render_template(
        "auth/profile.html",
        registrations=my_registrations,
        upcoming_events=upcoming_events,
    )