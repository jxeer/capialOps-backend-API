"""
CapitalOps API - Module 1: Capital Engine Routes

Handles investor alignment, deal distribution, matching logic, and
allocation tracking. This is the investor-facing module.

Access restricted to:
    - sponsor_admin:   Full access (CRUD deals, approve allocations, manage investors)
    - investor_tier1:  View matched deals, submit allocation requests
    - investor_tier2:  Priority access with enhanced reporting

Routes:
    GET  /api/capital/                  — Capital Engine overview (stats + lists)
    GET  /api/capital/deals             — Deal pipeline listing
    GET  /api/capital/deals/<id>        — Individual deal with allocations
    GET  /api/capital/investors         — Investor profile listing
    POST /api/capital/investors         — Create new investor profile
    POST /api/capital/allocations       — Create a new allocation
    GET  /api/capital/matching          — Run deal-investor matching engine
"""

from flask import Blueprint, request, jsonify, g
from app import db
from app.models import Deal, Investor, Allocation, Project, Asset
from app.auth_utils import jwt_required, role_required

capital_bp = Blueprint("capital", __name__)

# Roles permitted to access Capital Engine routes
CAPITAL_ROLES = ("sponsor_admin", "investor_tier1", "investor_tier2")


@capital_bp.route("/", methods=["GET"])
@jwt_required
@role_required(*CAPITAL_ROLES)
def index():
    """
    Capital Engine overview.

    Returns aggregate capital metrics along with deal, investor,
    and allocation lists.
    """
    deals = Deal.query.all()
    investors = Investor.query.all()
    allocations = Allocation.query.all()

    total_required = sum(float(d.capital_required or 0) for d in deals)
    total_raised = sum(float(d.capital_raised or 0) for d in deals)

    return jsonify({
        "total_required": total_required,
        "total_raised": total_raised,
        "deals": [d.to_dict() for d in deals],
        "investors": [i.to_dict() for i in investors],
        "allocations": [a.to_dict() for a in allocations],
    })


@capital_bp.route("/deals", methods=["GET"])
@jwt_required
@role_required(*CAPITAL_ROLES)
def deals():
    """List all deals in the pipeline."""
    deals = Deal.query.all()
    return jsonify({"deals": [d.to_dict() for d in deals]})


@capital_bp.route("/deals/<int:deal_id>", methods=["GET"])
@jwt_required
@role_required(*CAPITAL_ROLES)
def deal_detail(deal_id):
    """
    Individual deal detail with allocations and available investors.

    Returns the deal, its allocations, and active investors
    (for the allocation creation form on the frontend).
    """
    deal = Deal.query.get_or_404(deal_id)
    allocations = Allocation.query.filter_by(deal_id=deal_id).all()
    investors = Investor.query.filter_by(status="Active").all()

    return jsonify({
        "deal": deal.to_dict(),
        "allocations": [a.to_dict() for a in allocations],
        "investors": [i.to_dict() for i in investors],
    })


@capital_bp.route("/investors", methods=["GET"])
@jwt_required
@role_required(*CAPITAL_ROLES)
def investors():
    """List all investor profiles."""
    investors = Investor.query.all()
    return jsonify({"investors": [i.to_dict() for i in investors]})


@capital_bp.route("/investors", methods=["POST"])
@jwt_required
@role_required("sponsor_admin")
def create_investor():
    """
    Create a new investor profile. Sponsor Admin only.

    Expects JSON body with investor fields:
        {
            "name": "Investor Name",
            "accreditation_status": "Verified",
            "check_size_min": 500000,
            ...
        }

    Returns (201): Created investor object.
    Returns (400): If name is missing.
    """
    data = request.get_json()
    if not data or not data.get("name"):
        return jsonify({"error": "Investor name is required"}), 400

    investor = Investor(
        name=data["name"],
        accreditation_status=data.get("accreditation_status", "Pending"),
        check_size_min=data.get("check_size_min", 0),
        check_size_max=data.get("check_size_max", 0),
        asset_preference=data.get("asset_preference", ""),
        geography_preference=data.get("geography_preference", ""),
        risk_tolerance=data.get("risk_tolerance", ""),
        structure_preference=data.get("structure_preference", ""),
        timeline_preference=data.get("timeline_preference", ""),
        strategic_interest=data.get("strategic_interest", ""),
        tier_level=data.get("tier_level", "Tier 1"),
        status="Active",
    )
    db.session.add(investor)
    db.session.commit()

    return jsonify({"investor": investor.to_dict()}), 201


@capital_bp.route("/allocations", methods=["POST"])
@jwt_required
@role_required("sponsor_admin")
def create_allocation():
    """
    Create a new allocation (investor commitment to a deal). Sponsor Admin only.

    Expects JSON body:
        {
            "investor_id": 1,
            "deal_id": 1,
            "soft_commit_amount": 500000,
            "hard_commit_amount": 0,
            "notes": "Initial commitment"
        }

    Returns (201): Created allocation object.
    Returns (400): If investor_id or deal_id is missing.
    """
    data = request.get_json()
    if not data or not data.get("investor_id") or not data.get("deal_id"):
        return jsonify({"error": "investor_id and deal_id are required"}), 400

    allocation = Allocation(
        investor_id=data["investor_id"],
        deal_id=data["deal_id"],
        soft_commit_amount=data.get("soft_commit_amount", 0),
        hard_commit_amount=data.get("hard_commit_amount", 0),
        status="Pending",
        notes=data.get("notes", ""),
    )
    db.session.add(allocation)
    db.session.commit()

    return jsonify({"allocation": allocation.to_dict()}), 201


@capital_bp.route("/matching", methods=["GET"])
@jwt_required
@role_required(*CAPITAL_ROLES)
def matching():
    """
    Rule-based deal-investor matching engine.

    Scores each active investor against each open deal:
        - Asset type preference match:    +25 points
        - Risk tolerance alignment:       +25 points
        - Check size within range:        +25 points
        - Verified accreditation:         +15 points
        - Tier 2 (priority) investor:     +10 points

    Only matches scoring >= 25 are returned, sorted by score descending.
    """
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
                    "investor": investor.to_dict(),
                    "deal": deal.to_dict(),
                    "asset": asset.to_dict(),
                    "score": min(score, 100),
                    "reasons": reasons,
                })

    # Sort by match score descending
    matches.sort(key=lambda x: x["score"], reverse=True)
    return jsonify({"matches": matches})
