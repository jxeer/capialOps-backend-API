from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from app.models import Deal, Investor, Allocation, Project, Asset
from functools import wraps

capital_bp = Blueprint("capital", __name__)


def capital_access_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if current_user.role not in ("sponsor_admin", "investor_tier1", "investor_tier2"):
            flash("Access denied. Capital Engine requires authorization.", "error")
            return redirect(url_for("dashboard.index"))
        return f(*args, **kwargs)
    return decorated


@capital_bp.route("/")
@login_required
@capital_access_required
def index():
    deals = Deal.query.all()
    investors = Investor.query.all()
    allocations = Allocation.query.all()

    total_required = sum(float(d.capital_required or 0) for d in deals)
    total_raised = sum(float(d.capital_raised or 0) for d in deals)

    return render_template(
        "capital/index.html",
        deals=deals,
        investors=investors,
        allocations=allocations,
        total_required=total_required,
        total_raised=total_raised,
    )


@capital_bp.route("/deals")
@login_required
@capital_access_required
def deals():
    deals = Deal.query.all()
    return render_template("capital/deals.html", deals=deals)


@capital_bp.route("/deals/<int:deal_id>")
@login_required
@capital_access_required
def deal_detail(deal_id):
    deal = Deal.query.get_or_404(deal_id)
    allocations = Allocation.query.filter_by(deal_id=deal_id).all()
    investors = Investor.query.filter_by(status="Active").all()
    return render_template("capital/deal_detail.html", deal=deal, allocations=allocations, investors=investors)


@capital_bp.route("/investors")
@login_required
@capital_access_required
def investors():
    investors = Investor.query.all()
    return render_template("capital/investors.html", investors=investors)


@capital_bp.route("/investors/add", methods=["GET", "POST"])
@login_required
@capital_access_required
def add_investor():
    if current_user.role != "sponsor_admin":
        flash("Only Sponsor Admin can add investors.", "error")
        return redirect(url_for("capital.investors"))

    if request.method == "POST":
        investor = Investor(
            name=request.form["name"],
            accreditation_status=request.form.get("accreditation_status", "Pending"),
            check_size_min=request.form.get("check_size_min", 0),
            check_size_max=request.form.get("check_size_max", 0),
            asset_preference=request.form.get("asset_preference", ""),
            geography_preference=request.form.get("geography_preference", ""),
            risk_tolerance=request.form.get("risk_tolerance", ""),
            structure_preference=request.form.get("structure_preference", ""),
            timeline_preference=request.form.get("timeline_preference", ""),
            strategic_interest=request.form.get("strategic_interest", ""),
            tier_level=request.form.get("tier_level", "Tier 1"),
            status="Active",
        )
        db.session.add(investor)
        db.session.commit()
        flash("Investor added successfully.", "success")
        return redirect(url_for("capital.investors"))

    return render_template("capital/add_investor.html")


@capital_bp.route("/allocations/create", methods=["POST"])
@login_required
@capital_access_required
def create_allocation():
    if current_user.role != "sponsor_admin":
        flash("Only Sponsor Admin can create allocations.", "error")
        return redirect(url_for("capital.index"))

    allocation = Allocation(
        investor_id=request.form["investor_id"],
        deal_id=request.form["deal_id"],
        soft_commit_amount=request.form.get("soft_commit_amount", 0),
        hard_commit_amount=request.form.get("hard_commit_amount", 0),
        status="Pending",
        notes=request.form.get("notes", ""),
    )
    db.session.add(allocation)
    db.session.commit()
    flash("Allocation created successfully.", "success")
    return redirect(url_for("capital.deal_detail", deal_id=request.form["deal_id"]))


@capital_bp.route("/matching")
@login_required
@capital_access_required
def matching():
    investors = Investor.query.filter_by(status="Active").all()
    deals = Deal.query.filter(Deal.status == "Open").all()

    matches = []
    for deal in deals:
        project = deal.project
        asset = project.asset
        for investor in investors:
            score = 0
            reasons = []
            if investor.asset_preference and (investor.asset_preference == "All" or investor.asset_preference.lower() in asset.asset_type.lower()):
                score += 25
                reasons.append("Asset type match")
            if investor.risk_tolerance and investor.risk_tolerance.lower().replace("-", " ") in deal.risk_level.lower().replace("-", " "):
                score += 25
                reasons.append("Risk tolerance aligned")
            if float(investor.check_size_min or 0) <= float(deal.capital_required or 0) and float(investor.check_size_max or 0) >= float(investor.check_size_min or 0):
                score += 25
                reasons.append("Check size fit")
            if investor.accreditation_status == "Verified":
                score += 15
                reasons.append("Accredited")
            if investor.tier_level == "Tier 2":
                score += 10
                reasons.append("Priority tier")

            if score >= 25:
                matches.append({
                    "investor": investor,
                    "deal": deal,
                    "asset": asset,
                    "score": min(score, 100),
                    "reasons": reasons,
                })

    matches.sort(key=lambda x: x["score"], reverse=True)
    return render_template("capital/matching.html", matches=matches)
