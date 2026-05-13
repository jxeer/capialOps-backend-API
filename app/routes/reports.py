"""
CapitalOps API - Financial Report Routes

Handles generation and sharing of financial summary reports.

Access Control:
    sponsor_admin:
        Can generate and share all reports.

Routes:
    GET  /api/v1/reports/       — List reports received by current user
    GET  /api/v1/reports/sent   — List reports sent by current user
    GET  /api/v1/reports/:id    — Get single report (marks as read)
    POST /api/v1/reports/       — Generate and share a report
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt
from app import db
from app.models import FinancialReport, Project, Deal, Allocation, Milestone, RiskFlag, User
from app.auth_utils import role_required
from app.notifications import create_notification

reports_bp = Blueprint("reports", __name__)


@reports_bp.route("/", methods=["GET"])
@jwt_required()
def index():
    """
    List all reports sent to the current user.

    Query Parameters:
        project_id: Filter by project (optional)
        deal_id: Filter by deal (optional)

    Returns (200):
        { "reports": [ ... ] }
    """
    user_id = get_jwt().get("user_id")

    query = FinancialReport.query.filter_by(recipient_user_id=user_id)

    project_id = request.args.get("project_id", type=int)
    if project_id:
        query = query.filter_by(project_id=project_id)

    deal_id = request.args.get("deal_id", type=int)
    if deal_id:
        query = query.filter_by(deal_id=deal_id)

    reports = query.order_by(FinancialReport.created_at.desc()).all()
    return jsonify({"reports": [r.to_dict() for r in reports]})


@reports_bp.route("/sent", methods=["GET"])
@jwt_required()
def sent():
    """
    List all reports sent by the current user.

    Returns (200):
        { "reports": [ ... ] }
    """
    user_id = get_jwt().get("user_id")
    reports = FinancialReport.query.filter_by(
        created_by_user_id=user_id
    ).order_by(FinancialReport.created_at.desc()).all()
    return jsonify({"reports": [r.to_dict() for r in reports]})


@reports_bp.route("/<int:report_id>", methods=["GET"])
@jwt_required()
def get_report(report_id):
    """
    Get a single report by ID.

    Marks the report as read if the current user is the recipient.

    Returns (200):
        { "report": { ... } }
    Returns (404):
        { "error": "Report not found" }
    """
    user_id = get_jwt().get("user_id")

    report = FinancialReport.query.get_or_404(report_id)

    if report.recipient_user_id == user_id and not report.is_read:
        report.is_read = True
        db.session.commit()

    return jsonify({"report": report.to_dict()})


@reports_bp.route("/", methods=["POST"])
@jwt_required()
@role_required("sponsor_admin")
def create_report():
    """
    Generate and share a financial report.

    Request Body:
        recipient_user_id: int (required)
        project_id: int (optional, one of project_id or deal_id required)
        deal_id: int (optional, one of project_id or deal_id required)
        report_type: "project_summary" | "deal_summary" (required)

    Returns (201):
        { "report": { ... } }
    Returns (400):
        { "error": "project_id or deal_id required" }
    Returns (404):
        { "error": "Recipient user not found" }
    """
    user_id = get_jwt().get("user_id")
    data = request.get_json()

    recipient_user_id = data.get("recipient_user_id")
    project_id = data.get("project_id")
    deal_id = data.get("deal_id")
    report_type = data.get("report_type")

    if not recipient_user_id:
        return jsonify({"error": "recipient_user_id is required"}), 400

    if not project_id and not deal_id:
        return jsonify({"error": "project_id or deal_id required"}), 400

    if report_type not in ("project_summary", "deal_summary"):
        return jsonify({"error": "report_type must be 'project_summary' or 'deal_summary'"}), 400

    recipient = User.query.get(recipient_user_id)
    if not recipient:
        return jsonify({"error": "Recipient user not found"}), 404

    if report_type == "project_summary":
        if not project_id:
            return jsonify({"error": "project_id required for project_summary report"}), 400

        project = Project.query.get(project_id)
        if not project:
            return jsonify({"error": "Project not found"}), 404

        milestones = Milestone.query.filter_by(project_id=project_id).all()
        completed_milestones = [m for m in milestones if m.status == "Complete"]
        risk_flags = RiskFlag.query.filter_by(project_id=project_id).all()
        open_risk_flags = [r for r in risk_flags if r.status == "Open"]

        content = {
            "project_id": project.id,
            "asset_name": project.asset.name if project.asset else None,
            "budget_total": float(project.budget_total or 0),
            "budget_actual": float(project.budget_actual or 0),
            "budget_remaining": float(project.budget_total or 0) - float(project.budget_actual or 0),
            "milestone_count": len(milestones),
            "milestones_complete": len(completed_milestones),
            "milestone_completion_pct": (
                round(len(completed_milestones) / len(milestones) * 100, 1)
                if milestones else 0
            ),
            "risk_flag_count": len(open_risk_flags),
            "deals": [
                {
                    "deal_id": deal.id,
                    "capital_required": float(deal.capital_required or 0),
                    "capital_raised": float(deal.capital_raised or 0),
                    "raise_pct": (
                        round(float(deal.capital_raised or 0) / float(deal.capital_required or 0) * 100, 1)
                        if deal.capital_required else 0
                    ),
                    "status": deal.status,
                }
                for deal in project.deals
            ],
        }

        title = f"Project Summary: {project.asset.name}" if project.asset else "Project Summary"

    else:
        if not deal_id:
            return jsonify({"error": "deal_id required for deal_summary report"}), 400

        deal = Deal.query.get(deal_id)
        if not deal:
            return jsonify({"error": "Deal not found"}), 404

        allocations = Allocation.query.filter_by(deal_id=deal_id).all()
        allocation_statuses = {}
        for a in allocations:
            allocation_statuses[a.status] = allocation_statuses.get(a.status, 0) + 1

        content = {
            "deal_id": deal.id,
            "project_name": deal.project.asset.name if deal.project and deal.project.asset else None,
            "capital_required": float(deal.capital_required or 0),
            "capital_raised": float(deal.capital_raised or 0),
            "raise_pct": (
                round(float(deal.capital_raised or 0) / float(deal.capital_required or 0) * 100, 1)
                if deal.capital_required else 0
            ),
            "allocation_count": len(allocations),
            "allocation_statuses": allocation_statuses,
            "return_profile": deal.return_profile,
            "duration": deal.duration,
            "risk_level": deal.risk_level,
        }

        title = f"Deal Summary: {deal.project.asset.name}" if deal.project and deal.project.asset else "Deal Summary"

    report = FinancialReport(
        created_by_user_id=user_id,
        recipient_user_id=recipient_user_id,
        project_id=project_id,
        deal_id=deal_id,
        report_type=report_type,
        title=title,
        content=content,
    )
    db.session.add(report)
    db.session.commit()

    create_notification(
        user_id=recipient_user_id,
        notification_type="financial_report",
        title=title,
        body=f"You have received a new financial report: {title}",
        related_entity_type="financial_report",
        related_entity_id=report.id,
    )

    return jsonify({"report": report.to_dict()}), 201