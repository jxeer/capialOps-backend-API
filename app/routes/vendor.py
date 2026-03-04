"""
CapitalOps API - Module 3: Asset & Vendor Control Routes

Handles vendor management, work order tracking, and operational discipline.

Access restricted to:
    - sponsor_admin:      Full access (add vendors, create/update work orders)
    - general_contractor: View vendors, create/update work orders
    - vendor:             View own work orders only (future scoping)

Routes:
    GET  /api/vendor/                          — Vendor overview with stats
    POST /api/vendor/                          — Register a new vendor
    GET  /api/vendor/work-orders               — List all work orders
    POST /api/vendor/work-orders               — Create a new work order
    PATCH /api/vendor/work-orders/<id>         — Update work order status/cost
"""

from flask import Blueprint, request, jsonify, g
from app import db
from app.models import Vendor, WorkOrder, Asset, Portfolio
from app.auth_utils import jwt_required, role_required

vendor_bp = Blueprint("vendor", __name__)

# Roles permitted to access Asset & Vendor Control routes
VENDOR_ROLES = ("sponsor_admin", "general_contractor", "vendor")


@vendor_bp.route("/", methods=["GET"])
@jwt_required
@role_required(*VENDOR_ROLES)
def index():
    """
    Vendor & Asset Control overview with computed stats.

    Returns:
        - Summary stats: total vendors, expired COIs, open work orders,
          cost breakdown (total, CapEx, OpEx)
        - Full vendor listing
        - Work order listing (sorted by most recent)
        - Asset listing
    """
    vendors = Vendor.query.all()
    work_orders = WorkOrder.query.order_by(WorkOrder.created_at.desc()).all()
    assets = Asset.query.all()

    # Compute summary statistics
    coi_expired = sum(1 for v in vendors if v.coi_status == "Expired")
    open_orders = sum(1 for wo in work_orders if wo.status not in ("Complete", "Cancelled"))
    total_cost = sum(float(wo.cost or 0) for wo in work_orders)
    capex_total = sum(float(wo.cost or 0) for wo in work_orders if wo.capex_flag)

    stats = {
        "total_vendors": len(vendors),
        "coi_expired": coi_expired,
        "open_orders": open_orders,
        "total_cost": total_cost,
        "capex_total": capex_total,
        "opex_total": total_cost - capex_total,
    }

    return jsonify({
        "stats": stats,
        "vendors": [v.to_dict() for v in vendors],
        "work_orders": [wo.to_dict() for wo in work_orders],
        "assets": [a.to_dict() for a in assets],
    })


@vendor_bp.route("/", methods=["POST"])
@jwt_required
@role_required("sponsor_admin")
def create_vendor():
    """
    Register a new vendor for an asset. Sponsor Admin only.

    Expects JSON body:
        {
            "asset_id": 1,
            "name": "Vendor Name",
            "type": "Electrical",
            "coi_status": "Current",
            "sla_type": "Standard",
            "performance_score": 85
        }

    Returns (201): Created vendor object.
    Returns (400): If asset_id or name is missing.
    """
    data = request.get_json()
    if not data or not data.get("asset_id") or not data.get("name"):
        return jsonify({"error": "asset_id and name are required"}), 400

    # Auto-assign to the current portfolio
    portfolio = Portfolio.query.first()

    vendor = Vendor(
        asset_id=data["asset_id"],
        portfolio_id=portfolio.id,
        name=data["name"],
        type=data.get("type", ""),
        coi_status=data.get("coi_status", "Pending"),
        sla_type=data.get("sla_type", "Standard"),
        performance_score=data.get("performance_score", 0),
    )
    db.session.add(vendor)
    db.session.commit()

    return jsonify({"vendor": vendor.to_dict()}), 201


@vendor_bp.route("/work-orders", methods=["GET"])
@jwt_required
@role_required(*VENDOR_ROLES)
def list_work_orders():
    """List all work orders, sorted by most recent first."""
    work_orders = WorkOrder.query.order_by(WorkOrder.created_at.desc()).all()
    return jsonify({"work_orders": [wo.to_dict() for wo in work_orders]})


@vendor_bp.route("/work-orders", methods=["POST"])
@jwt_required
@role_required("sponsor_admin", "general_contractor")
def create_work_order():
    """
    Create a new work order.

    Expects JSON body:
        {
            "vendor_id": 1,
            "asset_id": 1,
            "type": "Maintenance",
            "priority": "Normal",
            "cost": 5000,
            "capex_flag": false
        }

    Returns (201): Created work order object.
    Returns (400): If vendor_id or asset_id is missing.
    """
    data = request.get_json()
    if not data or not data.get("vendor_id") or not data.get("asset_id"):
        return jsonify({"error": "vendor_id and asset_id are required"}), 400

    portfolio = Portfolio.query.first()

    wo = WorkOrder(
        vendor_id=data["vendor_id"],
        asset_id=data["asset_id"],
        portfolio_id=portfolio.id,
        type=data.get("type", ""),
        priority=data.get("priority", "Normal"),
        cost=data.get("cost", 0),
        capex_flag=data.get("capex_flag", False),
        status="Open",
    )
    db.session.add(wo)
    db.session.commit()

    return jsonify({"work_order": wo.to_dict()}), 201


@vendor_bp.route("/work-orders/<int:wo_id>", methods=["PATCH"])
@jwt_required
@role_required(*VENDOR_ROLES)
def update_work_order(wo_id):
    """
    Update a work order's status and/or cost.

    Expects JSON body with any of:
        {
            "status": "Complete",
            "cost": 5500
        }

    Returns (200): Updated work order object.
    """
    wo = WorkOrder.query.get_or_404(wo_id)
    data = request.get_json() or {}

    if "status" in data:
        wo.status = data["status"]
    if "cost" in data:
        wo.cost = data["cost"]

    db.session.commit()
    return jsonify({"work_order": wo.to_dict()})
