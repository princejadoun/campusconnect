"""
Database models for CampusConnect using Flask-SQLAlchemy ORM.
Defines User, Event, and Registration tables along with helper methods.
"""

import uuid
from datetime import datetime
from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash

db = SQLAlchemy()


class User(UserMixin, db.Model):
    """Represents a student or administrator in CampusConnect."""

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="student")  # 'student' or 'admin'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    events_created = db.relationship("Event", backref="creator", lazy=True)
    registrations = db.relationship(
        "Registration", backref="student", lazy=True, cascade="all, delete-orphan"
    )

    def set_password(self, raw_password: str) -> None:
        """Hashes and stores a plain-text password securely."""
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password: str) -> bool:
        """Verifies a plain-text password against the stored hash."""
        return check_password_hash(self.password_hash, raw_password)

    def is_admin(self) -> bool:
        """Returns True if the user has administrator privileges."""
        return self.role == "admin"

    def __repr__(self) -> str:
        return f"<User {self.email} ({self.role})>"


class Event(db.Model):
    """Represents a college event created by an administrator."""

    __tablename__ = "events"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=False)
    venue = db.Column(db.String(150), nullable=False)
    event_date = db.Column(db.DateTime, nullable=False)
    reg_deadline = db.Column(db.DateTime, nullable=False)
    max_seats = db.Column(db.Integer, nullable=False, default=100)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    registrations = db.relationship(
        "Registration", backref="event", lazy=True, cascade="all, delete-orphan"
    )

    def registered_count(self) -> int:
        """Returns total number of students registered for this event."""
        return len(self.registrations)

    def seats_remaining(self) -> int:
        """Returns how many seats are still available."""
        return max(0, self.max_seats - self.registered_count())

    def is_registration_open(self) -> bool:
        """Checks if seats are available and the registration deadline has not passed."""
        return self.seats_remaining() > 0 and datetime.utcnow() <= self.reg_deadline

    def __repr__(self) -> str:
        return f"<Event {self.title}>"


class Registration(db.Model):
    """Links a Student to an Event, storing QR pass and attendance/certificate status."""

    __tablename__ = "registrations"
    __table_args__ = (
        db.UniqueConstraint("user_id", "event_id", name="uq_user_event_registration"),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    event_id = db.Column(db.Integer, db.ForeignKey("events.id"), nullable=False)

    # Unique token encoded inside the student's QR entry pass
    qr_token = db.Column(
        db.String(64), unique=True, nullable=False, default=lambda: str(uuid.uuid4())
    )

    # Attendance tracking fields (prevents duplicate QR scans)
    attended = db.Column(db.Boolean, nullable=False, default=False)
    attended_at = db.Column(db.DateTime, nullable=True)

    # Unique verification ID printed on the downloadable PDF certificate
    cert_code = db.Column(
        db.String(32),
        unique=True,
        nullable=False,
        default=lambda: f"CC-{uuid.uuid4().hex[:8].upper()}",
    )

    registered_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<Registration user={self.user_id} event={self.event_id} attended={self.attended}>"