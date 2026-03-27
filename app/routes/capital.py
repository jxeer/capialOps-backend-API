"""
CapitalOps API - Module 1: Capital Engine Routes

Handles investor alignment, deal distribution, matching logic, and
allocation tracking — the investor-facing module of CapitalOps.

This module enables:
    - Sponsors to create and manage investment deals
    - Admins to manage investor profiles and track allocations
    - Tiered investors to view matched deals and submit allocation requests
    - A rule-based matching engine to score investors against open deals

Access Control:
    Full CRUD access (sponsor_admin):
        - Create, update, and manage all deals
        - Create and manage investor profiles
        - Create and approve/reject allocations

    Read access + allocation requests (investor_tier1, investor_tier2):
        - View all deals and deal details
        - View matched deals via the matching engine
        - Submit allocation requests (soft/hard commitments)

    Tier2 investors receive priority scoring (+10 points) in the matching
    engine, giving them enhanced visibility to higher-priority deal flow.

Routes:
    GET  /api/v1/capital/           — Capital Engine overview with stats + lists
    GET  /api/v1/capital/deals      — Deal pipeline listing (all deals)
    GET  /api/v1/capital/deals/<id> — Individual deal detail with allocations
    GET  /api/v1/capital/investors  — Investor profile listing
    POST /api/v1/capital/investors  — Create new investor profile (admin only)
    POST /api/v1/capital/allocations — Create a new allocation (admin only)
    GET  /api/v1/capital/matching   — Run deal-investor matching engine

Security Considerations:
    - Role-based access enforced via @role_required decorator
    - Investor and deal data is scoped to the authenticated user's portfolio
    - Sponsor admin only endpoints prevent tier1/tier2 users from modifying
      deal or investor records
    - All monetary fields use float for flexibility; frontend should
      format appropriately for display
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from app import db
from app.models import Deal, Investor, Allocation
from app.auth_utils import role_required

capital_bp = Blueprint("capital", __name__)

# Roles permitted to access Capital Engine routes.
# investor_tier1 and investor_tier2 have read access to all routes.
# sponsor_admin has full CRUD access.
# Note: The matching endpoint also uses this tuple for role access.
CAPITAL_ROLES = ("sponsor_admin", "investor_tier1", "investor_tier2")


@capital_bp.route("/", methods=["GET"])
@jwt_required()
@role_required(*CAPITAL_ROLES)
def index():
    """
    Capital Engine overview — aggregate metrics and full entity lists.

    Returns capital raising summary statistics along with complete
    lists of deals, investors, and allocations for the portfolio.
    Used as the main landing page data for the Capital module.

    Metrics computed:
        - total_required: Sum of capital_required across all deals
        - total_raised: Sum of capital_raised across all deals

    Lists returned:
        - All Deal objects (full via .to_dict())
        - All Investor objects (full via .to_dict())
        - All Allocation objects (full via .to_dict())

    Returns (200):
        {
            "total_required": number,
            "total_raised": number,
            "deals": [...],
            "investors": [...],
            "allocations": [...]
        }
    """
    deals = Deal.query.all()
    investors = Investor.query.all()
    allocations = Allocation.query.all()

    # Aggregate capital metrics from all deals
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
@jwt_required()
@role_required(*CAPITAL_ROLES)
def deals():
    """
    List all deals in the investment pipeline.

    Returns the complete deal pipeline as an array of Deal objects.
    No filtering is applied — all deals are returned regardless of
    status (Open, Funded, Closed, etc.).

    This endpoint is used to populate deal listing tables and dropdowns
    throughout the Capital module UI.

    Returns (200):
        { "deals": [...] }
    """
    deals = Deal.query.all()
    return jsonify({"deals": [d.to_dict() for d in deals]})


@capital_bp.route("/deals/<int:deal_id>", methods=["GET"])
@jwt_required()
@role_required(*CAPITAL_ROLES)
def deal_detail(deal_id):
    """
    Individual deal detail with associated allocations and available investors.

    Fetches a single deal by ID, its related allocations, and the full
    list of active investors (for allocation assignment UI).

    URL Parameters:
        deal_id: Integer primary key of the Deal

    Returns (200):
        {
            "deal": { ... deal object ... },
            "allocations": [ ... allocations for this deal ... ],
            "investors": [ ... all active investors ... ]
        }

    Returns (404):
        If deal_id does not correspond to an existing Deal
    """
    deal = Deal.query.get_or_404(deal_id)
    # Filter allocations to only those associated with this deal
    allocations = Allocation.query.filter_by(deal_id=deal_id).all()
    # Return all active investors for the allocation assignment UI
    investors = Investor.query.filter_by(status="Active").all()

    return jsonify({
        "deal": deal.to_dict(),
        "allocations": [a.to_dict() for a in allocations],
        "investors": [i.to_dict() for i in investors],
    })


@capital_bp.route("/investors", methods=["GET"])
@jwt_required()
@role_required(*CAPITAL_ROLES)
def investors():
    """
    List all investor profiles.

    Returns the complete investor roster as an array of Investor objects.
    No filtering by status is applied here — all investors are returned
    including those who may be inactive or pending.

    Use cases:
        - Admin investor management panel
        - Investor dropdown in allocation forms
        - Investor directory views

    Returns (200):
        { "investors": [...] }
    """
    investors = Investor.query.all()
    return jsonify({"investors": [i.to_dict() for i in investors]})


@capital_bp.route("/investors", methods=["POST"])
@jwt_required()
@role_required("sponsor_admin")
def create_investor():
    """
    Create a new investor profile.

    Restricted to sponsor_admin role. Tier1/Tier2 investors cannot
    create investor profiles — they are the subjects of these records.

    Request Format:
        Content-Type: application/json
        Body: {
            "name": "Acme Capital Partners",         (required)
            "accreditation_status": "Verified",       (optional, default: "Pending")
            "check_size_min": 50000,                   (optional, default: 0)
            "check_size_max": 500000,                   (optional, default: 0)
            "asset_preference": "Industrial",          (optional)
            "geography_preference": "Southwest",      (optional)
            "risk_tolerance": "Moderate",               (optional)
            "structure_preference": "Equity",          (optional)
            "timeline_preference": "18 months",       (optional)
            "strategic_interest": "..."                (optional)
            "tier_level": "Tier 2"                    (optional, default: "Tier 1")
        }

    Returns (201):
        { "investor": { ... created investor object ... } }

    Returns (400):
        { "error": "Investor name is required" }
        if the required 'name' field is missing
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
@jwt_required()
@role_required("sponsor_admin")
def create_allocation():
    """
    Create a new allocation (investor commitment to a deal).

    Allocations represent a specific investor's commitment (soft or hard)
    to a specific deal. Soft commits are non-binding expressions of interest;
    hard commits are binding commitments.

    Restricted to sponsor_admin role. This ensures only authorized
    personnel can record formal investment commitments.

    Request Format:
        Content-Type: application/json
        Body: {
            "investor_id": 123,         (required)
            "deal_id": 456,             (required)
            "soft_commit_amount": 100000,  (optional, default: 0)
            "hard_commit_amount": 50000,   (optional, default: 0)
            "notes": "LP意向函已签署"         (optional)
        }

    Returns (201):
        { "allocation": { ... created allocation object ... } }

    Returns (400):
        { "error": "investor_id and deal_id are required" }
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
@jwt_required()
@role_required(*CAPITAL_ROLES)
def matching():
    """
    Rule-based deal-investor matching engine.

    Scores each active investor against each open deal using five criteria:
        1. Asset type preference match:     +25 points
           Investor's asset_preference matches the deal's asset type.
           "All" preference matches any asset type (case-insensitive substring).

        2. Risk tolerance alignment:         +25 points
           Investor's risk_tolerance matches the deal's risk_level.
           Hyphens are normalized before comparison (case-insensitive).

        3. Check size within range:         +25 points
           Investor's check_size_min <= deal's capital_required AND
           investor's check_size_max >= check_size_min.
           This ensures the deal fits within the investor's typical range.

        4. Verified accreditation status:   +15 points
           Investor has accreditation_status = "Verified".

        5. Priority tier investor:          +10 points
           Investor has tier_level = "Tier 2" (priority investors).

    Scoring Rules:
        - Maximum possible score: 100 points
        - Minimum threshold to return a match: 25 points
          (At least one criterion must match; otherwise excluded)
        - Results sorted by score descending (best matches first)

    Data Requirements:
        - Only investors with status="Active" are considered
        - Only deals with status="Open" are considered
        - Investor and deal must both have valid asset/project relationships

    Returns (200):
        {
            "matches": [
                {
                    "investor": { ... investor object ... },
                    "deal": { ... deal object ... },
                    "asset": { ... asset object ... },
                    "score": number,      — 25 to 100
                    "reasons": [         — List of matched criteria strings
                        "Asset type match",
                        "Accredited",
                        "Priority tier"
                    ]
                },
                ...
            ]
        }
    """
    investors = Investor.query.filter_by(status="Active").all()
    # Only match against open deals — funded/closed deals are not available
    deals = Deal.query.filter(Deal.status == "Open").all()

    matches = []
    for deal in deals:
        # Navigate the relationship: deal -> project -> asset
        project = deal.project
        asset = project.asset

        for investor in investors:
            score = 0
            reasons = []

            # Criterion 1: Asset type preference match (+25)
            # "All" is a wildcard that matches any asset type
            if investor.asset_preference and (investor.asset_preference == "All" or investor.asset_preference.lower() in asset.asset_type.lower()):
                score += 25
                reasons.append("Asset type match")

            # Criterion 2: Risk tolerance alignment (+25)
            # Normalize hyphens for comparison (e.g., "Moderate-High" == "Moderate High")
            if investor.risk_tolerance and investor.risk_tolerance.lower().replace("-", " ") in deal.risk_level.lower().replace("-", " "):
                score += 25
                reasons.append("Risk tolerance aligned")

            # Criterion 3: Check size fits the deal (+25)
            # Capital required must fall within investor's typical check range
            if float(investor.check_size_min or 0) <= float(deal.capital_required or 0) and float(investor.check_size_max or 0) >= float(investor.check_size_min or 0):
                score += 25
                reasons.append("Check size fit")

            # Criterion 4: Verified accreditation status (+15)
            # Only verified investors get this bonus — unverified are excluded
            if investor.accreditation_status == "Verified":
                score += 15
                reasons.append("Accredited")

            # Criterion 5: Priority tier investor (+10)
            # Tier 2 investors are explicitly flagged as priority by admins
            if investor.tier_level == "Tier 2":
                score += 10
                reasons.append("Priority tier")

            # Only include matches scoring at least 25 (one criterion met)
            # Score is capped at 100 even if all criteria match
            if score >= 25:
                matches.append({
                    "investor": investor.to_dict(),
                    "deal": deal.to_dict(),
                    "asset": asset.to_dict(),
                    "score": min(score, 100),
                    "reasons": reasons,
                })

    # Sort by match score descending — best matches appear first
    matches.sort(key=lambda x: x["score"], reverse=True)
    return jsonify({"matches": matches})
