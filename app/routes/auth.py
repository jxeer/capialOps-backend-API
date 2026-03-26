"""
CapitalOps API - Authentication Routes

Handles JWT-based authentication using flask-jwt-extended.
Clients POST credentials to /login and receive a signed access token
to use as a Bearer token on all subsequent requests.

Routes:
    POST /api/v1/auth/login           — Authenticate and receive a JWT access token
    GET  /api/v1/auth/me              — Get the current authenticated user's profile
    POST /api/v1/auth/forgot-password — Generate a password reset token and send email
    POST /api/v1/auth/reset-password — Validate token and update user's password
"""

import os
from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required
from app.models import User, PasswordResetToken
from app.auth_utils import get_current_user
import resend

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["POST"])
def login():
    """
    Authenticate a user and return a JWT access token.

    Expects JSON body:
        {
            "username": "admin",
            "password": "admin123"
        }

    Returns on success (200):
        {
            "accessToken": "<jwt_access_token>",
            "user": { id, username, role, full_name }
        }

    Returns on failure (400): If username or password is missing.
    Returns on failure (401): If credentials are invalid.
    """
    data = request.get_json()

    # Validate that JSON body is present and has required fields
    if not data or not data.get("username") or not data.get("password"):
        return jsonify({"error": "Username and password are required"}), 400

    # Look up user by username
    user = User.query.filter_by(username=data["username"]).first()

    # Verify password hash matches
    if not user or not user.check_password(data["password"]):
        return jsonify({"error": "Invalid username or password"}), 401

    # Create access token with user ID (stringified) as identity and role as
    # additional claim. JWT claims: sub = str(user.id), role = user.role.
    # The role claim allows role_required() to check permissions without a DB lookup.
    access_token = create_access_token(
        identity=str(user.id),
        additional_claims={"role": user.role},
    )

    return jsonify({
        "accessToken": access_token,
        "user": user.to_dict(),
    })


@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def me():
    """
    Return the currently authenticated user's profile.

    Requires a valid JWT in the Authorization header.
    Used by the frontend to verify token validity and load user state.

    Returns (200):
        { "user": { ...user profile... } }
    """
    user = get_current_user()
    if not user:
        return jsonify({"error": "User not found"}), 404
    return jsonify({"user": user.to_dict()})


@auth_bp.route("/forgot-password", methods=["POST"])
def forgot_password():
    """
    Generate a password reset token and send a reset email to the user.

    Accepts either a username or an email address in the request body.
    Returns success even if the email/username is not found, to prevent
    account enumeration attacks.

    Expects JSON body:
        {
            "username": "admin"  // optional, mutually exclusive with email
            "email": "admin@example.com"  // optional, mutually exclusive with username
        }

    Returns (200):
        { "message": "If an account exists, a reset email has been sent." }
    Returns (400): If neither username nor email is provided.
    """
    data = request.get_json()

    if not data:
        return jsonify({"error": "Request body is required"}), 400

    identifier = data.get("username") or data.get("email")
    if not identifier:
        return jsonify({"error": "Username or email is required"}), 400

    user = User.query.filter(
        (User.username == identifier) | (User.email == identifier)
    ).first()

    if not user or not user.password_hash:
        return jsonify({
            "message": "If an account exists with a password, a reset email has been sent."
        }), 200

    db = _get_db()
    reset_token = PasswordResetToken.generate_token(user.id)
    db.session.add(reset_token)
    db.session.commit()

    _send_reset_email(user, reset_token.token)

    return jsonify({
        "message": "If an account exists with a password, a reset email has been sent."
    }), 200


@auth_bp.route("/reset-password", methods=["POST"])
def reset_password():
    """
    Validate a password reset token and update the user's password.

    Expects JSON body:
        {
            "token": "abc123...",
            "password": "newpassword123"
        }

    Returns (200):
        { "message": "Password has been reset successfully." }
    Returns (400): If token or password is missing, or if password is too short.
    Returns (401): If token is invalid, expired, or already used.
    """
    data = request.get_json()

    if not data:
        return jsonify({"error": "Request body is required"}), 400

    token_str = data.get("token")
    password = data.get("password")

    if not token_str:
        return jsonify({"error": "Reset token is required"}), 400
    if not password:
        return jsonify({"error": "New password is required"}), 400
    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters"}), 400

    reset_token = PasswordResetToken.query.filter_by(token=token_str).first()

    if not reset_token or not reset_token.is_valid:
        return jsonify({"error": "Invalid or expired reset token"}), 401

    db = _get_db()
    user = db.session.get(User, reset_token.user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    reset_token.used = True
    user.set_password(password)
    db.session.commit()

    return jsonify({"message": "Password has been reset successfully."}), 200


def _send_reset_email(user, token):
    """
    Send a password reset email to the given user via Resend.

    Args:
        user: The User model instance to send the email to.
        token: The password reset token string.
    """
    resend_api_key = os.environ.get("RESEND_API_KEY")
    frontend_origin = os.environ.get("FRONTEND_ORIGIN", "http://localhost:5173")
    reset_link = f"{frontend_origin}/auth/reset-password?token={token}"

    email_html = f"""
    <h1>Password Reset Request</h1>
    <p>Hi {user.full_name or user.username},</p>
    <p>We received a request to reset your CapitalOps password. Click the link below to set a new password:</p>
    <p><a href="{reset_link}">Reset Password</a></p>
    <p>This link will expire in 30 minutes.</p>
    <p>If you didn't request this, you can safely ignore this email.</p>
    """

    if not resend_api_key:
        return

    try:
        resend.api_key = resend_api_key
        resend.Emails.send({
            "from": "CapitalOps <onboarding@resend.dev>",
            "to": user.email,
            "subject": "Reset your CapitalOps password",
            "html": email_html,
        })
    except Exception as e:
        pass


def _get_db():
    """Import db here to avoid circular imports."""
    from app import db
    return db
