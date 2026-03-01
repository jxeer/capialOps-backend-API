"""
CapitalOps - Module 2: Execution Control Routes

Translates raw project data into governance-level clarity. This module
provides milestone progress tracking, budget vs actual reporting,
risk flag monitoring, and a governance event log.

Access restricted to:
    - sponsor_admin:      Full access to all execution data
    - project_manager:    Update milestones, log delays, view dashboards
    - general_contractor: Confirm milestone completion only

Key features:
    - Per-project execution dashboard with milestone rollups
    - Budget variance reporting (total vs actual with percentage)
    - Risk flag tracking on individual milestones
    - Structured delay explanation logging
    - Governance event log aggregating all projects

Routes:
    GET  /execution/                         — Execution overview (all projects)
    GET  /execution/project/<id>             — Individual project detail with milestones
    POST /execution/milestone/<id>/update    — Update milestone status/delay
    GET  /execution/governance               — Governance event log
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from app.models import Project, Milestone, RiskFlag, Asset
from functools import wraps
from datetime import date

execution_bp = Blueprint("execution", __name__)


def execution_access_required(f):
    """
    Decorator to restrict access to Execution Control routes.

    Only sponsor_admin, project_manager, and general_contractor roles
    can access Module 2. Investors and vendors are redirected to the dashboard.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        if current_user.role not in ("sponsor_admin", "project_manager", "general_contractor"):
            flash("Access denied.", "error")
            return redirect(url_for("dashboard.index"))
        return f(*args, **kwargs)
    return decorated


@execution_bp.route("/")
@login_required
@execution_access_required
def index():
    """
    Execution Control overview — displays all projects with computed metrics.

    For each project, computes:
        - Milestone progress (completed / total as percentage)
        - Risk flag count (milestones flagged as risky)
        - Budget variance (total - actual)
        - Budget utilization percentage

    Projects are displayed as summary cards with progress bars and
    as a detailed comparison table below.
    """
    projects = Project.query.all()
    project_data = []

    for p in projects:
        # Compute milestone progress for this project
        milestones = Milestone.query.filter_by(project_id=p.id).all()
        completed = sum(1 for m in milestones if m.status == "Complete")
        total = len(milestones)
        progress = round(completed / total * 100) if total else 0

        # Count active risk flags
        risk_count = sum(1 for m in milestones if m.risk_flag)

        # Calculate budget metrics
        budget_variance = float(p.budget_total or 0) - float(p.budget_actual or 0)
        budget_pct = round(float(p.budget_actual or 0) / float(p.budget_total or 1) * 100)

        project_data.append({
            "project": p,
            "asset": p.asset,
            "progress": progress,
            "completed": completed,
            "total": total,
            "risk_count": risk_count,
            "budget_variance": budget_variance,
            "budget_pct": budget_pct,
        })

    return render_template("execution/index.html", project_data=project_data)


@execution_bp.route("/project/<int:project_id>")
@login_required
@execution_access_required
def project_detail(project_id):
    """
    Individual project execution detail page.

    Displays all milestones ordered by target date, risk flags,
    and (for authorized roles) inline forms to update milestone
    status and log delay explanations.
    """
    project = Project.query.get_or_404(project_id)
    milestones = Milestone.query.filter_by(project_id=project_id).order_by(Milestone.target_date).all()
    risk_flags = RiskFlag.query.filter_by(project_id=project_id).all()

    # Calculate overall milestone progress for the header stats
    completed = sum(1 for m in milestones if m.status == "Complete")
    total = len(milestones)
    progress = round(completed / total * 100) if total else 0

    return render_template(
        "execution/project_detail.html",
        project=project,
        milestones=milestones,
        risk_flags=risk_flags,
        progress=progress,
    )


@execution_bp.route("/milestone/<int:milestone_id>/update", methods=["POST"])
@login_required
@execution_access_required
def update_milestone(milestone_id):
    """
    Update a milestone's status, delay explanation, and/or risk flag.

    Role-based restrictions:
        - project_manager / sponsor_admin: Can change status, add delay notes, toggle risk flags
        - general_contractor: Can ONLY mark milestones as "Complete" (confirming work done)

    When a milestone is marked as "Complete", the completion_date is
    automatically set to today's date if not already recorded.
    """
    milestone = Milestone.query.get_or_404(milestone_id)

    # General contractors can only confirm completion — not change to other statuses
    if current_user.role == "general_contractor" and request.form.get("status") != "Complete":
        flash("General contractors can only mark milestones as complete.", "error")
        return redirect(url_for("execution.project_detail", project_id=milestone.project_id))

    # Update milestone fields from form data
    milestone.status = request.form.get("status", milestone.status)

    if request.form.get("delay_explanation"):
        milestone.delay_explanation = request.form["delay_explanation"]

    if request.form.get("risk_flag"):
        milestone.risk_flag = request.form["risk_flag"] == "true"

    # Auto-set completion date when milestone is marked complete
    if milestone.status == "Complete" and not milestone.completion_date:
        milestone.completion_date = date.today()

    db.session.commit()
    flash("Milestone updated.", "success")
    return redirect(url_for("execution.project_detail", project_id=milestone.project_id))


@execution_bp.route("/governance")
@login_required
@execution_access_required
def governance():
    """
    Governance event log — structured execution reporting across all projects.

    Displays:
        - Project status summary (all projects with budget and timeline info)
        - Risk & delay log (milestones flagged as risky or delayed)
        - Full milestone timeline across all projects sorted by target date

    This provides the governance-level view that flows upward to inform
    the Capital Engine (Module 1) about project execution health.
    """
    projects = Project.query.all()
    milestones = Milestone.query.order_by(Milestone.target_date.desc()).all()
    risk_flags = RiskFlag.query.order_by(RiskFlag.created_at.desc()).all()
    return render_template("execution/governance.html", projects=projects, milestones=milestones, risk_flags=risk_flags)
