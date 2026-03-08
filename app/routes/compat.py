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
from datetime import datetime
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
