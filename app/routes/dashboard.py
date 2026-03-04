"""
CapitalOps API - Portfolio Dashboard Route

Returns aggregated portfolio-level metrics across all three modules.
Used by the React frontend's main dashboard view.

Routes:
    GET /api/v1/dashboard/ — Portfolio overview with aggregated stats
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

    Computes:
        - Active project count (excludes completed projects)
        - Total budget vs actual spend across all projects
        - Capital raised vs required across all deals
        - Capital raise percentage
        - Milestone completion progress (percentage)
        - Active risk flag count
        - Active investor count
        - Vendor count and expired COI count

    Returns (200):
        {
            "stats": { ...aggregated metrics... },
            "projects": [ ...project list... ],
            "deals": [ ...deal list... ],
            "risk_milestones": [ ...flagged milestones... ]
        }
    """
    # Query all core data needed for dashboard aggregations
    projects = Project.query.all()
    deals = Deal.query.all()
    investors = Investor.query.filter_by(status="Active").all()
    risk_milestones = Milestone.query.filter_by(risk_flag=True).all()
    vendors = Vendor.query.all()

    # --- Budget Aggregations ---
    total_budget = sum(float(p.budget_total or 0) for p in projects)
    total_actual = sum(float(p.budget_actual or 0) for p in projects)

    # --- Capital Aggregations ---
    total_capital_required = sum(float(d.capital_required or 0) for d in deals)
    total_capital_raised = sum(float(d.capital_raised or 0) for d in deals)

    # --- Milestone Progress ---
    milestones = Milestone.query.all()
    completed = sum(1 for m in milestones if m.status == "Complete")
    total_milestones = len(milestones)
    milestone_progress = round((completed / total_milestones * 100) if total_milestones else 0)

    # --- Vendor Compliance ---
    coi_expired = sum(1 for v in vendors if v.coi_status == "Expired")

    stats = {
        "active_projects": len([p for p in projects if p.status != "Complete"]),
        "total_budget": total_budget,
        "total_actual": total_actual,
        "budget_variance": total_budget - total_actual,
        "capital_required": total_capital_required,
        "capital_raised": total_capital_raised,
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
