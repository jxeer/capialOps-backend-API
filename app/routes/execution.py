from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from app.models import Project, Milestone, RiskFlag, Asset
from functools import wraps
from datetime import date

execution_bp = Blueprint("execution", __name__)


def execution_access_required(f):
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
    project = Project.query.get_or_404(project_id)
    milestones = Milestone.query.filter_by(project_id=project_id).order_by(Milestone.target_date).all()
    risk_flags = RiskFlag.query.filter_by(project_id=project_id).all()

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
    milestone = Milestone.query.get_or_404(milestone_id)

    if current_user.role == "general_contractor" and request.form.get("status") != "Complete":
        flash("General contractors can only mark milestones as complete.", "error")
        return redirect(url_for("execution.project_detail", project_id=milestone.project_id))

    milestone.status = request.form.get("status", milestone.status)
    if request.form.get("delay_explanation"):
        milestone.delay_explanation = request.form["delay_explanation"]
    if request.form.get("risk_flag"):
        milestone.risk_flag = request.form["risk_flag"] == "true"
    if milestone.status == "Complete" and not milestone.completion_date:
        milestone.completion_date = date.today()

    db.session.commit()
    flash("Milestone updated.", "success")
    return redirect(url_for("execution.project_detail", project_id=milestone.project_id))


@execution_bp.route("/governance")
@login_required
@execution_access_required
def governance():
    projects = Project.query.all()
    milestones = Milestone.query.order_by(Milestone.target_date.desc()).all()
    risk_flags = RiskFlag.query.order_by(RiskFlag.created_at.desc()).all()
    return render_template("execution/governance.html", projects=projects, milestones=milestones, risk_flags=risk_flags)
