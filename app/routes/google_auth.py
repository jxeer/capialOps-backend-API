"""
CapitalOps API - Google Authentication Route

Provides a single endpoint for Google Sign-In token verification.
The frontend obtains a Google ID token via the Google Sign-In SDK,
then POSTs it here. The backend verifies the token with Google's
public keys, finds or creates the user in the database, and returns
a CapitalOps JWT access token.

Flow:
    1. Frontend shows "Sign in with Google" button
    2. User authenticates with Google → frontend receives an ID token
    3. Frontend POSTs { "credential": "<google_id_token>" } to /api/v1/auth/google
    4. Backend verifies the token against Google's public keys
    5. Backend finds existing user by google_id or email, or creates a new one
    6. Backend returns a CapitalOps JWT + user profile (same format as /login)

Environment Variables:
    GOOGLE_OAUTH_CLIENT_ID  — Your Google Cloud OAuth 2.0 Client ID
                              (must match the client_id used by the frontend SDK)

New User Default Role:
    First-time Google sign-in users are assigned the 'investor_tier1' role.
    An admin can promote them to a higher role via the admin panel.
"""

import os
import logging

from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token
from google.oauth2 import id_token as google_id_token
from google.auth.transport import requests as google_requests

from app import db
from app.models import User

logger = logging.getLogger(__name__)

google_auth_bp = Blueprint("google_auth", __name__)

# Default role assigned to new users who sign in via Google for the first time.
# Admins can upgrade their role later through the application.
DEFAULT_GOOGLE_USER_ROLE = "investor_tier1"


@google_auth_bp.route("/status", methods=["GET"])
def google_status():
    """Check if Google OAuth is configured and enabled."""
    client_id = os.environ.get("GOOGLE_OAUTH_CLIENT_ID")
    return jsonify({
        "enabled": bool(client_id),
        "configured": bool(client_id),
    })


@google_auth_bp.route("/debug", methods=["GET"])
def google_debug():
    """Debug endpoint to verify route registration."""
    return jsonify({
        "message": "Google debug endpoint works",
        "client_id_set": bool(os.environ.get("GOOGLE_OAUTH_CLIENT_ID")),
        "client_id": os.environ.get("GOOGLE_OAUTH_CLIENT_ID", "NOT SET")[:20] + "...",
    })

@google_auth_bp.route("/gauth", methods=["GET"])
def google_redirect():
    """Redirect to Google's OAuth consent page.
    
    Redirects to:
    https://accounts.google.com/o/oauth2/v2/auth?
        client_id=GOOGLE_OAUTH_CLIENT_ID
        &redirect_uri=backend_url/api/v1/auth/google/callback
        &response_type=code
        &scope=openid%20email%20profile
        &access_type=offline
    """
    import urllib.parse
    client_id = os.environ.get("GOOGLE_OAUTH_CLIENT_ID")
    if not client_id:
        return jsonify({"error": "Google OAuth not configured"}), 400
    
    backend_url = request.url_root.rstrip("/")
    redirect_uri = f"{backend_url}/api/v1/auth/google/callback"
    
    params = urllib.parse.urlencode({
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "select_account",
    })
    
    return jsonify({
        "authUrl": f"https://accounts.google.com/o/oauth2/v2/auth?{params}"
    })


@google_auth_bp.route("/google", methods=["POST"])
def google_login():
    """
    Verify a Google ID token and return a CapitalOps JWT.

    Expects JSON body:
        {
            "credential": "<google_id_token_string>"
        }

    The 'credential' field is the ID token returned by Google Sign-In
    (either from the One Tap prompt or the standard Sign-In button).

    Verification steps:
        1. Check GOOGLE_OAUTH_CLIENT_ID is configured
        2. Validate the Google ID token signature + claims via google-auth library
        3. Confirm the email is verified by Google
        4. Find an existing user by google_id, or by email (and link the account)
        5. If no user exists, create a new one with the default role
        6. Issue a CapitalOps JWT with the same format as /login

    Returns on success (200):
        {
            "accessToken": "<jwt_access_token>",
            "user": { id, username, email, role, full_name, ... },
            "isNewUser": true/false
        }

    Returns on failure:
        400 — Missing credential or GOOGLE_OAUTH_CLIENT_ID not configured
        401 — Google token verification failed (invalid, expired, wrong audience)
        409 — Email already linked to a different Google account
    """
    # Retrieve the Google Client ID from environment
    client_id = os.environ.get("GOOGLE_OAUTH_CLIENT_ID")
    if not client_id:
        logger.error("GOOGLE_OAUTH_CLIENT_ID environment variable is not set")
        return jsonify({
            "error": "Google authentication is not configured on this server"
        }), 400

    # Parse the request body
    data = request.get_json()
    if not data or not data.get("credential"):
        return jsonify({"error": "Google credential token is required"}), 400

    credential = data["credential"]

    # Verify the Google ID token using Google's public keys.
    # This checks the token signature, expiration, issuer, and audience (client_id).
    try:
        idinfo = google_id_token.verify_oauth2_token(
            credential,
            google_requests.Request(),
            client_id,
        )
    except ValueError as e:
        # Token is invalid — could be expired, wrong audience, bad signature, etc.
        logger.warning("Google token verification failed: %s", str(e))
        return jsonify({"error": "Invalid Google token"}), 401

    # Extract user info from the verified token claims
    google_sub = idinfo["sub"]           # Google's unique user ID (stable across sessions)
    email = idinfo.get("email", "")
    email_verified = idinfo.get("email_verified", False)
    given_name = idinfo.get("given_name", "")
    family_name = idinfo.get("family_name", "")
    full_name = idinfo.get("name", f"{given_name} {family_name}".strip())

    # Require a verified email — Google occasionally returns unverified emails
    if not email_verified:
        return jsonify({"error": "Google email is not verified"}), 401

    # --- User Lookup / Creation ---
    # Uses a three-step strategy with safety checks to prevent account takeover.
    is_new_user = False

    # Strategy 1: Find by google_id (returning user who has signed in with Google before)
    user = User.query.filter_by(google_id=google_sub).first()

    if not user:
        # Strategy 2: Find by email (existing account created via username/password,
        # now linking their Google account for the first time)
        user = User.query.filter_by(email=email).first()
        if user:
            # Safety check: only link if the user has no Google account linked yet.
            # If a different Google account is already linked, reject to prevent
            # account takeover by someone who controls the same email on a different
            # Google workspace.
            if user.google_id is not None and user.google_id != google_sub:
                logger.warning(
                    "Google link conflict: email=%s already linked to google_id=%s, "
                    "attempted with google_id=%s",
                    email, user.google_id, google_sub
                )
                return jsonify({
                    "error": "This email is already linked to a different Google account"
                }), 409

            # Link the Google account to the existing user
            user.google_id = google_sub
            if not user.full_name:
                user.full_name = full_name
            db.session.commit()
            logger.info("Linked Google account to existing user: %s", email)

    if not user:
        # Strategy 3: Create a brand new user account
        # Generate a unique username from the email prefix.
        base_username = email.split("@")[0]
        username = base_username
        counter = 1
        while User.query.filter_by(username=username).first():
            username = f"{base_username}{counter}"
            counter += 1

        try:
            user = User(
                username=username,
                email=email,
                role=DEFAULT_GOOGLE_USER_ROLE,
                full_name=full_name,
                google_id=google_sub,
                password_hash=None,  # No password for Google-only accounts
            )
            db.session.add(user)
            db.session.commit()
            is_new_user = True
            logger.info("Created new Google user: %s (role=%s)", email, DEFAULT_GOOGLE_USER_ROLE)
        except Exception:
            # Race condition: another request created this user between our check and insert.
            db.session.rollback()
            user = User.query.filter_by(google_id=google_sub).first()
            if not user:
                user = User.query.filter_by(email=email).first()
            if not user:
                logger.error("Failed to create or find Google user: %s", email)
                return jsonify({"error": "Account creation failed, please try again"}), 500

    # Issue a CapitalOps JWT with the same structure as the /login endpoint
    access_token = create_access_token(
        identity=str(user.id),
        additional_claims={"role": user.role},
    )

    return jsonify({
        "accessToken": access_token,
        "user": user.to_dict(),
        "isNewUser": is_new_user,
    })
