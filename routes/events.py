"""
Event Management routes for CampusConnect.
Owned by Member 2.

This module provides the blueprint and controllers for:
- Browsing and searching college events with live seat counts (browse)
- Viewing detailed event information and attendee lists (event_detail)
- Creating new campus events with date and seat validation (create_event)
- Deleting events with cascading registration cleanup (delete_event)
- Registering authenticated students for events with strict validations:
  blocking duplicate registrations, full events, or expired deadlines (register_event)
"""

from datetime import datetime
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

# Import database models and role-based access control decorators
try:
    from models import Event, Registration, User, db
    from decorators import admin_required
except ImportError:
    from campusconnect.models import Event, Registration, User, db
    from campusconnect.decorators import admin_required

# -----------------------------------------------------------------------------
# Blueprint Definition
# url_prefix='/events' means all endpoints defined here will be prefixed with /events
# e.g., browse() -> /events/, create_event() -> /events/create
# -----------------------------------------------------------------------------
events_bp = Blueprint("events", __name__, url_prefix="/events")


# -----------------------------------------------------------------------------
# 1. Browse & Search Events
# -----------------------------------------------------------------------------
@events_bp.route("/")
@events_bp.route("")
def browse():
    """
    Displays the event catalog with real-time seat availability.
    Supports search queries across title, description, and venue.
    
    URL: /events/ or /events
    Method: GET
    Access: Public (anyone can browse events)
    """
    # Retrieve optional search keyword from URL query parameters (?q=keyword)
    search_query = request.args.get("q", "").strip()

    # Base query for all events
    query = Event.query

    # If the user entered a search query, filter case-insensitively across key fields
    if search_query:
        search_pattern = f"%{search_query}%"
        query = query.filter(
            db.or_(
                Event.title.ilike(search_pattern),
                Event.description.ilike(search_pattern),
                Event.venue.ilike(search_pattern),
            )
        )

    # Order upcoming events by date ascending (soonest events first)
    events = query.order_by(Event.event_date.asc()).all()

    # Current UTC timestamp for comparison with registration deadlines
    now = datetime.utcnow()

    return render_template(
        "events/browse.html",
        events=events,
        search_query=search_query,
        now=now,
    )


# -----------------------------------------------------------------------------
# 2. View Event Details
# -----------------------------------------------------------------------------
@events_bp.route("/<int:event_id>")
def event_detail(event_id: int):
    """
    Displays full details for a single event, including description,
    seat count, registration deadlines, and registration action button.
    For administrators, also lists registered attendees.
    
    URL: /events/<event_id>
    Method: GET
    Access: Public (anyone can view details)
    """
    # Fetch the event or return a 404 Not Found error if it doesn't exist
    event = Event.query.get_or_404(event_id)

    # Check if the logged-in user has already registered for this event
    user_registration = None
    is_registered = False

    if current_user.is_authenticated:
        user_registration = Registration.query.filter_by(
            user_id=current_user.id,
            event_id=event.id,
        ).first()
        is_registered = user_registration is not None

    now = datetime.utcnow()

    return render_template(
        "events/event_detail.html",
        event=event,
        is_registered=is_registered,
        user_registration=user_registration,
        now=now,
    )


# -----------------------------------------------------------------------------
# 3. Create Event (Admin Only)
# -----------------------------------------------------------------------------
@events_bp.route("/create", methods=["GET", "POST"])
@admin_required
def create_event():
    """
    Renders the event creation form (GET) and processes the submission (POST).
    Restricted to administrators using the @admin_required decorator.
    
    URL: /events/create
    Method: GET, POST
    Access: Administrator only
    """
    # Form data dictionary to repopulate fields if validation fails
    form_data = {}

    if request.method == "POST":
        # Extract inputs from submitted form
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        venue = request.form.get("venue", "").strip()
        event_date_str = request.form.get("event_date", "").strip()
        reg_deadline_str = request.form.get("reg_deadline", "").strip()
        max_seats_str = request.form.get("max_seats", "").strip()

        # Preserve form data so user does not need to retype everything on error
        form_data = {
            "title": title,
            "description": description,
            "venue": venue,
            "event_date": event_date_str,
            "reg_deadline": reg_deadline_str,
            "max_seats": max_seats_str,
        }

        # Step 1: Validate required fields are not empty
        if not (title and description and venue and event_date_str and reg_deadline_str and max_seats_str):
            flash("All fields are required. Please fill in all details.", "danger")
            return render_template("events/create_event.html", form_data=form_data)

        # Step 2: Validate max_seats is a positive integer
        try:
            max_seats = int(max_seats_str)
            if max_seats <= 0:
                flash("Total available seats must be greater than zero.", "danger")
                return render_template("events/create_event.html", form_data=form_data)
        except ValueError:
            flash("Maximum seats must be a valid positive integer.", "danger")
            return render_template("events/create_event.html", form_data=form_data)

        # Step 3: Parse ISO datetime strings from HTML5 datetime-local inputs
        try:
            event_date = datetime.fromisoformat(event_date_str)
            reg_deadline = datetime.fromisoformat(reg_deadline_str)
        except (ValueError, TypeError):
            flash("Invalid date or time format. Please select valid dates.", "danger")
            return render_template("events/create_event.html", form_data=form_data)

        # Step 4: Validate logical date constraints (deadline must not be after event date)
        if reg_deadline > event_date:
            flash("Registration deadline cannot be scheduled after the event date.", "danger")
            return render_template("events/create_event.html", form_data=form_data)

        # Step 5: Save the new event to the database
        try:
            new_event = Event(
                title=title,
                description=description,
                venue=venue,
                event_date=event_date,
                reg_deadline=reg_deadline,
                max_seats=max_seats,
                created_by=current_user.id,
            )
            db.session.add(new_event)
            db.session.commit()

            flash(f"Event '{new_event.title}' was created successfully!", "success")
            return redirect(url_for("events.event_detail", event_id=new_event.id))
        except SQLAlchemyError:
            db.session.rollback()
            flash("A database error occurred while creating the event. Please try again.", "danger")
            return render_template("events/create_event.html", form_data=form_data)

    # GET request: render empty form
    return render_template("events/create_event.html", form_data=form_data)


# -----------------------------------------------------------------------------
# 4. Delete Event (Admin Only)
# -----------------------------------------------------------------------------
@events_bp.route("/<int:event_id>/delete", methods=["POST", "GET"])
@events_bp.route("/delete/<int:event_id>", methods=["POST", "GET"])
@admin_required
def delete_event(event_id: int):
    """
    Deletes an event and cascades to remove associated registrations.
    Restricted to administrators using the @admin_required decorator.
    
    URL: /events/<event_id>/delete
    Method: POST (recommended), GET (supported fallback)
    Access: Administrator only
    """
    event = Event.query.get_or_404(event_id)
    event_title = event.title

    try:
        # Delete event record; SQLAlchemy cascade handles associated registrations
        db.session.delete(event)
        db.session.commit()
        flash(f"Event '{event_title}' has been successfully deleted.", "success")
    except SQLAlchemyError:
        # Roll back transaction if an error occurs to keep database consistent
        db.session.rollback()
        flash("A database error occurred while deleting the event. Please try again.", "danger")
        return redirect(url_for("events.event_detail", event_id=event.id))

    return redirect(url_for("events.browse"))


# -----------------------------------------------------------------------------
# 5. Register Student for an Event
# -----------------------------------------------------------------------------
@events_bp.route("/<int:event_id>/register", methods=["POST"])
@login_required
def register_event(event_id: int):
    """
    Registers the authenticated student for an event.
    
    Enforces business logic validations:
    1. Blocks duplicate registration for the same student and event.
    2. Blocks registration if event seats are full.
    3. Blocks registration if the registration deadline has passed.
    
    Uses try/except blocks to ensure robust error handling and database rollback.
    
    URL: /events/<event_id>/register
    Method: POST
    Access: Authenticated users (@login_required)
    """
    event = Event.query.get_or_404(event_id)
    now = datetime.utcnow()

    # Rule 1: Prevent duplicate registrations
    existing_registration = Registration.query.filter_by(
        user_id=current_user.id,
        event_id=event.id,
    ).first()

    if existing_registration:
        flash("You are already registered for this event!", "warning")
        return redirect(url_for("events.event_detail", event_id=event.id))

    # Rule 2: Prevent registration if event is fully booked
    if event.seats_remaining() <= 0:
        flash("Registration closed: This event is already fully booked!", "danger")
        return redirect(url_for("events.event_detail", event_id=event.id))

    # Rule 3: Prevent registration if deadline has elapsed
    if now > event.reg_deadline:
        flash("Registration closed: The deadline for this event has passed.", "danger")
        return redirect(url_for("events.event_detail", event_id=event.id))

    # Rule 4: Create new registration entry with transaction error handling
    try:
        new_registration = Registration(
            user_id=current_user.id,
            event_id=event.id,
        )
        db.session.add(new_registration)
        db.session.commit()

        flash(
            f"Successfully registered for '{event.title}'! Your QR entry pass is now available.",
            "success",
        )
    except IntegrityError:
        # Handles concurrency race-condition caught by the database unique constraint
        db.session.rollback()
        flash("You are already registered for this event.", "warning")
    except SQLAlchemyError:
        # Handles general database errors
        db.session.rollback()
        flash("A database error occurred while completing your registration. Please try again.", "danger")

    return redirect(url_for("events.event_detail", event_id=event.id))
