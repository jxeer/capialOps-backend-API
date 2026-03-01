"""
CapitalOps - Module 1: Capital Engine Routes

Handles investor alignment, deal distribution, matching logic, and
allocation tracking. This is the investor-facing module that provides
transparency into the capital raise process.

Access restricted to:
    - sponsor_admin:   Full access (create deals, approve allocations, manage investors)
    - investor_tier1:  View matched deals, submit allocation requests
    - investor_tier2:  Priority access with enhanced reporting

Key features:
    - Capital overview dashboard with raise progress
    - Deal pipeline listing and individual deal rooms
    - Investor profile management (add/view)
    - Rule-based deal-investor matching engine
    - Allocation tracking (soft commit / hard commit)

Routes:
    GET  /capital/                  — Capital Engine overview
    GET  /capital/deals             — Deal pipeline listing
    GET  /capital/deals/<id>        — Individual deal room with allocation form
    GET  /capital/investors         — Investor profile listing
    GET  /capital/investors/add     — Add investor form (Sponsor Admin only)
    POST /capital/investors/add     — Create new investor profile
    POST /capital/allocations/create — Create a new allocation
    GET  /capital/matching          — Run deal-investor matching engine
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from app.models import Deal, Investor, Allocation, Project, Asset
from functools import wraps

capital_bp = Blueprint("capital", __name__)


def capital_access_required(f):
    """
    Decorator to restrict access to Capital Engine routes.

    Only sponsor_admin, investor_tier1, and investor_tier2 roles
    can access Module 1. All other roles are redirected to the dashboard
    with an access denied message.
    """
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
    """
    Capital Engine overview page.

    Displays aggregate capital metrics (total required, raised, gap)
    along with active deal and investor pipeline summaries.
    """
    deals = Deal.query.all()
    investors = Investor.query.all()
    allocations = Allocation.query.all()

    # Calculate portfolio-wide capital totals
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
    """List all deals in the pipeline with their key metrics."""
    deals = Deal.query.all()
    return render_template("capital/deals.html", deals=deals)


@capital_bp.route("/deals/<int:deal_id>")
@login_required
@capital_access_required
def deal_detail(deal_id):
    """
    Individual deal room page.

    Shows detailed deal information, existing allocations, and
    (for Sponsor Admin) an allocation creation form. This is the
    "truth room" where investors can see deal-level transparency.
    """
    deal = Deal.query.get_or_404(deal_id)
    allocations = Allocation.query.filter_by(deal_id=deal_id).all()
    # Provide active investors for the allocation dropdown (Sponsor Admin)
    investors = Investor.query.filter_by(status="Active").all()
    return render_template("capital/deal_detail.html", deal=deal, allocations=allocations, investors=investors)


@capital_bp.route("/investors")
@login_required
@capital_access_required
def investors():
    """List all investor profiles with preferences, tier levels, and status."""
    investors = Investor.query.all()
    return render_template("capital/investors.html", investors=investors)


@capital_bp.route("/investors/add", methods=["GET", "POST"])
@login_required
@capital_access_required
def add_investor():
    """
    Add a new investor profile. Sponsor Admin only.

    GET:  Render the investor creation form with all preference fields.
    POST: Create the investor record from form data and redirect to listing.
    """
    # Only Sponsor Admin can create new investor profiles
    if current_user.role != "sponsor_admin":
        flash("Only Sponsor Admin can add investors.", "error")
        return redirect(url_for("capital.investors"))

    if request.method == "POST":
        # Build investor from form fields with sensible defaults
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
    """
    Create a new allocation (investor commitment to a deal). Sponsor Admin only.

    Allocations track both soft commits (verbal/preliminary) and hard commits
    (legally binding). New allocations are created with "Pending" status.
    Redirects back to the deal detail page after creation.
    """
    # Only Sponsor Admin can create allocations
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
    """
    Rule-based deal-investor matching engine.

    Scores each active investor against each open deal using the following criteria:
        - Asset type preference match:    +25 points
        - Risk tolerance alignment:       +25 points
        - Check size within range:        +25 points
        - Verified accreditation:         +15 points
        - Tier 2 (priority) investor:     +10 points

    Only matches scoring >= 25 (at least one criterion met) are displayed.
    Results are sorted by score descending, with Sponsor Admin able to
    navigate directly to the deal room to create an allocation.

    Note: This is a basic rule-based matching system per the MVP spec.
    Advanced scoring, tier automation, and cross-portfolio analytics
    are explicitly deferred per the blueprint's Phase 1 constraints.
    """
    # Get only active investors and open deals for matching
    investors = Investor.query.filter_by(status="Active").all()
    deals = Deal.query.filter(Deal.status == "Open").all()

    matches = []
    for deal in deals:
        project = deal.project
        asset = project.asset

        for investor in investors:
            score = 0
            reasons = []

            # Criterion 1: Asset type preference match (+25)
            if investor.asset_preference and (investor.asset_preference == "All" or investor.asset_preference.lower() in asset.asset_type.lower()):
                score += 25
                reasons.append("Asset type match")

            # Criterion 2: Risk tolerance alignment (+25)
            if investor.risk_tolerance and investor.risk_tolerance.lower().replace("-", " ") in deal.risk_level.lower().replace("-", " "):
                score += 25
                reasons.append("Risk tolerance aligned")

            # Criterion 3: Check size fits the deal (+25)
            if float(investor.check_size_min or 0) <= float(deal.capital_required or 0) and float(investor.check_size_max or 0) >= float(investor.check_size_min or 0):
                score += 25
                reasons.append("Check size fit")

            # Criterion 4: Verified accreditation status (+15)
            if investor.accreditation_status == "Verified":
                score += 15
                reasons.append("Accredited")

            # Criterion 5: Priority tier investor (+10)
            if investor.tier_level == "Tier 2":
                score += 10
                reasons.append("Priority tier")

            # Only include matches with at least one criterion met
            if score >= 25:
                matches.append({
                    "investor": investor,
                    "deal": deal,
                    "asset": asset,
                    "score": min(score, 100),  # Cap at 100%
                    "reasons": reasons,
                })

    # Sort by match score descending (strongest matches first)
    matches.sort(key=lambda x: x["score"], reverse=True)
    return render_template("capital/matching.html", matches=matches)
