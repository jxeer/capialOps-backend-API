"""
CapitalOps - Module 3: Asset & Vendor Control Routes

Handles vendor management, work order tracking, and operational discipline.
This is the foundation layer of the data flow — operational truth from
vendor/maintenance activities flows upward into Execution Control (Module 2)
and ultimately into investor transparency (Module 1).

Access restricted to:
    - sponsor_admin:      Full access (add vendors, create/update work orders)
    - general_contractor: View vendors, create/update work orders
    - vendor:             View own work orders only (future scoping)

Key features:
    - Vendor registration with COI and SLA tracking
    - Work order creation and status management
    - CapEx vs OpEx cost classification
    - Performance scoring and compliance monitoring

Routes:
    GET  /vendor/                          — Vendor & asset overview dashboard
    GET  /vendor/add                       — Add vendor form (Sponsor Admin only)
    POST /vendor/add                       — Create new vendor record
    GET  /vendor/work-orders/create        — Work order creation form
    POST /vendor/work-orders/create        — Create new work order
    POST /vendor/work-orders/<id>/update   — Update work order status/cost
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from app.models import Vendor, WorkOrder, Asset
from functools import wraps

vendor_bp = Blueprint("vendor", __name__)


def vendor_access_required(f):
    """
    Decorator to restrict access to Asset & Vendor Control routes.

    Only sponsor_admin, general_contractor, and vendor roles
    can access Module 3. Investors and PMs are redirected to the dashboard.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        if current_user.role not in ("sponsor_admin", "general_contractor", "vendor"):
            flash("Access denied.", "error")
            return redirect(url_for("dashboard.index"))
        return f(*args, **kwargs)
    return decorated


@vendor_bp.route("/")
@login_required
@vendor_access_required
def index():
    """
    Vendor & Asset Control overview dashboard.

    Displays:
        - Summary stats: total vendors, expired COIs, open work orders,
          total cost breakdown (CapEx vs OpEx)
        - Vendor listing with COI status, SLA type, and performance scores
        - Work order listing with priority, cost, and completion actions

    The COI (Certificate of Insurance) expired count is a key compliance
    metric — vendors with expired COIs need immediate attention.
    """
    vendors = Vendor.query.all()
    work_orders = WorkOrder.query.order_by(WorkOrder.created_at.desc()).all()
    assets = Asset.query.all()

    # --- Compute summary statistics ---

    # Count vendors with expired insurance certificates
    coi_expired = sum(1 for v in vendors if v.coi_status == "Expired")

    # Count work orders that are still open (not completed or cancelled)
    open_orders = sum(1 for wo in work_orders if wo.status not in ("Complete", "Cancelled"))

    # Calculate cost breakdown: total, CapEx (capital expenditures), and OpEx (operating expenses)
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

    return render_template("vendor/index.html", vendors=vendors, work_orders=work_orders, assets=assets, stats=stats)


@vendor_bp.route("/add", methods=["GET", "POST"])
@login_required
@vendor_access_required
def add_vendor():
    """
    Register a new vendor for an asset. Sponsor Admin only.

    GET:  Render the vendor registration form with asset dropdown
          and all vendor attribute fields.
    POST: Create the vendor record, auto-assigning the current portfolio,
          and redirect to the vendor listing.
    """
    # Only Sponsor Admin can register new vendors
    if current_user.role != "sponsor_admin":
        flash("Only Sponsor Admin can add vendors.", "error")
        return redirect(url_for("vendor.index"))

    assets = Asset.query.all()

    if request.method == "POST":
        # Auto-assign to the current portfolio (single portfolio for now)
        from app.models import Portfolio
        portfolio = Portfolio.query.first()

        vendor = Vendor(
            asset_id=request.form["asset_id"],
            portfolio_id=portfolio.id,
            name=request.form["name"],
            type=request.form.get("type", ""),
            coi_status=request.form.get("coi_status", "Pending"),
            sla_type=request.form.get("sla_type", "Standard"),
            performance_score=int(request.form.get("performance_score", 0)),
        )
        db.session.add(vendor)
        db.session.commit()
        flash("Vendor added successfully.", "success")
        return redirect(url_for("vendor.index"))

    return render_template("vendor/add_vendor.html", assets=assets)


@vendor_bp.route("/work-orders/create", methods=["GET", "POST"])
@login_required
@vendor_access_required
def create_work_order():
    """
    Create a new work order assigning work to a vendor.

    GET:  Render the work order creation form with vendor/asset dropdowns,
          work type, priority, cost, and CapEx classification fields.
    POST: Create the work order with "Open" status and redirect to vendor listing.

    The CapEx flag (capex_flag) distinguishes capital expenditures from
    operating expenses — this classification is important for financial
    reporting and governance.
    """
    vendors = Vendor.query.all()
    assets = Asset.query.all()

    if request.method == "POST":
        # Auto-assign to the current portfolio
        from app.models import Portfolio
        portfolio = Portfolio.query.first()

        wo = WorkOrder(
            vendor_id=request.form["vendor_id"],
            asset_id=request.form["asset_id"],
            portfolio_id=portfolio.id,
            type=request.form.get("type", ""),
            priority=request.form.get("priority", "Normal"),
            cost=request.form.get("cost", 0),
            capex_flag=request.form.get("capex_flag") == "on",  # Checkbox sends "on" when checked
            status="Open",
        )
        db.session.add(wo)
        db.session.commit()
        flash("Work order created.", "success")
        return redirect(url_for("vendor.index"))

    return render_template("vendor/create_work_order.html", vendors=vendors, assets=assets)


@vendor_bp.route("/work-orders/<int:wo_id>/update", methods=["POST"])
@login_required
@vendor_access_required
def update_work_order(wo_id):
    """
    Update a work order's status and/or cost.

    Used primarily for marking work orders as complete from the
    vendor listing page. Cost can also be updated if the final
    amount differs from the estimate.
    """
    wo = WorkOrder.query.get_or_404(wo_id)

    # Update status (e.g., Open → Complete)
    wo.status = request.form.get("status", wo.status)

    # Optionally update cost if provided
    if request.form.get("cost"):
        wo.cost = request.form["cost"]

    db.session.commit()
    flash("Work order updated.", "success")
    return redirect(url_for("vendor.index"))
