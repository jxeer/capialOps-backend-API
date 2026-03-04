"""
CapitalOps API - Module 2: Execution Control Routes

Translates raw project data into governance-level clarity.

Access restricted to:
    - sponsor_admin:      Full access
    - project_manager:    Update milestones, log delays
    - general_contractor: Confirm milestone completion only

Routes:
    GET   /api/execution/                         — All projects with computed metrics
    GET   /api/execution/projects/<id>            — Individual project with milestones
    PATCH /api/execution/milestones/<id>          — Update milestone status/delay
    GET   /api/execution/governance               — Governance event log
"""

from flask import Blueprint, request, jsonify, g
from app import db
from app.models import Project, Milestone, RiskFlag, Asset
from app.auth_utils import jwt_required, role_required
from datetime import date

execution_bp = Blueprint("execution", __name__)

# Roles permitted to access Execution Control routes
EXECUTION_ROLES = ("sponsor_admin", "project_manager", "general_contractor")


@execution_bp.route("/", methods=["GET"])
@jwt_required
@role_required(*EXECUTION_ROLES)
def index():
    """
    Execution Control overview — all projects with computed metrics.

    For each project, computes:
        - Milestone progress (completed / total as percentage)
        - Risk flag count
        - Budget variance and utilization percentage
    """
    projects = Project.query.all()
    project_data = []

    for p in projects:
        milestones = Milestone.query.filter_by(project_id=p.id).all()
        completed = sum(1 for m in milestones if m.status == "Complete")
        total = len(milestones)
        progress = round(completed / total * 100) if total else 0
        risk_count = sum(1 for m in milestones if m.risk_flag)
        budget_variance = float(p.budget_total or 0) - float(p.budget_actual or 0)
        budget_pct = round(float(p.budget_actual or 0) / float(p.budget_total or 1) * 100)

        project_data.append({
            "project": p.to_dict(),
            "asset": p.asset.to_dict() if p.asset else None,
            "progress": progress,
            "completed_milestones": completed,
            "total_milestones": total,
            "risk_count": risk_count,
            "budget_variance": budget_variance,
            "budget_pct": budget_pct,
        })

    return jsonify({"projects": project_data})


@execution_bp.route("/projects/<int:project_id>", methods=["GET"])
@jwt_required
@role_required(*EXECUTION_ROLES)
def project_detail(project_id):
    """
    Individual project with milestones, risk flags, and progress.
    """
    project = Project.query.get_or_404(project_id)
    milestones = Milestone.query.filter_by(project_id=project_id).order_by(Milestone.target_date).all()
    risk_flags = RiskFlag.query.filter_by(project_id=project_id).all()

    completed = sum(1 for m in milestones if m.status == "Complete")
    total = len(milestones)
    progress = round(completed / total * 100) if total else 0

    return jsonify({
        "project": project.to_dict(),
        "milestones": [m.to_dict() for m in milestones],
        "risk_flags": [r.to_dict() for r in risk_flags],
        "progress": progress,
    })


@execution_bp.route("/milestones/<int:milestone_id>", methods=["PATCH"])
@jwt_required
@role_required(*EXECUTION_ROLES)
def update_milestone(milestone_id):
    """
    Update a milestone's status, delay explanation, and/or risk flag.

    Expects JSON body with any of:
        {
            "status": "Complete",
            "delay_explanation": "Weather delay",
            "risk_flag": true
        }

    Role restrictions:
        - general_contractor: Can ONLY set status to "Complete"
        - project_manager / sponsor_admin: Can update all fields

    Returns (200): Updated milestone object.
    Returns (403): If GC tries to set status to anything other than "Complete".
    """
    milestone = Milestone.query.get_or_404(milestone_id)
    data = request.get_json() or {}

    # General contractors can only confirm completion
    if g.current_user.role == "general_contractor" and data.get("status") != "Complete":
        return jsonify({"error": "General contractors can only mark milestones as complete"}), 403

    # Update fields from request data
    if "status" in data:
        milestone.status = data["status"]
    if "delay_explanation" in data:
        milestone.delay_explanation = data["delay_explanation"]
    if "risk_flag" in data:
        milestone.risk_flag = data["risk_flag"]

    # Auto-set completion date when marked complete
    if milestone.status == "Complete" and not milestone.completion_date:
        milestone.completion_date = date.today()

    db.session.commit()
    return jsonify({"milestone": milestone.to_dict()})


@execution_bp.route("/governance", methods=["GET"])
@jwt_required
@role_required(*EXECUTION_ROLES)
def governance():
    """
    Governance event log — structured execution reporting across all projects.

    Returns projects, milestones (sorted by target date desc), and risk flags.
    """
    projects = Project.query.all()
    milestones = Milestone.query.order_by(Milestone.target_date.desc()).all()
    risk_flags = RiskFlag.query.order_by(RiskFlag.created_at.desc()).all()

    return jsonify({
        "projects": [p.to_dict() for p in projects],
        "milestones": [m.to_dict() for m in milestones],
        "risk_flags": [r.to_dict() for r in risk_flags],
    })
