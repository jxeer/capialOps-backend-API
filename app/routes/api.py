from flask import Blueprint, jsonify
from flask_login import login_required, current_user
from app.models import Project, Deal, Investor, Milestone, Vendor, WorkOrder, Asset
from app import csrf

api_bp = Blueprint("api", __name__)
csrf.exempt(api_bp)


@api_bp.route("/projects")
@login_required
def projects():
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
