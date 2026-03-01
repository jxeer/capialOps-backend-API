from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from app.models import Vendor, WorkOrder, Asset
from functools import wraps

vendor_bp = Blueprint("vendor", __name__)


def vendor_access_required(f):
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
    vendors = Vendor.query.all()
    work_orders = WorkOrder.query.order_by(WorkOrder.created_at.desc()).all()
    assets = Asset.query.all()

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

    return render_template("vendor/index.html", vendors=vendors, work_orders=work_orders, assets=assets, stats=stats)


@vendor_bp.route("/add", methods=["GET", "POST"])
@login_required
@vendor_access_required
def add_vendor():
    if current_user.role != "sponsor_admin":
        flash("Only Sponsor Admin can add vendors.", "error")
        return redirect(url_for("vendor.index"))

    assets = Asset.query.all()
    if request.method == "POST":
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
    vendors = Vendor.query.all()
    assets = Asset.query.all()

    if request.method == "POST":
        from app.models import Portfolio
        portfolio = Portfolio.query.first()
        wo = WorkOrder(
            vendor_id=request.form["vendor_id"],
            asset_id=request.form["asset_id"],
            portfolio_id=portfolio.id,
            type=request.form.get("type", ""),
            priority=request.form.get("priority", "Normal"),
            cost=request.form.get("cost", 0),
            capex_flag=request.form.get("capex_flag") == "on",
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
    wo = WorkOrder.query.get_or_404(wo_id)
    wo.status = request.form.get("status", wo.status)
    if request.form.get("cost"):
        wo.cost = request.form["cost"]
    db.session.commit()
    flash("Work order updated.", "success")
    return redirect(url_for("vendor.index"))
