"""
CapitalOps API - Authentication Utilities

Provides helper functions and decorators for JWT-based route protection
using flask-jwt-extended.

Token flow:
    1. Client POSTs credentials to /api/v1/auth/login
    2. Server returns a signed access token via create_access_token()
    3. Client sends token in the Authorization header: "Bearer <token>"
    4. @jwt_required() (from flask-jwt-extended) validates the token
    5. get_current_user() loads the User from the DB using the token identity

The access token carries additional claims (role) so the role_required()
decorator can enforce permissions without an extra DB lookup.

Token identity: user.id (integer)
Additional claims: { "role": "sponsor_admin" }
"""

from functools import wraps
from flask import jsonify
from flask_jwt_extended import get_jwt_identity, get_jwt, verify_jwt_in_request
from app import db
from app.models import User


def get_current_user():
    """
    Load the authenticated User from the database using the JWT identity.

    Must be called inside a request protected by @jwt_required().
    The JWT identity is the user's primary key ID.

    Returns:
        User: The authenticated user's model instance, or None if not found.
    """
    user_id = get_jwt_identity()
    return db.session.get(User, int(user_id))


def role_required(*allowed_roles):
    """
    Decorator to restrict access to specific roles.

    Reads the 'role' claim from the JWT and checks it against the allowed list.
    This avoids an extra DB query — the role is embedded in the token at login time.

    Must be stacked AFTER @jwt_required() so the token is already validated.

    Args:
        *allowed_roles: One or more role strings that are allowed access.

    Returns 403 JSON error if the user's role is not in the allowed list.

    Usage:
        @bp.route("/admin-only")
        @jwt_required()
        @role_required("sponsor_admin")
        def admin_endpoint():
            ...
    """
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            # Read the role claim directly from the JWT payload
            claims = get_jwt()
            user_role = claims.get("role", "")
            if user_role not in allowed_roles:
                return jsonify({"error": "Access denied"}), 403
            return f(*args, **kwargs)
        return decorated
    return decorator
