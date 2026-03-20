"""
CapitalOps API - GUI Compatibility Layer

Provides flat REST endpoints at /api/ that match the response format
expected by the CapitalOps frontend GUI (React + Express proxy).

Key differences from the /api/v1/ routes:
    - No JWT authentication (the GUI's Express server proxies without tokens)
    - camelCase JSON keys (frontend uses camelCase throughout)
    - String IDs (frontend expects string-typed IDs for Zod schema validation)
    - Flat arrays (frontend expects bare arrays, not wrapped in named keys)

The GUI's Express server sets BACKEND_URL and proxies req.originalUrl directly,
so these routes must match the exact paths the frontend fetches:
    GET  /api/backend-status
    GET  /api/dashboard/stats
    GET  /api/portfolios
    GET  /api/assets          POST /api/assets
    GET  /api/assets/:id
    GET  /api/projects        POST /api/projects
    GET  /api/projects/:id
    GET  /api/deals           POST /api/deals
    GET  /api/deals/:id
    GET  /api/investors       POST /api/investors
    GET  /api/investors/:id
    GET  /api/allocations     POST /api/allocations
    GET  /api/milestones      POST /api/milestones
    GET  /api/milestones/project/:projectId
    GET  /api/vendors         POST /api/vendors
    GET  /api/vendors/:id
    GET  /api/work-orders     POST /api/work-orders
    GET  /api/work-orders/vendor/:vendorId
    GET  /api/risk-flags
    GET  /api/risk-flags/project/:projectId
"""

import os
import uuid
from functools import wraps
from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_cors import cross_origin
from app import db
from app.models import (
    Portfolio, Asset, Project, Deal, Investor,
    Allocation, Milestone, Vendor, WorkOrder, RiskFlag, User,
    ConnectionRequest, Conversation, Message,
)

compat_bp = Blueprint("compat", __name__)


def _require_api_key(f):
    """Protect mutation routes with a shared API key.

    The GUI's Express server must send the key in X-API-Key header.
    If COMPAT_API_KEY is not set, mutation routes are open (dev mode).
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        api_key = os.environ.get("COMPAT_API_KEY")
        if api_key:
            provided = request.headers.get("X-API-Key", "")
            if provided != api_key:
                return jsonify({"error": "Invalid or missing API key"}), 403
        return f(*args, **kwargs)
    return decorated


def _snake_to_camel(name):
    """Convert a snake_case string to camelCase.

    Examples:
        'capital_required' -> 'capitalRequired'
        'portfolio_id'     -> 'portfolioId'
        'id'               -> 'id'  (single-word stays unchanged)
    """
    parts = name.split("_")
    return parts[0] + "".join(p.capitalize() for p in parts[1:])


# Explicit camelCase overrides for fields where the generic converter
# produces a different casing than what the frontend schema expects.
_CAMEL_OVERRIDES = {
    "capex_flag": "capExFlag",
}


def _to_gui(record_dict):
    """Transform a model's to_dict() output into GUI-compatible format.

    Applies two transformations:
        1. All keys converted from snake_case to camelCase (with overrides)
        2. The 'id' field is cast to a string (frontend uses string IDs)
    """
    result = {}
    for key, value in record_dict.items():
        camel_key = _CAMEL_OVERRIDES.get(key, _snake_to_camel(key))
        if key == "id":
            result[camel_key] = str(value)
        elif key.endswith("_id") and value is not None:
            result[camel_key] = str(value)
        else:
            result[camel_key] = value
    return result


# ---------------------------------------------------------------------------
# Backend Status (used by the GUI dashboard to show connectivity indicator)
# ---------------------------------------------------------------------------

from flask_cors import cross_origin

@compat_bp.route("/backend-status", methods=["GET"])
def backend_status():
    """Health check endpoint for the frontend to verify backend connectivity."""
    return jsonify({
        "service": "capitalops-api",
        "status": "ok",
        "connected": True,
        "mode": "live",
        "url": request.url_root,
    })


@compat_bp.route("/login", methods=["POST"])
@_require_api_key
def compat_login():
    """Authenticate user and return JWT token (same as /api/v1/auth/login)."""
    from flask_jwt_extended import create_access_token

    data = request.get_json() or {}
    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify({"message": "Username and password required"}), 400

    user = User.query.filter_by(username=username).first()
    if not user or not user.check_password(password):
        return jsonify({"message": "Invalid credentials"}), 401

    access_token = create_access_token(
        identity=str(user.id),
        additional_claims={"role": user.role},
    )

    return jsonify({
        "accessToken": access_token,
        "user": user.to_dict(),
    })


@compat_bp.route("/setup-admin", methods=["POST"])
def setup_admin():
    """Create admin user if not exists. Use this to bootstrap the app.
    This endpoint is open but only creates one admin account.
    """
    admin = User.query.filter_by(username="admin").first()
    if admin:
        return jsonify({"message": "Admin already exists", "user": admin.to_dict()})

    admin = User(
        username="admin",
        email="admin@capitalops.io",
        role="sponsor_admin",
        full_name="Admin User",
    )
    admin.set_password("admin123")
    db.session.add(admin)
    db.session.commit()

    return jsonify({
        "message": "Admin created",
        "username": "admin",
        "password": "admin123",
        "user": admin.to_dict(),
    }), 201


@compat_bp.route("/register", methods=["POST"])
@_require_api_key
def compat_register():
    """Create a new user account."""
    from flask_jwt_extended import create_access_token

    data = request.get_json() or {}
    username = data.get("username")
    password = data.get("password")
    email = data.get("email")
    full_name = data.get("fullName") or data.get("full_name")

    if not username or not password:
        return jsonify({"message": "Username and password required"}), 400

    # Check if user exists
    existing = User.query.filter_by(username=username).first()
    if existing:
        return jsonify({"message": "Username already exists"}), 409

    if email:
        existing_email = User.query.filter_by(email=email).first()
        if existing_email:
            return jsonify({"message": "Email already exists"}), 409

    # Create new user
    user = User(
        username=username,
        email=email or f"{username}@example.com",
        full_name=full_name or username,
        role="investor_tier1",
    )
    user.set_password(password)

    db.session.add(user)
    db.session.commit()

    # Create token
    access_token = create_access_token(
        identity=str(user.id),
        additional_claims={"role": user.role},
    )

    return jsonify({
        "accessToken": access_token,
        "user": user.to_dict(),
    }), 201



# ---------------------------------------------------------------------------
# User (from session or JWT) - for GUI compatibility
# ---------------------------------------------------------------------------

def _get_user_from_request():
    """Extract user from request - checks JWT Bearer token or Flask session."""
    from flask import request, session
    from flask_jwt_extended import decode_token
    from app.auth_utils import get_current_user
    
    # Try JWT Bearer token first
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        try:
            decoded = decode_token(token)
            user_id = decoded.get("sub")
            if user_id:
                user = User.query.get(int(user_id))
                if user:
                    return user
        except Exception:
            pass
    
    # Fall back to session
    user_id = session.get("user_id")
    if user_id:
        return User.query.get(user_id)
    
    return None


@compat_bp.route("/user", methods=["GET"])
def get_user():
    """Return the current authenticated user from JWT token or session."""
    user = _get_user_from_request()
    if not user:
        return jsonify({"message": "Authentication required"}), 401
    return jsonify(user.to_dict())


@compat_bp.route("/user", methods=["PUT"])
@_require_api_key
def update_user_profile():
    """Update the current user's profile, including profile image."""
    from flask import session
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"message": "Authentication required"}), 401
    
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    data = request.get_json() or {}
    
    if "profileImage" in data:
        user.profile_image = data["profileImage"]
    
    db.session.commit()
    return jsonify(user.to_dict())

# ---------------------------------------------------------------------------
# Dashboard Stats
# ---------------------------------------------------------------------------

@compat_bp.route("/dashboard/stats", methods=["GET"])
def dashboard_stats():
    """Return aggregated stats matching the GUI's dashboard stat cards.

    Response shape (camelCase):
        {
            totalAssets, activeProjects, totalCapitalRequired,
            totalCapitalRaised, activeDeals, totalInvestors,
            openWorkOrders, riskFlags
        }
    """
    assets = Asset.query.all()
    projects = Project.query.all()
    deals = Deal.query.all()
    investors = Investor.query.all()
    work_orders = WorkOrder.query.all()
    risk_flags = RiskFlag.query.filter_by(status="Open").all()

    active_projects = [p for p in projects if p.status not in ("Complete", "Completed", "Closed")]
    active_deals = [d for d in deals if d.status in ("Active", "Open")]
    open_wos = [w for w in work_orders if w.status in ("Open", "In Progress")]

    return jsonify({
        "totalAssets": len(assets),
        "activeProjects": len(active_projects),
        "totalCapitalRequired": sum(float(d.capital_required or 0) for d in deals),
        "totalCapitalRaised": sum(float(d.capital_raised or 0) for d in deals),
        "activeDeals": len(active_deals),
        "totalInvestors": len(investors),
        "openWorkOrders": len(open_wos),
        "riskFlags": len(risk_flags),
    })


# ---------------------------------------------------------------------------
# Portfolios
# ---------------------------------------------------------------------------

@compat_bp.route("/portfolios", methods=["GET"])
def list_portfolios():
    """Return all portfolios as a flat array."""
    portfolios = Portfolio.query.all()
    return jsonify([_to_gui(p.to_dict()) for p in portfolios])


# ---------------------------------------------------------------------------
# Assets
# ---------------------------------------------------------------------------

@compat_bp.route("/assets", methods=["GET"])
def list_assets():
    """Return all assets as a flat array."""
    assets = Asset.query.all()
    return jsonify([_to_gui(a.to_dict()) for a in assets])


@compat_bp.route("/assets/<int:asset_id>", methods=["GET"])
def get_asset(asset_id):
    """Return a single asset by ID."""
    asset = Asset.query.get_or_404(asset_id)
    return jsonify(_to_gui(asset.to_dict()))


@compat_bp.route("/assets", methods=["POST"])
@_require_api_key
def create_asset():
    """Create a new asset. Expects camelCase JSON body.

    Required: portfolioId, name
    Returns (201): the created asset.
    """
    data = request.get_json()
    if not data or not data.get("name"):
        return jsonify({"error": "name is required"}), 400

    portfolio = Portfolio.query.first()
    asset = Asset(
        portfolio_id=int(data.get("portfolioId", portfolio.id if portfolio else 1)),
        name=data["name"],
        location=data.get("location", ""),
        asset_type=data.get("assetType", ""),
        square_footage=data.get("squareFootage", 0),
        status=data.get("status", "Pre-dev"),
        asset_manager=data.get("assetManager", ""),
        media=data.get("media", []),
    )
    db.session.add(asset)
    db.session.commit()
    return jsonify(_to_gui(asset.to_dict())), 201


# ---------------------------------------------------------------------------
# Projects
# ---------------------------------------------------------------------------

@compat_bp.route("/projects", methods=["GET"])
def list_projects():
    """Return all projects as a flat array."""
    projects = Project.query.all()
    return jsonify([_to_gui(p.to_dict()) for p in projects])


@compat_bp.route("/projects/<int:project_id>", methods=["GET"])
def get_project(project_id):
    """Return a single project by ID."""
    project = Project.query.get_or_404(project_id)
    return jsonify(_to_gui(project.to_dict()))


@compat_bp.route("/projects", methods=["POST"])
@_require_api_key
def create_project():
    """Create a new project. Expects camelCase JSON body.

    Required: assetId
    Returns (201): the created project.
    """
    data = request.get_json()
    if not data or not data.get("assetId"):
        return jsonify({"error": "assetId is required"}), 400

    portfolio = Portfolio.query.first()
    project = Project(
        asset_id=int(data["assetId"]),
        portfolio_id=int(data.get("portfolioId", portfolio.id if portfolio else 1)),
        phase=data.get("phase", "Planning"),
        start_date=data.get("startDate"),
        target_completion=data.get("targetCompletion"),
        budget_total=data.get("budgetTotal", 0),
        budget_actual=data.get("budgetActual", 0),
        status=data.get("status", "Planning"),
        pm_assigned=data.get("pmAssigned", ""),
        media=data.get("media", []),
    )
    db.session.add(project)
    db.session.commit()
    return jsonify(_to_gui(project.to_dict())), 201


# ---------------------------------------------------------------------------
# Deals
# ---------------------------------------------------------------------------

@compat_bp.route("/deals", methods=["GET"])
def list_deals():
    """Return all deals as a flat array."""
    deals = Deal.query.all()
    return jsonify([_to_gui(d.to_dict()) for d in deals])


@compat_bp.route("/deals/<int:deal_id>", methods=["GET"])
def get_deal(deal_id):
    """Return a single deal by ID."""
    deal = Deal.query.get_or_404(deal_id)
    return jsonify(_to_gui(deal.to_dict()))


@compat_bp.route("/deals", methods=["POST"])
@_require_api_key
def create_deal():
    """Create a new deal. Expects camelCase JSON body.

    Required: projectId
    Returns (201): the created deal.
    """
    data = request.get_json()
    if not data or not data.get("projectId"):
        return jsonify({"error": "projectId is required"}), 400

    portfolio = Portfolio.query.first()
    deal = Deal(
        project_id=int(data["projectId"]),
        portfolio_id=int(data.get("portfolioId", portfolio.id if portfolio else 1)),
        capital_required=data.get("capitalRequired", 0),
        capital_raised=data.get("capitalRaised", 0),
        return_profile=data.get("returnProfile", ""),
        duration=data.get("duration", ""),
        risk_level=data.get("riskLevel", "Medium"),
        complexity=data.get("complexity", "Moderate"),
        phase=data.get("phase", ""),
        status=data.get("status", "Draft"),
    )
    db.session.add(deal)
    db.session.commit()
    return jsonify(_to_gui(deal.to_dict())), 201


# ---------------------------------------------------------------------------
# Investors
# ---------------------------------------------------------------------------

@compat_bp.route("/investors", methods=["GET"])
def list_investors():
    """Return all investors as a flat array."""
    investors = Investor.query.all()
    return jsonify([_to_gui(i.to_dict()) for i in investors])


@compat_bp.route("/investors/<int:investor_id>", methods=["GET"])
def get_investor(investor_id):
    """Return a single investor by ID."""
    investor = Investor.query.get_or_404(investor_id)
    return jsonify(_to_gui(investor.to_dict()))


@compat_bp.route("/investors", methods=["POST"])
@_require_api_key
def create_investor():
    """Create a new investor. Expects camelCase JSON body.

    Required: name
    Returns (201): the created investor.
    """
    data = request.get_json()
    if not data or not data.get("name"):
        return jsonify({"error": "name is required"}), 400

    investor = Investor(
        name=data["name"],
        accreditation_status=data.get("accreditationStatus", "Pending"),
        check_size_min=data.get("checkSizeMin", 0),
        check_size_max=data.get("checkSizeMax", 0),
        asset_preference=data.get("assetPreference", ""),
        geography_preference=data.get("geographyPreference", ""),
        risk_tolerance=data.get("riskTolerance", ""),
        structure_preference=data.get("structurePreference", ""),
        timeline_preference=data.get("timelinePreference", ""),
        strategic_interest=data.get("strategicInterest", ""),
        tier_level=data.get("tierLevel", "Tier 1"),
        status=data.get("status", "Active"),
    )
    db.session.add(investor)
    db.session.commit()
    return jsonify(_to_gui(investor.to_dict())), 201


# ---------------------------------------------------------------------------
# Allocations
# ---------------------------------------------------------------------------

@compat_bp.route("/allocations", methods=["GET"])
def list_allocations():
    """Return all allocations as a flat array."""
    allocations = Allocation.query.order_by(Allocation.created_at.desc()).all()
    result = []
    for a in allocations:
        gui = _to_gui(a.to_dict())
        gui["timestamp"] = gui.pop("createdAt", None)
        result.append(gui)
    return jsonify(result)


@compat_bp.route("/allocations", methods=["POST"])
@_require_api_key
def create_allocation():
    """Create a new allocation. Expects camelCase JSON body.

    Required: investorId, dealId
    Returns (201): the created allocation.
    """
    data = request.get_json()
    if not data or not data.get("investorId") or not data.get("dealId"):
        return jsonify({"error": "investorId and dealId are required"}), 400

    allocation = Allocation(
        investor_id=int(data["investorId"]),
        deal_id=int(data["dealId"]),
        soft_commit_amount=data.get("softCommitAmount", 0),
        hard_commit_amount=data.get("hardCommitAmount", 0),
        status=data.get("status", "Pending"),
        notes=data.get("notes", ""),
    )
    db.session.add(allocation)
    db.session.commit()

    gui = _to_gui(allocation.to_dict())
    gui["timestamp"] = gui.pop("createdAt", None)
    return jsonify(gui), 201


# ---------------------------------------------------------------------------
# Milestones
# ---------------------------------------------------------------------------

@compat_bp.route("/milestones", methods=["GET"])
def list_milestones():
    """Return all milestones as a flat array."""
    milestones = Milestone.query.order_by(Milestone.target_date).all()
    return jsonify([_to_gui(m.to_dict()) for m in milestones])


@compat_bp.route("/milestones/project/<int:project_id>", methods=["GET"])
def milestones_by_project(project_id):
    """Return milestones filtered by project ID."""
    milestones = Milestone.query.filter_by(project_id=project_id).order_by(Milestone.target_date).all()
    return jsonify([_to_gui(m.to_dict()) for m in milestones])


@compat_bp.route("/milestones", methods=["POST"])
@_require_api_key
def create_milestone():
    """Create a new milestone. Expects camelCase JSON body.

    Required: projectId, name
    Returns (201): the created milestone.
    """
    data = request.get_json()
    if not data or not data.get("projectId") or not data.get("name"):
        return jsonify({"error": "projectId and name are required"}), 400

    portfolio = Portfolio.query.first()
    milestone = Milestone(
        project_id=int(data["projectId"]),
        portfolio_id=int(data.get("portfolioId", portfolio.id if portfolio else 1)),
        name=data["name"],
        category=data.get("category", ""),
        target_date=data.get("targetDate"),
        completion_date=data.get("completionDate"),
        status=data.get("status", "Pending"),
        delay_explanation=data.get("delayExplanation", ""),
        risk_flag=data.get("riskFlag", False),
    )
    db.session.add(milestone)
    db.session.commit()
    return jsonify(_to_gui(milestone.to_dict())), 201


# ---------------------------------------------------------------------------
# Vendors
# ---------------------------------------------------------------------------

@compat_bp.route("/vendors", methods=["GET"])
def list_vendors():
    """Return all vendors as a flat array."""
    vendors = Vendor.query.all()
    return jsonify([_to_gui(v.to_dict()) for v in vendors])


@compat_bp.route("/vendors/<int:vendor_id>", methods=["GET"])
def get_vendor(vendor_id):
    """Return a single vendor by ID."""
    vendor = Vendor.query.get_or_404(vendor_id)
    return jsonify(_to_gui(vendor.to_dict()))


@compat_bp.route("/vendors", methods=["POST"])
@_require_api_key
def create_vendor():
    """Create a new vendor. Expects camelCase JSON body.

    Required: assetId, name
    Returns (201): the created vendor.
    """
    data = request.get_json()
    if not data or not data.get("assetId") or not data.get("name"):
        return jsonify({"error": "assetId and name are required"}), 400

    portfolio = Portfolio.query.first()
    vendor = Vendor(
        asset_id=int(data["assetId"]),
        portfolio_id=int(data.get("portfolioId", portfolio.id if portfolio else 1)),
        name=data["name"],
        type=data.get("type", ""),
        coi_status=data.get("coiStatus", "Pending"),
        sla_type=data.get("slaType", "Standard"),
        performance_score=data.get("performanceScore", 0),
    )
    db.session.add(vendor)
    db.session.commit()
    return jsonify(_to_gui(vendor.to_dict())), 201


# ---------------------------------------------------------------------------
# Work Orders
# ---------------------------------------------------------------------------

@compat_bp.route("/work-orders", methods=["GET"])
def list_work_orders():
    """Return all work orders as a flat array."""
    work_orders = WorkOrder.query.order_by(WorkOrder.created_at.desc()).all()
    return jsonify([_to_gui(wo.to_dict()) for wo in work_orders])


@compat_bp.route("/work-orders/vendor/<int:vendor_id>", methods=["GET"])
def work_orders_by_vendor(vendor_id):
    """Return work orders filtered by vendor ID."""
    work_orders = WorkOrder.query.filter_by(vendor_id=vendor_id).all()
    return jsonify([_to_gui(wo.to_dict()) for wo in work_orders])


@compat_bp.route("/work-orders", methods=["POST"])
@_require_api_key
def create_work_order():
    """Create a new work order. Expects camelCase JSON body.

    Required: vendorId, assetId
    Returns (201): the created work order.
    """
    data = request.get_json()
    if not data or not data.get("vendorId") or not data.get("assetId"):
        return jsonify({"error": "vendorId and assetId are required"}), 400

    portfolio = Portfolio.query.first()
    wo = WorkOrder(
        vendor_id=int(data["vendorId"]),
        asset_id=int(data["assetId"]),
        portfolio_id=int(data.get("portfolioId", portfolio.id if portfolio else 1)),
        type=data.get("type", ""),
        priority=data.get("priority", "Medium"),
        cost=data.get("cost", 0),
        capex_flag=data.get("capExFlag", False),
        status=data.get("status", "Open"),
        description=data.get("description"),
    )
    db.session.add(wo)
    db.session.commit()
    return jsonify(_to_gui(wo.to_dict())), 201


# ---------------------------------------------------------------------------
# Risk Flags
# ---------------------------------------------------------------------------

@compat_bp.route("/risk-flags", methods=["GET"])
def list_risk_flags():
    """Return all risk flags as a flat array."""
    risk_flags = RiskFlag.query.order_by(RiskFlag.created_at.desc()).all()
    return jsonify([_to_gui(r.to_dict()) for r in risk_flags])


@compat_bp.route("/risk-flags/project/<int:project_id>", methods=["GET"])
def risk_flags_by_project(project_id):
    """Return risk flags filtered by project ID."""
    risk_flags = RiskFlag.query.filter_by(project_id=project_id).order_by(RiskFlag.created_at.desc()).all()
    return jsonify([_to_gui(r.to_dict()) for r in risk_flags])


# ---------------------------------------------------------------------------
# Asset mutations (PUT / DELETE)
# ---------------------------------------------------------------------------

@compat_bp.route("/assets/<int:asset_id>", methods=["PUT"])
@_require_api_key
def update_asset(asset_id):
    """Update an asset. Expects camelCase JSON body."""
    asset = Asset.query.get_or_404(asset_id)
    data = request.get_json() or {}
    if "name" in data: asset.name = data["name"]
    if "location" in data: asset.location = data["location"]
    if "assetType" in data: asset.asset_type = data["assetType"]
    if "squareFootage" in data: asset.square_footage = data["squareFootage"]
    if "status" in data: asset.status = data["status"]
    if "assetManager" in data: asset.asset_manager = data["assetManager"]
    if "media" in data: asset.media = data["media"]
    db.session.commit()
    return jsonify(_to_gui(asset.to_dict()))


@compat_bp.route("/assets/<int:asset_id>", methods=["DELETE"])
@_require_api_key
def delete_asset(asset_id):
    """Delete an asset."""
    asset = Asset.query.get_or_404(asset_id)
    db.session.delete(asset)
    db.session.commit()
    return jsonify({"deleted": True})


# ---------------------------------------------------------------------------
# Project mutations (PUT / DELETE)
# ---------------------------------------------------------------------------

@compat_bp.route("/projects/<int:project_id>", methods=["PUT"])
@_require_api_key
def update_project(project_id):
    """Update a project. Expects camelCase JSON body."""
    project = Project.query.get_or_404(project_id)
    data = request.get_json() or {}
    if "phase" in data: project.phase = data["phase"]
    if "startDate" in data: project.start_date = data["startDate"]
    if "targetCompletion" in data: project.target_completion = data["targetCompletion"]
    if "budgetTotal" in data: project.budget_total = data["budgetTotal"]
    if "budgetActual" in data: project.budget_actual = data["budgetActual"]
    if "status" in data: project.status = data["status"]
    if "pmAssigned" in data: project.pm_assigned = data["pmAssigned"]
    if "media" in data: project.media = data["media"]
    db.session.commit()
    return jsonify(_to_gui(project.to_dict()))


@compat_bp.route("/projects/<int:project_id>", methods=["DELETE"])
@_require_api_key
def delete_project(project_id):
    """Delete a project."""
    project = Project.query.get_or_404(project_id)
    db.session.delete(project)
    db.session.commit()
    return jsonify({"deleted": True})


# ---------------------------------------------------------------------------
# Deal mutations (PUT / DELETE)
# ---------------------------------------------------------------------------

@compat_bp.route("/deals/<int:deal_id>", methods=["PUT"])
@_require_api_key
def update_deal(deal_id):
    """Update a deal. Expects camelCase JSON body."""
    deal = Deal.query.get_or_404(deal_id)
    data = request.get_json() or {}
    if "capitalRequired" in data: deal.capital_required = data["capitalRequired"]
    if "capitalRaised" in data: deal.capital_raised = data["capitalRaised"]
    if "returnProfile" in data: deal.return_profile = data["returnProfile"]
    if "duration" in data: deal.duration = data["duration"]
    if "riskLevel" in data: deal.risk_level = data["riskLevel"]
    if "complexity" in data: deal.complexity = data["complexity"]
    if "phase" in data: deal.phase = data["phase"]
    if "status" in data: deal.status = data["status"]
    db.session.commit()
    return jsonify(_to_gui(deal.to_dict()))


@compat_bp.route("/deals/<int:deal_id>", methods=["DELETE"])
@_require_api_key
def delete_deal(deal_id):
    """Delete a deal."""
    deal = Deal.query.get_or_404(deal_id)
    db.session.delete(deal)
    db.session.commit()
    return jsonify({"deleted": True})


# ---------------------------------------------------------------------------
# Investor mutations (PUT / DELETE)
# ---------------------------------------------------------------------------

@compat_bp.route("/investors/<int:investor_id>", methods=["PUT"])
@_require_api_key
def update_investor(investor_id):
    """Update an investor. Expects camelCase JSON body."""
    investor = Investor.query.get_or_404(investor_id)
    data = request.get_json() or {}
    if "name" in data: investor.name = data["name"]
    if "accreditationStatus" in data: investor.accreditation_status = data["accreditationStatus"]
    if "checkSizeMin" in data: investor.check_size_min = data["checkSizeMin"]
    if "checkSizeMax" in data: investor.check_size_max = data["checkSizeMax"]
    if "assetPreference" in data: investor.asset_preference = data["assetPreference"]
    if "geographyPreference" in data: investor.geography_preference = data["geographyPreference"]
    if "riskTolerance" in data: investor.risk_tolerance = data["riskTolerance"]
    if "structurePreference" in data: investor.structure_preference = data["structurePreference"]
    if "timelinePreference" in data: investor.timeline_preference = data["timelinePreference"]
    if "strategicInterest" in data: investor.strategic_interest = data["strategicInterest"]
    if "tierLevel" in data: investor.tier_level = data["tierLevel"]
    if "status" in data: investor.status = data["status"]
    db.session.commit()
    return jsonify(_to_gui(investor.to_dict()))


@compat_bp.route("/investors/<int:investor_id>", methods=["DELETE"])
@_require_api_key
def delete_investor(investor_id):
    """Delete an investor."""
    investor = Investor.query.get_or_404(investor_id)
    db.session.delete(investor)
    db.session.commit()
    return jsonify({"deleted": True})


# ---------------------------------------------------------------------------
# Allocation mutations (PUT / DELETE)
# ---------------------------------------------------------------------------

@compat_bp.route("/allocations/<int:allocation_id>", methods=["PUT"])
@_require_api_key
def update_allocation(allocation_id):
    """Update an allocation. Expects camelCase JSON body."""
    allocation = Allocation.query.get_or_404(allocation_id)
    data = request.get_json() or {}
    if "softCommitAmount" in data: allocation.soft_commit_amount = data["softCommitAmount"]
    if "hardCommitAmount" in data: allocation.hard_commit_amount = data["hardCommitAmount"]
    if "status" in data: allocation.status = data["status"]
    if "notes" in data: allocation.notes = data["notes"]
    db.session.commit()
    gui = _to_gui(allocation.to_dict())
    gui["timestamp"] = gui.pop("createdAt", None)
    return jsonify(gui)


@compat_bp.route("/allocations/<int:allocation_id>", methods=["DELETE"])
@_require_api_key
def delete_allocation(allocation_id):
    """Delete an allocation."""
    allocation = Allocation.query.get_or_404(allocation_id)
    db.session.delete(allocation)
    db.session.commit()
    return jsonify({"deleted": True})


# ---------------------------------------------------------------------------
# Milestone mutations (PUT / DELETE)
# ---------------------------------------------------------------------------

@compat_bp.route("/milestones/<int:milestone_id>", methods=["PUT"])
@_require_api_key
def update_milestone(milestone_id):
    """Update a milestone. Expects camelCase JSON body."""
    milestone = Milestone.query.get_or_404(milestone_id)
    data = request.get_json() or {}
    if "name" in data: milestone.name = data["name"]
    if "category" in data: milestone.category = data["category"]
    if "targetDate" in data: milestone.target_date = data["targetDate"]
    if "completionDate" in data: milestone.completion_date = data["completionDate"]
    if "status" in data: milestone.status = data["status"]
    if "delayExplanation" in data: milestone.delay_explanation = data["delayExplanation"]
    if "riskFlag" in data: milestone.risk_flag = data["riskFlag"]
    db.session.commit()
    return jsonify(_to_gui(milestone.to_dict()))


@compat_bp.route("/milestones/<int:milestone_id>", methods=["DELETE"])
@_require_api_key
def delete_milestone(milestone_id):
    """Delete a milestone."""
    milestone = Milestone.query.get_or_404(milestone_id)
    db.session.delete(milestone)
    db.session.commit()
    return jsonify({"deleted": True})


# ---------------------------------------------------------------------------
# Vendor mutations (PUT / DELETE)
# ---------------------------------------------------------------------------

@compat_bp.route("/vendors/<int:vendor_id>", methods=["PUT"])
@_require_api_key
def update_vendor(vendor_id):
    """Update a vendor. Expects camelCase JSON body."""
    vendor = Vendor.query.get_or_404(vendor_id)
    data = request.get_json() or {}
    if "name" in data: vendor.name = data["name"]
    if "type" in data: vendor.type = data["type"]
    if "coiStatus" in data: vendor.coi_status = data["coiStatus"]
    if "slaType" in data: vendor.sla_type = data["slaType"]
    if "performanceScore" in data: vendor.performance_score = data["performanceScore"]
    db.session.commit()
    return jsonify(_to_gui(vendor.to_dict()))


@compat_bp.route("/vendors/<int:vendor_id>", methods=["DELETE"])
@_require_api_key
def delete_vendor(vendor_id):
    """Delete a vendor."""
    vendor = Vendor.query.get_or_404(vendor_id)
    db.session.delete(vendor)
    db.session.commit()
    return jsonify({"deleted": True})


# ---------------------------------------------------------------------------
# Work Order mutations (PUT / DELETE)
# ---------------------------------------------------------------------------

@compat_bp.route("/work-orders/<int:wo_id>", methods=["PUT"])
@_require_api_key
def update_work_order(wo_id):
    """Update a work order. Expects camelCase JSON body."""
    wo = WorkOrder.query.get_or_404(wo_id)
    data = request.get_json() or {}
    if "type" in data: wo.type = data["type"]
    if "priority" in data: wo.priority = data["priority"]
    if "cost" in data: wo.cost = data["cost"]
    if "capExFlag" in data: wo.capex_flag = data["capExFlag"]
    if "status" in data: wo.status = data["status"]
    if "completionDate" in data: wo.completion_date = data["completionDate"]
    if "description" in data: wo.description = data["description"]
    db.session.commit()
    return jsonify(_to_gui(wo.to_dict()))


@compat_bp.route("/work-orders/<int:wo_id>", methods=["DELETE"])
@_require_api_key
def delete_work_order(wo_id):
    """Delete a work order."""
    wo = WorkOrder.query.get_or_404(wo_id)
    db.session.delete(wo)
    db.session.commit()
    return jsonify({"deleted": True})


# ---------------------------------------------------------------------------
# Risk Flag mutations (POST / PUT / DELETE)
# ---------------------------------------------------------------------------

@compat_bp.route("/risk-flags", methods=["POST"])
@_require_api_key
def create_risk_flag():
    """Create a new risk flag. Expects camelCase JSON body.

    Required: projectId
    Returns (201): the created risk flag.
    """
    data = request.get_json()
    if not data or not data.get("projectId"):
        return jsonify({"error": "projectId is required"}), 400

    portfolio = Portfolio.query.first()
    rf = RiskFlag(
        project_id=int(data["projectId"]),
        portfolio_id=int(data.get("portfolioId", portfolio.id if portfolio else 1)),
        category=data.get("category", ""),
        severity=data.get("severity", "Medium"),
        description=data.get("description", ""),
        status=data.get("status", "Open"),
    )
    db.session.add(rf)
    db.session.commit()
    return jsonify(_to_gui(rf.to_dict())), 201


@compat_bp.route("/risk-flags/<int:rf_id>", methods=["PUT"])
@_require_api_key
def update_risk_flag(rf_id):
    """Update a risk flag. Expects camelCase JSON body."""
    rf = RiskFlag.query.get_or_404(rf_id)
    data = request.get_json() or {}
    if "category" in data: rf.category = data["category"]
    if "severity" in data: rf.severity = data["severity"]
    if "description" in data: rf.description = data["description"]
    if "status" in data:
        rf.status = data["status"]
        if data["status"] == "Resolved" and not rf.resolved_at:
            rf.resolved_at = datetime.utcnow()
    db.session.commit()
    return jsonify(_to_gui(rf.to_dict()))


@compat_bp.route("/risk-flags/<int:rf_id>", methods=["DELETE"])
@_require_api_key
def delete_risk_flag(rf_id):
    """Delete a risk flag."""
    rf = RiskFlag.query.get_or_404(rf_id)
    db.session.delete(rf)
    db.session.commit()
    return jsonify({"deleted": True})


# ---------------------------------------------------------------------------
# S3 File Upload (Phase 4 - Profile Enhancement)
# ---------------------------------------------------------------------------

@compat_bp.route("/upload", methods=["POST"])
@cross_origin(origin="*", methods=["POST"], allow_headers=["Content-Type", "Authorization", "X-API-Key"], supports_credentials=True)
@_require_api_key
def upload_file():
    """Handle file uploads for profile avatars.

    Accepts a multipart 'file' field. Converts the image to a base64 data URL
    and stores it directly in the database — no S3 or external storage required.
    If a 'userId' form field is provided, the data URL is persisted to that
    user's profile_image column immediately.

    Returns (201): { "url": "<data_url>", "key": "<path>" }
    """
    import base64
    import io
    from app.routes.uploads import _image_to_data_url, MAX_UPLOAD_BYTES

    file = request.files.get("file")
    path = request.form.get("path", "avatar")
    user_id = request.form.get("userId")

    if not file:
        return jsonify({"error": "File is required"}), 400

    # Read and validate size
    file_data = file.read()
    if not file_data:
        return jsonify({"error": "Empty file received"}), 400
    if len(file_data) > MAX_UPLOAD_BYTES:
        return jsonify({"error": f"File too large. Maximum size is {MAX_UPLOAD_BYTES // (1024*1024)} MB"}), 400

    # Convert to base64 data URL (no S3 needed)
    mime_type = file.content_type or "image/jpeg"
    data_url = _image_to_data_url(file_data, mime_type)

    # Persist to user's profile_image if userId provided
    if user_id:
        try:
            user = User.query.get(int(user_id))
            if user:
                user.profile_image = data_url
                db.session.commit()
        except Exception:
            pass  # Non-fatal — still return the URL

    return jsonify({"url": data_url, "key": path}), 201

@compat_bp.route("/connection-requests", methods=["GET"])
@_require_api_key
def list_connection_requests():
    """List connection requests for the current user (as receiver)."""
    user_id = request.headers.get("X-User-ID")
    if not user_id:
        return jsonify({"error": "X-User-ID header required"}), 400
    
    requests = ConnectionRequest.query.filter_by(receiver_id=int(user_id)).all()
    return jsonify([r.to_dict() for r in requests])


@compat_bp.route("/connection-requests", methods=["POST"])
@_require_api_key
def send_connection_request():
    """Send a connection request to another user."""
    user_id = request.headers.get("X-User-ID")
    if not user_id:
        return jsonify({"error": "X-User-ID header required"}), 400
    
    data = request.get_json()
    if not data or not data.get("receiverId"):
        return jsonify({"error": "receiverId is required"}), 400
    
    sender_id = int(user_id)
    receiver_id = int(data["receiverId"])
    message = data.get("message", "")
    
    existing = ConnectionRequest.query.filter(
        (ConnectionRequest.sender_id == sender_id and ConnectionRequest.receiver_id == receiver_id) |
        (ConnectionRequest.sender_id == receiver_id and ConnectionRequest.receiver_id == sender_id)
    ).first()
    
    if existing:
        return jsonify({"error": "Connection already exists or request pending"}), 400
    
    req = ConnectionRequest(
        sender_id=sender_id,
        receiver_id=receiver_id,
        message=message,
        status="pending"
    )
    db.session.add(req)
    db.session.commit()
    
    return jsonify(req.to_dict()), 201


@compat_bp.route("/connection-requests/<int:req_id>", methods=["PUT"])
@_require_api_key
def update_connection_request(req_id):
    """Accept or decline a connection request."""
    user_id = request.headers.get("X-User-ID")
    if not user_id:
        return jsonify({"error": "X-User-ID header required"}), 400
    
    req = ConnectionRequest.query.get_or_404(req_id)
    
    if req.receiver_id != int(user_id):
        return jsonify({"error": " Not authorized to update this request"}), 403
    
    data = request.get_json()
    if not data or not data.get("status"):
        return jsonify({"error": "status is required"}), 400
    
    if data["status"] not in ("accepted", "declined"):
        return jsonify({"error": "status must be 'accepted' or 'declined'"}), 400
    
    req.status = data["status"]
    req.responded_at = datetime.utcnow()
    db.session.commit()
    
    return jsonify(req.to_dict())


@compat_bp.route("/connection-requests/<int:req_id>", methods=["DELETE"])
@_require_api_key
def delete_connection_request(req_id):
    """Withdraw a connection request."""
    user_id = request.headers.get("X-User-ID")
    if not user_id:
        return jsonify({"error": "X-User-ID header required"}), 400
    
    req = ConnectionRequest.query.get_or_404(req_id)
    
    if req.sender_id != int(user_id):
        return jsonify({"error": "Not authorized to delete this request"}), 403
    
    db.session.delete(req)
    db.session.commit()
    
    return jsonify({"deleted": True})


@compat_bp.route("/connections", methods=["GET"])
@_require_api_key
def list_connections():
    """Get all connected users for the current user."""
    user_id = request.headers.get("X-User-ID")
    if not user_id:
        return jsonify({"error": "X-User-ID header required"}), 400
    
    requests = ConnectionRequest.query.filter(
        (ConnectionRequest.sender_id == int(user_id)) | (ConnectionRequest.receiver_id == int(user_id))
    ).filter_by(status="accepted").all()
    
    connections = []
    for req in requests:
        if req.sender_id == int(user_id):
            connections.append(req.receiver.to_dict())
        else:
            connections.append(req.sender.to_dict())
    
    return jsonify(connections)


@compat_bp.route("/connection-pending", methods=["GET"])
@_require_api_key
def list_pending_requests():
    """Get all pending incoming connection requests for the current user."""
    user_id = request.headers.get("X-User-ID")
    if not user_id:
        return jsonify({"error": "X-User-ID header required"}), 400
    
    requests = ConnectionRequest.query.filter_by(receiver_id=int(user_id), status="pending").all()
    return jsonify([r.to_dict() for r in requests])


@compat_bp.route("/conversations", methods=["GET"])
@_require_api_key
def list_conversations():
    """List all conversations for the current user."""
    user_id = request.headers.get("X-User-ID")
    if not user_id:
        return jsonify({"error": "X-User-ID header required"}), 400
    
    conversations = Conversation.query.filter(
        (Conversation.user_id1 == int(user_id)) | (Conversation.user_id2 == int(user_id))
    ).all()
    
    return jsonify([c.to_dict() for c in conversations])


@compat_bp.route("/conversations", methods=["POST"])
@_require_api_key
def create_conversation():
    """Create or get a conversation with another user."""
    user_id = request.headers.get("X-User-ID")
    if not user_id:
        return jsonify({"error": "X-User-ID header required"}), 400
    
    data = request.get_json()
    if not data or not data.get("userId"):
        return jsonify({"error": "userId is required"}), 400
    
    user1_id = int(user_id)
    user2_id = int(data["userId"])
    
    if user1_id == user2_id:
        return jsonify({"error": "Cannot create conversation with yourself"}), 400
    
    existing = Conversation.query.filter(
        (Conversation.user_id1 == user1_id and Conversation.user_id2 == user2_id) |
        (Conversation.user_id1 == user2_id and Conversation.user_id2 == user1_id)
    ).first()
    
    if existing:
        return jsonify(existing.to_dict())
    
    conv = Conversation(user_id1=user1_id, user_id2=user2_id)
    db.session.add(conv)
    db.session.commit()
    
    return jsonify(conv.to_dict()), 201


@compat_bp.route("/messages", methods=["GET"])
@_require_api_key
def list_messages():
    """Get messages in a conversation."""
    user_id = request.headers.get("X-User-ID")
    if not user_id:
        return jsonify({"error": "X-User-ID header required"}), 400
    
    conversation_id = request.args.get("conversationId")
    if not conversation_id:
        return jsonify({"error": "conversationId is required"}), 400
    
    conv = Conversation.query.get_or_404(int(conversation_id))
    
    if conv.user_id1 != int(user_id) and conv.user_id2 != int(user_id):
        return jsonify({"error": "Not authorized to view this conversation"}), 403
    
    messages = Message.query.filter_by(conversation_id=int(conversation_id)).all()
    return jsonify([m.to_dict() for m in messages])


@compat_bp.route("/messages", methods=["POST"])
@_require_api_key
def send_message():
    """Send a message in a conversation."""
    user_id = request.headers.get("X-User-ID")
    if not user_id:
        return jsonify({"error": "X-User-ID header required"}), 400
    
    data = request.get_json()
    if not data or not data.get("conversationId") or not data.get("content"):
        return jsonify({"error": "conversationId and content are required"}), 400
    
    conv = Conversation.query.get_or_404(int(data["conversationId"]))
    
    if conv.user_id1 != int(user_id) and conv.user_id2 != int(user_id):
        return jsonify({"error": "Not authorized to send messages to this conversation"}), 403
    
    msg = Message(
        conversation_id=int(data["conversationId"]),
        sender_id=int(user_id),
        content=data["content"]
    )
    db.session.add(msg)
    db.session.commit()
    
    return jsonify(msg.to_dict()), 201


@compat_bp.route("/messages/<int:msg_id>", methods=["PUT"])
@_require_api_key
def update_message(msg_id):
    """Mark a message as read."""
    user_id = request.headers.get("X-User-ID")
    if not user_id:
        return jsonify({"error": "X-User-ID header required"}), 400
    
    msg = Message.query.get_or_404(msg_id)
    
    conv = Conversation.query.get_or_404(msg.conversation_id)
    if conv.user_id1 != int(user_id) and conv.user_id2 != int(user_id):
        return jsonify({"error": "Not authorized to update this message"}), 403
    
    msg.read_at = datetime.utcnow()
    db.session.commit()
    
    return jsonify(msg.to_dict())


@compat_bp.route("/messages/<int:msg_id>", methods=["DELETE"])
@_require_api_key
def delete_message(msg_id):
    """Delete a message."""
    user_id = request.headers.get("X-User-ID")
    if not user_id:
        return jsonify({"error": "X-User-ID header required"}), 400
    
    msg = Message.query.get_or_404(msg_id)
    
    if msg.sender_id != int(user_id):
        return jsonify({"error": "Not authorized to delete this message"}), 403
    
    db.session.delete(msg)
    db.session.commit()
    
    return jsonify({"deleted": True})


@compat_bp.route("/users/<int:user_id>", methods=["PUT"])
@_require_api_key
def update_user(user_id):
    """Update a user's profile with all new Phase 4 fields."""
    user = User.query.get_or_404(user_id)
    data = request.get_json() or {}
    
    # Profile fields
    if "profileType" in data: user.profile_type = data["profileType"]
    if "profileStatus" in data: user.profile_status = data["profileStatus"]
    if "title" in data: user.title = data["title"]
    if "organization" in data: user.organization = data["organization"]
    if "linkedInUrl" in data: user.linked_in_url = data["linkedInUrl"]
    if "bio" in data: user.bio = data["bio"]
    
    # Investor fields
    if "geographicFocus" in data: user.geographic_focus = data["geographicFocus"]
    if "investmentStage" in data: user.investment_stage = data["investmentStage"]
    if "targetReturn" in data: user.target_return = data["targetReturn"]
    if "checkSizeMin" in data: user.check_size_min = data["checkSizeMin"]
    if "checkSizeMax" in data: user.check_size_max = data["checkSizeMax"]
    if "riskTolerance" in data: user.risk_tolerance = data["riskTolerance"]
    if "strategicInterest" in data: user.strategic_interest = data["strategicInterest"]
    
    # Vendor fields
    if "serviceTypes" in data: user.service_types = data["serviceTypes"]
    if "geographicServiceArea" in data: user.geographic_service_area = data["geographicServiceArea"]
    if "yearsOfExperience" in data: user.years_of_experience = data["yearsOfExperience"]
    if "certifications" in data: user.certifications = data["certifications"]
    if "averageProjectSize" in data: user.average_project_size = data["averageProjectSize"]
    
    # Developer fields
    if "developmentFocus" in data: user.development_focus = data["developmentFocus"]
    if "developmentType" in data: user.development_type = data["developmentType"]
    if "teamSize" in data: user.team_size = data["teamSize"]
    if "portfolioValue" in data: user.portfolio_value = data["portfolioValue"]
    
    db.session.commit()
    return jsonify(_to_gui(user.to_dict()))


@compat_bp.route("/upload", methods=["POST"])
@_require_api_key
def upload_media():
    """Upload a media file and return a base64 data URL.

    Accepts either:
    - multipart/form-data with an 'image' field
    - JSON body with 'imageData' field containing base64-encoded image

    Returns {url: "data:image/...;base64,..."} for direct use in img src.
    """
    import base64
    import io

    # Handle JSON body with base64 image
    if request.is_json:
        data = request.get_json() or {}
        image_data = data.get("imageData")
        if not image_data:
            return jsonify({"error": "No image provided"}), 400

        # Decode base64
        try:
            if image_data.startswith("data:"):
                header, encoded = image_data.split(",", 1)
                mime_type = header.split(";")[0].replace("data:", "") or "image/jpeg"
                file_data = base64.b64decode(encoded)
            else:
                file_data = base64.b64decode(image_data)
                mime_type = "image/jpeg"
        except Exception:
            return jsonify({"error": "Invalid base64 data"}), 400

        if len(file_data) > 5 * 1024 * 1024:
            return jsonify({"error": "File too large (max 5MB)"}), 400

        encoded_result = base64.b64encode(file_data).decode("utf-8")
        data_url = f"data:{mime_type};base64,{encoded_result}"
        return jsonify({"url": data_url, "key": data.get("name", "image")})

    # Handle multipart form data
    if "image" not in request.files:
        return jsonify({"error": "No image provided"}), 400

    file = request.files["image"]
    if not file.filename:
        return jsonify({"error": "Empty file"}), 400

    file_data = file.read()
    if len(file_data) > 5 * 1024 * 1024:
        return jsonify({"error": "File too large (max 5MB)"}), 400

    mime_type = file.content_type or "image/jpeg"
    if not mime_type.startswith("image/"):
        return jsonify({"error": "Only image files allowed"}), 400

    encoded = base64.b64encode(file_data).decode("utf-8")
    data_url = f"data:{mime_type};base64,{encoded}"

    return jsonify({"url": data_url, "key": file.filename or "image"})
