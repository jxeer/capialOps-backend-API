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
from functools import wraps
from flask import Blueprint, request, jsonify
from app import db
from app.models import (
    Portfolio, Asset, Project, Deal, Investor,
    Allocation, Milestone, Vendor, WorkOrder, RiskFlag,
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


def _to_gui(record_dict):
    """Transform a model's to_dict() output into GUI-compatible format.

    Applies two transformations:
        1. All keys converted from snake_case to camelCase
        2. The 'id' field is cast to a string (frontend uses string IDs)
    """
    result = {}
    for key, value in record_dict.items():
        camel_key = _snake_to_camel(key)
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

@compat_bp.route("/backend-status", methods=["GET"])
def backend_status():
    """Return backend connectivity info for the GUI's status badge."""
    return jsonify({
        "connected": True,
        "url": request.host_url.rstrip("/"),
        "mode": "live",
        "backendInfo": {"status": "ok", "service": "capitalops-api"},
    })


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
    result = []
    for wo in work_orders:
        gui = _to_gui(wo.to_dict())
        gui["capExFlag"] = gui.pop("capexFlag", False)
        if "description" not in gui:
            gui["description"] = ""
        result.append(gui)
    return jsonify(result)


@compat_bp.route("/work-orders/vendor/<int:vendor_id>", methods=["GET"])
def work_orders_by_vendor(vendor_id):
    """Return work orders filtered by vendor ID."""
    work_orders = WorkOrder.query.filter_by(vendor_id=vendor_id).all()
    result = []
    for wo in work_orders:
        gui = _to_gui(wo.to_dict())
        gui["capExFlag"] = gui.pop("capexFlag", False)
        if "description" not in gui:
            gui["description"] = ""
        result.append(gui)
    return jsonify(result)


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
    )
    db.session.add(wo)
    db.session.commit()

    gui = _to_gui(wo.to_dict())
    gui["capExFlag"] = gui.pop("capexFlag", False)
    gui["description"] = data.get("description", "")
    return jsonify(gui), 201


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
