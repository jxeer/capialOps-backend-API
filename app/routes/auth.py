"""
CapitalOps API - Authentication Routes

Handles JWT-based authentication. Clients POST credentials to /login
and receive a signed JWT to use as a Bearer token on all subsequent requests.

Routes:
    POST /api/auth/login    — Authenticate and receive a JWT
    GET  /api/auth/me       — Get the current authenticated user's profile
"""

from flask import Blueprint, request, jsonify
from app import db
from app.models import User
from app.auth_utils import generate_token, jwt_required
from flask import g

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["POST"])
def login():
    """
    Authenticate a user and return a JWT.

    Expects JSON body:
        {
            "username": "admin",
            "password": "admin123"
        }

    Returns on success (200):
        {
            "token": "<jwt_string>",
            "user": { ...user profile... }
        }

    Returns on failure (401):
        { "error": "Invalid username or password" }
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

    # Generate JWT and return with user profile
    token = generate_token(user)
    return jsonify({
        "token": token,
        "user": user.to_dict(),
    })


@auth_bp.route("/me", methods=["GET"])
@jwt_required
def me():
    """
    Return the currently authenticated user's profile.

    Requires a valid JWT in the Authorization header.
    Used by the frontend to verify token validity and load user state.

    Returns (200):
        { "user": { ...user profile... } }
    """
    return jsonify({"user": g.current_user.to_dict()})
