"""
CapitalOps - JSON API Routes

Provides RESTful JSON endpoints for programmatic access to core data.
These endpoints mirror the role-based access controls of the UI modules
and are intended for future frontend integrations or external consumers.

CSRF protection is exempted for this blueprint since these are
read-only GET endpoints that return JSON (no state-changing mutations).

Role enforcement:
    - /api/projects:    sponsor_admin, project_manager, general_contractor
    - /api/deals:       sponsor_admin, investor_tier1, investor_tier2
    - /api/milestones:  sponsor_admin, project_manager, general_contractor

Routes:
    GET /api/projects              — List all projects with budget data
    GET /api/deals                 — List all deals with capital raise data
    GET /api/milestones/<id>       — List milestones for a specific project
"""

from flask import Blueprint, jsonify
from flask_login import login_required, current_user
from app.models import Project, Deal, Investor, Milestone, Vendor, WorkOrder, Asset
from app import csrf

api_bp = Blueprint("api", __name__)

# Exempt API endpoints from CSRF since they are read-only GET routes
# returning JSON data. No state-changing POST operations are exposed here.
csrf.exempt(api_bp)


@api_bp.route("/projects")
@login_required
def projects():
    """
    List all projects with budget and status data.

    Access: sponsor_admin, project_manager, general_contractor
    Returns: JSON array of project objects with asset name, phase,
             status, budget totals, and PM assignment.
    """
    # Enforce role-based access — only execution-level roles can view project data
    if current_user.role not in ("sponsor_admin", "project_manager", "general_contractor"):
        return jsonify({"error": "Access denied"}), 403

    projects = Project.query.all()
    return jsonify([{
        "id": p.id,
        "asset": p.asset.name,
        "phase": p.phase,
        "status": p.status,
        "budget_total": float(p.budget_total or 0),
        "budget_actual": float(p.budget_actual or 0),
        "pm_assigned": p.pm_assigned,
    } for p in projects])


@api_bp.route("/deals")
@login_required
def deals():
    """
    List all deals with capital raise data.

    Access: sponsor_admin, investor_tier1, investor_tier2
    Returns: JSON array of deal objects with project name, capital
             amounts, risk level, and status.
    """
    # Enforce role-based access — only capital-level roles can view deal data
    if current_user.role not in ("sponsor_admin", "investor_tier1", "investor_tier2"):
        return jsonify({"error": "Access denied"}), 403

    deals = Deal.query.all()
    return jsonify([{
        "id": d.id,
        "project": d.project.asset.name,
        "capital_required": float(d.capital_required or 0),
        "capital_raised": float(d.capital_raised or 0),
        "risk_level": d.risk_level,
        "status": d.status,
    } for d in deals])


@api_bp.route("/milestones/<int:project_id>")
@login_required
def milestones(project_id):
    """
    List milestones for a specific project.

    Access: sponsor_admin, project_manager, general_contractor
    Returns: JSON array of milestone objects ordered by target date,
             including status, risk flags, and delay explanations.
    """
    # Enforce role-based access — only execution-level roles can view milestone data
    if current_user.role not in ("sponsor_admin", "project_manager", "general_contractor"):
        return jsonify({"error": "Access denied"}), 403

    milestones = Milestone.query.filter_by(project_id=project_id).order_by(Milestone.target_date).all()
    return jsonify([{
        "id": m.id,
        "name": m.name,
        "category": m.category,
        "target_date": m.target_date.isoformat() if m.target_date else None,
        "completion_date": m.completion_date.isoformat() if m.completion_date else None,
        "status": m.status,
        "risk_flag": m.risk_flag,
        "delay_explanation": m.delay_explanation,
    } for m in milestones])
