"""
Dev utilities - API routes for development and debugging.

WARNING: These routes should NEVER be exposed in production.
They are intentionally insecure for dev purposes only.

Routes:
    POST /api/v1/dev/seed    - Force re-seed demo data (bypasses normal guard)
    GET  /api/v1/dev/status  - Quick status check
"""

import os
from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required
from app import db
from app.auth_utils import get_current_user

dev_bp = Blueprint("dev", __name__)


@dev_bp.route("/seed", methods=["POST"])
@jwt_required()
def seed_demo_data_endpoint():
    """
    Force re-seed demo data for development.

    Requires admin role.

    Returns:
        JSON with seed status
    """
    user = get_current_user()
    if user.role != "sponsor_admin":
        return jsonify({"error": "Admin access required"}), 403

    try:
        from app import seed_demo_data as _seed
        _seed(force=True)
        return jsonify({
            "status": "success",
            "message": "Demo data seeded successfully"
        })
    except Exception as e:
        import traceback
        return jsonify({
            "status": "error",
            "error": str(e),
            "trace": traceback.format_exc()
        }), 500


@dev_bp.route("/status", methods=["GET"])
def status():
    """Quick status check for dev purposes."""
    from app.models import User, Portfolio, Asset
    return jsonify({
        "users": User.query.count(),
        "portfolios": Portfolio.query.count(),
        "assets": Asset.query.count(),
    })