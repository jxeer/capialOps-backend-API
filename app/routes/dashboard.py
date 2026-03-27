"""
CapitalOps API - Portfolio Dashboard Route

Returns aggregated portfolio-level metrics across all three modules
(Capital Engine, Execution Control, Asset & Vendor Control).
This endpoint powers the React frontend's main dashboard view, which
displays KPIs and high-level summaries for the authenticated user's
portfolio.

Access:
    Requires a valid JWT. Returns data scoped to the authenticated user's
    portfolio. Unauthenticated requests receive demo/fallback data.

Dashboard Metrics Provided:
    - Project counts and budget summaries (total, actual, variance)
    - Capital raise progress (required vs raised, percentage)
    - Milestone completion tracking (completed count, total count, %)
    - Risk flag counts (flagged milestones)
    - Investor counts (active investors)
    - Vendor compliance (total vendors, expired COIs)

Routes:
    GET /api/v1/dashboard/ — Full portfolio overview with stats, projects, deals,
                              and flagged milestones

Response Structure:
    {
        "stats": {
            "active_projects": number,     — Projects not marked "Complete"
            "total_budget": number,         — Sum of all project budgets
            "total_actual": number,         — Sum of all project actuals spent
            "budget_variance": number,      — total_budget - total_actual
            "capital_required": number,     — Sum of all deal capital requirements
            "capital_raised": number,       — Sum of all deal capital raised
            "capital_pct": number,          — capital_raised / capital_required as %
            "active_investors": number,     — Count of investors with status="Active"
            "milestone_progress": number,   — % of milestones that are "Complete"
            "risk_flags": number,            — Count of milestones with risk_flag=True
            "total_vendors": number,       — Total vendor count
            "coi_expired": number,          — Vendors with coi_status="Expired"
        },
        "projects": [...],     — All projects (full objects via .to_dict())
        "deals": [...],        — All deals (full objects via .to_dict())
        "risk_milestones": [...] — Milestones where risk_flag=True
    }

Security Considerations:
    - JWT required (user data isolation enforced at auth layer)
    - No user-scoped filtering here (relies on upstream auth/isolation)
    - Returns full project and deal objects — ensure to_dict() doesn't
      expose sensitive fields that should be restricted by role
"""

from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required
from app.models import Project, Deal, Investor, Milestone, Vendor

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/", methods=["GET"])
@jwt_required()
def index():
    """
    Return aggregated portfolio stats from all three modules.

    This is the primary dashboard data endpoint. It computes summary
    statistics across all projects, deals, investors, milestones,
    risk flags, and vendors in the system.

    Metrics computed:
        - Active project count: Projects where status != "Complete"
        - Total budget: Sum of all project budget_total fields
        - Total actual: Sum of all project budget_actual fields
        - Budget variance: total_budget - total_actual (positive = under budget)
        - Capital required: Sum of all deal capital_required fields
        - Capital raised: Sum of all deal capital_raised fields
        - Capital raise %: (capital_raised / capital_required) * 100
        - Active investors: Count of investors with status="Active"
        - Milestone progress: (completed_count / total_count) * 100
        - Risk flags: Count of milestones with risk_flag=True
        - Total vendors: Count of all vendors
        - Expired COIs: Vendors where coi_status="Expired"

    Note on Null Handling:
        Fields like budget_total, budget_actual, capital_required use
        `float(p.budget_total or 0)` pattern to safely handle NULL/missing
        values in the database, defaulting to 0.

    Returns (200):
        {
            "stats": {
                "active_projects": number,
                "total_budget": number,
                "total_actual": number,
                "budget_variance": number,
                "capital_required": number,
                "capital_raised": number,
                "capital_pct": number,
                "active_investors": number,
                "milestone_progress": number,
                "risk_flags": number,
                "total_vendors": number,
                "coi_expired": number
            },
            "projects": [p.to_dict() for p in projects],
            "deals": [d.to_dict() for d in deals],
            "risk_milestones": [m.to_dict() for m in risk_milestones]
        }
    """
    # Query all core data needed for dashboard aggregations.
    # These queries fetch all records; for large portfolios this could
    # be optimized with indexed filters or pagination if needed.
    projects = Project.query.all()
    deals = Deal.query.all()
    # Only active investors count toward the active_investors metric
    investors = Investor.query.filter_by(status="Active").all()
    # Risk milestones are milestones that have been flagged for risk
    risk_milestones = Milestone.query.filter_by(risk_flag=True).all()
    vendors = Vendor.query.all()

    # --- Budget Aggregations ---
    # Using `or 0` handles None/NULL database values gracefully.
    # If budget_total is NULL, float(NULL) would error, so we coerce to 0.
    total_budget = sum(float(p.budget_total or 0) for p in projects)
    total_actual = sum(float(p.budget_actual or 0) for p in projects)

    # --- Capital Aggregations ---
    # Same null-handling pattern for deal capital fields
    total_capital_required = sum(float(d.capital_required or 0) for d in deals)
    total_capital_raised = sum(float(d.capital_raised or 0) for d in deals)

    # --- Milestone Progress ---
    # Counts completed vs total milestones to compute % completion
    milestones = Milestone.query.all()
    completed = sum(1 for m in milestones if m.status == "Complete")
    total_milestones = len(milestones)
    # Guard against division by zero if no milestones exist
    milestone_progress = round((completed / total_milestones * 100) if total_milestones else 0)

    # --- Vendor Compliance ---
    # COI = Certificate of Insurance. Expired COIs are a compliance risk.
    coi_expired = sum(1 for v in vendors if v.coi_status == "Expired")

    stats = {
        # Active projects = those not yet marked "Complete"
        "active_projects": len([p for p in projects if p.status != "Complete"]),
        "total_budget": total_budget,
        "total_actual": total_actual,
        # Positive variance = under budget, negative = over budget
        "budget_variance": total_budget - total_actual,
        "capital_required": total_capital_required,
        "capital_raised": total_capital_raised,
        # Percentage of capital raise goal achieved
        "capital_pct": round(total_capital_raised / total_capital_required * 100) if total_capital_required else 0,
        "active_investors": len(investors),
        "milestone_progress": milestone_progress,
        "risk_flags": len(risk_milestones),
        "total_vendors": len(vendors),
        "coi_expired": coi_expired,
    }

    return jsonify({
        "stats": stats,
        "projects": [p.to_dict() for p in projects],
        "deals": [d.to_dict() for d in deals],
        "risk_milestones": [m.to_dict() for m in risk_milestones],
    })
