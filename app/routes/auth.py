"""
CapitalOps API - Authentication Routes

Handles JWT-based authentication using flask-jwt-extended.
Clients POST credentials to /login and receive a signed access token
to use as a Bearer token on all subsequent requests.

Routes:
    POST /api/v1/auth/login    — Authenticate and receive a JWT access token
    GET  /api/v1/auth/me       — Get the current authenticated user's profile
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required
from app.models import User
from app.auth_utils import get_current_user

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
            "token": "<jwt_access_token>",
            "user": { ...user profile... }
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

    # Create access token with user ID as identity and role as additional claim.
    # The role claim allows role_required() to check permissions without a DB lookup.
    access_token = create_access_token(
        identity=str(user.id),
        additional_claims={"role": user.role},
    )

    return jsonify({
        "token": access_token,
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
