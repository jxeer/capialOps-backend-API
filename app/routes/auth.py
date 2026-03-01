"""
CapitalOps - Authentication Routes

Handles user login and logout. All other routes in the application
require authentication via the @login_required decorator, and
unauthenticated users are redirected here automatically by Flask-Login.

Routes:
    GET  /login  — Render the login page
    POST /login  — Authenticate user credentials and start a session
    GET  /logout — End the user's session and redirect to login
"""

from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required, current_user
from app import db
from app.models import User

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """
    Handle user login.

    GET:  Renders the login form. If the user is already authenticated,
          redirects to the dashboard instead of showing the login page.

    POST: Validates username/password against the database.
          On success: starts a session and redirects to the dashboard
          (or to the 'next' URL if they were redirected from a protected page).
          On failure: flashes an error message and re-renders the login form.
    """
    # Skip login page if user is already authenticated
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        # Look up user by username
        user = User.query.filter_by(username=username).first()

        # Verify password hash matches
        if user and user.check_password(password):
            login_user(user)
            # Redirect to the page they were trying to access, or the dashboard
            next_page = request.args.get("next")
            return redirect(next_page or url_for("dashboard.index"))

        flash("Invalid username or password", "error")

    return render_template("auth/login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    """End the user's session and redirect to the login page."""
    logout_user()
    return redirect(url_for("auth.login"))
