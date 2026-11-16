"""
Custom route decorators for role-based access control in CampusConnect.
"""

from functools import wraps
from flask import flash, redirect, url_for
from flask_login import current_user


def admin_required(view_func):
    """
    Restricts access to routes so only authenticated users with role == 'admin'
    can execute the wrapped view function.
    """

    @wraps(view_func)
    def wrapped_view(*args, **kwargs):
        if not current_user.is_authenticated:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for("auth.login"))

        if not current_user.is_admin():
            flash("Access denied: Administrator privileges required.", "danger")
            return redirect(url_for("auth.profile"))

        return view_func(*args, **kwargs)

    return wrapped_view