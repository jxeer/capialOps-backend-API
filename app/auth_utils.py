"""
CapitalOps API - JWT Authentication Utilities

Provides JWT token generation, validation, and route protection decorators.
Replaces Flask-Login session-based auth with stateless JWT Bearer tokens.

Token flow:
    1. Client POSTs credentials to /api/auth/login
    2. Server returns a signed JWT containing user_id and role
    3. Client sends JWT in the Authorization header: "Bearer <token>"
    4. jwt_required() decorator validates the token on protected routes

Token payload structure:
    {
        "user_id": 1,
        "role": "sponsor_admin",
        "exp": <expiration timestamp>,
        "iat": <issued-at timestamp>
    }
"""

import jwt
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify, current_app, g
from app import db
from app.models import User


def generate_token(user):
    """
    Generate a signed JWT for an authenticated user.

    Args:
        user: User model instance.

    Returns:
        str: Encoded JWT string containing user_id, role, and expiration.
    """
    expiration_hours = current_app.config.get("JWT_EXPIRATION_HOURS", 24)
    payload = {
        "user_id": user.id,
        "role": user.role,
        "exp": datetime.utcnow() + timedelta(hours=expiration_hours),
        "iat": datetime.utcnow(),
    }
    return jwt.encode(payload, current_app.config["SECRET_KEY"], algorithm="HS256")


def decode_token(token):
    """
    Decode and validate a JWT.

    Args:
        token: Encoded JWT string.

    Returns:
        dict: Decoded payload on success.

    Raises:
        jwt.ExpiredSignatureError: If the token has expired.
        jwt.InvalidTokenError: If the token is malformed or invalid.
    """
    return jwt.decode(token, current_app.config["SECRET_KEY"], algorithms=["HS256"])


def jwt_required(f):
    """
    Decorator to protect API routes with JWT authentication.

    Extracts the Bearer token from the Authorization header, decodes it,
    loads the user from the database, and stores it in g.current_user.

    Returns 401 JSON error if:
        - No Authorization header is present
        - Token format is invalid (not "Bearer <token>")
        - Token is expired or malformed
        - User ID in the token doesn't exist in the database
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        # Extract token from Authorization header
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify({"error": "Missing or invalid authorization header"}), 401

        token = auth_header.split("Bearer ")[1]

        try:
            # Decode and validate the JWT
            payload = decode_token(token)
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token has expired"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid token"}), 401

        # Load user from database using the user_id in the token
        user = db.session.get(User, payload["user_id"])
        if not user:
            return jsonify({"error": "User not found"}), 401

        # Store the authenticated user on Flask's request-scoped g object
        g.current_user = user
        return f(*args, **kwargs)
    return decorated


def role_required(*allowed_roles):
    """
    Decorator to restrict access to specific roles.

    Must be used AFTER @jwt_required so that g.current_user is populated.

    Args:
        *allowed_roles: One or more role strings that are allowed access.

    Returns 403 JSON error if the authenticated user's role is not in the allowed list.

    Usage:
        @bp.route("/admin-only")
        @jwt_required
        @role_required("sponsor_admin")
        def admin_endpoint():
            ...
    """
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if g.current_user.role not in allowed_roles:
                return jsonify({"error": "Access denied"}), 403
            return f(*args, **kwargs)
        return decorated
    return decorator
