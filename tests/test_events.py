"""
Automated Pytest suite for Member 2: Event Management module.
Tests:
- browse(): catalog listing, remaining seat counts, and search query filtering.
- event_detail(): event viewing, registration status, remaining seats.
- create_event(): admin restriction, validation rules (dates, seats, empty fields), successful creation.
- delete_event(): admin restriction, cascading delete of event and registrations.
- register_event(): login required, successful registration, duplicate blocking, full event blocking, past deadline blocking.
"""

from datetime import datetime, timedelta
import pytest
from app import create_app
from models import Event, Registration, User, db


@pytest.fixture
def app():
    """Configures an in-memory SQLite Flask application for isolated testing."""
    application = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "WTF_CSRF_ENABLED": False,
        "SECRET_KEY": "test-secret",
    })

    with application.app_context():
        db.create_all()

        # Seed admin
        admin = User(name="Admin User", email="admin@test.edu", role="admin")
        admin.set_password("admin123")

        # Seed students
        student1 = User(name="Student One", email="student1@test.edu", role="student")
        student1.set_password("student123")

        student2 = User(name="Student Two", email="student2@test.edu", role="student")
        student2.set_password("student123")

        db.session.add_all([admin, student1, student2])
        db.session.commit()

        # Seed test events
        now = datetime.utcnow()

        # Open event with available seats
        event_open = Event(
            title="Open Tech Summit",
            description="A summit on emerging tech.",
            venue="Hall A",
            event_date=now + timedelta(days=10),
            reg_deadline=now + timedelta(days=8),
            max_seats=50,
            created_by=admin.id,
        )

        # Full event (max_seats = 1, will have 1 registration)
        event_full = Event(
            title="Exclusive Workshop",
            description="Hands-on coding lab.",
            venue="Lab 101",
            event_date=now + timedelta(days=5),
            reg_deadline=now + timedelta(days=4),
            max_seats=1,
            created_by=admin.id,
        )

        # Expired event (deadline in the past)
        event_expired = Event(
            title="Past Registration Webinar",
            description="Online seminar whose registration deadline has passed.",
            venue="Online Zoom",
            event_date=now + timedelta(days=2),
            reg_deadline=now - timedelta(hours=1),
            max_seats=100,
            created_by=admin.id,
        )

        db.session.add_all([event_open, event_full, event_expired])
        db.session.commit()

        # Register student1 to event_full to make it 100% full
        reg_full = Registration(user_id=student1.id, event_id=event_full.id)
        db.session.add(reg_full)
        db.session.commit()

        yield application

        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def login(client, email, password):
    """Helper to authenticate a user session."""
    return client.post(
        "/login",
        data={"email": email, "password": password},
        follow_redirects=True,
    )


# -----------------------------------------------------------------------------
# 1. Tests for browse()
# -----------------------------------------------------------------------------
def test_browse_events_displays_all_and_seats(client):
    """Test browse page lists events and shows remaining seats."""
    response = client.get("/events/")
    assert response.status_code == 200
    html = response.data.decode("utf-8")
    assert "Open Tech Summit" in html
    assert "Exclusive Workshop" in html
    assert "Past Registration Webinar" in html
    assert "seats left" in html


def test_browse_search_query_matching(client):
    """Test searching by title or venue filters events properly."""
    response = client.get("/events/?q=Summit")
    assert response.status_code == 200
    html = response.data.decode("utf-8")
    assert "Open Tech Summit" in html
    assert "Exclusive Workshop" not in html

    # Search by venue
    response_venue = client.get("/events/?q=Lab 101")
    assert response_venue.status_code == 200
    html_venue = response_venue.data.decode("utf-8")
    assert "Exclusive Workshop" in html_venue
    assert "Open Tech Summit" not in html_venue


def test_browse_search_query_no_results(client):
    """Test search with no matches shows empty state."""
    response = client.get("/events/?q=NonExistentKeywordXYZ")
    assert response.status_code == 200
    html = response.data.decode("utf-8")
    assert "No Events Found" in html


# -----------------------------------------------------------------------------
# 2. Tests for event_detail()
# -----------------------------------------------------------------------------
def test_event_detail_view(client):
    """Test event detail route renders event data."""
    response = client.get("/events/1")
    assert response.status_code == 200
    html = response.data.decode("utf-8")
    assert "Open Tech Summit" in html
    assert "Hall A" in html
    assert "A summit on emerging tech." in html


def test_event_detail_404_on_invalid_id(client):
    """Test nonexistent event returns 404."""
    response = client.get("/events/9999")
    assert response.status_code == 404


def test_event_detail_registered_badge_for_student(client):
    """Test that a registered student sees the registered badge."""
    # Student 1 is registered for event 2 (Exclusive Workshop)
    login(client, "student1@test.edu", "student123")
    response = client.get("/events/2")
    assert response.status_code == 200
    html = response.data.decode("utf-8")
    assert "You&#39;re Registered" in html or "You're Registered" in html


# -----------------------------------------------------------------------------
# 3. Tests for create_event()
# -----------------------------------------------------------------------------
def test_create_event_requires_admin(client):
    """Test that anonymous and student users are blocked from create_event."""
    # Anonymous -> redirect to login
    response = client.get("/events/create", follow_redirects=False)
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]

    # Student -> redirect to profile with access denied
    login(client, "student1@test.edu", "student123")
    response = client.get("/events/create", follow_redirects=True)
    html = response.data.decode("utf-8")
    assert "Access denied: Administrator privileges required." in html


def test_create_event_success_as_admin(client, app):
    """Test administrator successfully creates an event."""
    login(client, "admin@test.edu", "admin123")

    now = datetime.utcnow()
    event_date = (now + timedelta(days=15)).strftime("%Y-%m-%dT%H:%M")
    reg_deadline = (now + timedelta(days=12)).strftime("%Y-%m-%dT%H:%M")

    response = client.post(
        "/events/create",
        data={
            "title": "Robotics Championship",
            "description": "Annual inter-college robot battle.",
            "venue": "Indoor Stadium",
            "event_date": event_date,
            "reg_deadline": reg_deadline,
            "max_seats": "80",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    html = response.data.decode("utf-8")
    assert "Robotics Championship" in html
    assert "Event &#39;Robotics Championship&#39; was created successfully!" in html or "created successfully!" in html

    # Verify in DB
    with app.app_context():
        created = Event.query.filter_by(title="Robotics Championship").first()
        assert created is not None
        assert created.max_seats == 80
        assert created.venue == "Indoor Stadium"


def test_create_event_validation_deadline_after_event_date(client):
    """Test validation catches registration deadline after event date."""
    login(client, "admin@test.edu", "admin123")

    now = datetime.utcnow()
    # Deadline is 15 days from now, but event date is 10 days (invalid)
    event_date = (now + timedelta(days=10)).strftime("%Y-%m-%dT%H:%M")
    reg_deadline = (now + timedelta(days=15)).strftime("%Y-%m-%dT%H:%M")

    response = client.post(
        "/events/create",
        data={
            "title": "Invalid Date Event",
            "description": "Some description",
            "venue": "Room 10",
            "event_date": event_date,
            "reg_deadline": reg_deadline,
            "max_seats": "50",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    html = response.data.decode("utf-8")
    assert "Registration deadline cannot be scheduled after the event date." in html


def test_create_event_validation_invalid_seats(client):
    """Test validation catches non-positive or non-integer seat numbers."""
    login(client, "admin@test.edu", "admin123")

    now = datetime.utcnow()
    event_date = (now + timedelta(days=5)).strftime("%Y-%m-%dT%H:%M")
    reg_deadline = (now + timedelta(days=3)).strftime("%Y-%m-%dT%H:%M")

    response = client.post(
        "/events/create",
        data={
            "title": "Zero Seats Event",
            "description": "Some description",
            "venue": "Room 10",
            "event_date": event_date,
            "reg_deadline": reg_deadline,
            "max_seats": "0",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    html = response.data.decode("utf-8")
    assert "Total available seats must be greater than zero." in html


# -----------------------------------------------------------------------------
# 4. Tests for delete_event()
# -----------------------------------------------------------------------------
def test_delete_event_requires_admin(client):
    """Test that non-admins cannot delete events."""
    # Anonymous
    response = client.post("/events/1/delete", follow_redirects=False)
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]

    # Student
    login(client, "student1@test.edu", "student123")
    response = client.post("/events/1/delete", follow_redirects=True)
    html = response.data.decode("utf-8")
    assert "Access denied: Administrator privileges required." in html


def test_delete_event_success_and_cascades(client, app):
    """Test administrator deletes event and registrations cascade."""
    login(client, "admin@test.edu", "admin123")

    # Event 2 has a registration
    with app.app_context():
        assert Event.query.get(2) is not None
        assert Registration.query.filter_by(event_id=2).count() == 1

    response = client.post("/events/2/delete", follow_redirects=True)
    assert response.status_code == 200
    html = response.data.decode("utf-8")
    assert "has been successfully deleted." in html

    # Verify event and cascading registrations are removed
    with app.app_context():
        assert Event.query.get(2) is None
        assert Registration.query.filter_by(event_id=2).count() == 0


# -----------------------------------------------------------------------------
# 5. Tests for register_event()
# -----------------------------------------------------------------------------
def test_register_event_requires_login(client):
    """Test anonymous user is redirected to login when trying to register."""
    response = client.post("/events/1/register", follow_redirects=False)
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_register_event_success(client, app):
    """Test student successfully registers for an open event."""
    login(client, "student2@test.edu", "student123")

    response = client.post("/events/1/register", follow_redirects=True)
    assert response.status_code == 200
    html = response.data.decode("utf-8")
    assert "Successfully registered for &#39;Open Tech Summit&#39;!" in html or "Successfully registered" in html

    with app.app_context():
        reg = Registration.query.filter_by(user_id=3, event_id=1).first()
        assert reg is not None
        assert reg.qr_token is not None
        assert reg.cert_code.startswith("CC-")


def test_register_event_blocks_duplicate(client):
    """Test that a student cannot register twice for the same event."""
    # Student 1 is already registered for Event 2 in fixture
    login(client, "student1@test.edu", "student123")

    response = client.post("/events/2/register", follow_redirects=True)
    assert response.status_code == 200
    html = response.data.decode("utf-8")
    assert "You are already registered for this event!" in html


def test_register_event_blocks_full_event(client):
    """Test that registration is rejected when an event is full."""
    # Event 2 has max_seats=1 and Student 1 already took it
    # Student 2 tries to register:
    login(client, "student2@test.edu", "student123")

    response = client.post("/events/2/register", follow_redirects=True)
    assert response.status_code == 200
    html = response.data.decode("utf-8")
    assert "Registration closed: This event is already fully booked!" in html


def test_register_event_blocks_past_deadline(client):
    """Test that registration is rejected if the deadline has passed."""
    login(client, "student2@test.edu", "student123")

    # Event 3 deadline was in the past
    response = client.post("/events/3/register", follow_redirects=True)
    assert response.status_code == 200
    html = response.data.decode("utf-8")
    assert "Registration closed: The deadline for this event has passed." in html
