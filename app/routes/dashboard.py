from flask import Blueprint, render_template
from flask_login import login_required, current_user
from app.models import Project, Deal, Investor, Milestone, Vendor, Asset, WorkOrder, RiskFlag
from app import db
from sqlalchemy import func

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/")
@login_required
def index():
    projects = Project.query.all()
    deals = Deal.query.all()
    investors = Investor.query.filter_by(status="Active").all()
    risk_milestones = Milestone.query.filter_by(risk_flag=True).all()
    vendors = Vendor.query.all()

    total_budget = sum(float(p.budget_total or 0) for p in projects)
    total_actual = sum(float(p.budget_actual or 0) for p in projects)
    total_capital_required = sum(float(d.capital_required or 0) for d in deals)
    total_capital_raised = sum(float(d.capital_raised or 0) for d in deals)

    milestones = Milestone.query.all()
    completed = sum(1 for m in milestones if m.status == "Complete")
    total_milestones = len(milestones)
    milestone_progress = round((completed / total_milestones * 100) if total_milestones else 0)

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

    return render_template(
        "dashboard/index.html",
        stats=stats,
        projects=projects,
        deals=deals,
        risk_milestones=risk_milestones,
    )
