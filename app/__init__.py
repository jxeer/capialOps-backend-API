import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect

db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()


def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "capitalops-dev-secret-key-change-in-production")
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_recycle": 300,
        "pool_pre_ping": True,
    }

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    login_manager.login_view = "auth.login"

    from app.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    from app.routes.auth import auth_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.capital import capital_bp
    from app.routes.execution import execution_bp
    from app.routes.vendor import vendor_bp
    from app.routes.api import api_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(capital_bp, url_prefix="/capital")
    app.register_blueprint(execution_bp, url_prefix="/execution")
    app.register_blueprint(vendor_bp, url_prefix="/vendor")
    app.register_blueprint(api_bp, url_prefix="/api")

    with app.app_context():
        db.create_all()
        if os.environ.get("REPL_SLUG") or os.environ.get("REPLIT_DEV_DOMAIN"):
            seed_demo_data()

    return app


def seed_demo_data():
    from app.models import User, Portfolio, Asset, Project, Deal, Investor, Milestone, Vendor

    if User.query.first():
        return

    admin = User(
        username="admin",
        email="admin@capitalops.io",
        role="sponsor_admin",
        full_name="Julian (Sponsor Admin)",
    )
    admin.set_password("admin123")
    db.session.add(admin)

    pm = User(
        username="pm",
        email="pm@capitalops.io",
        role="project_manager",
        full_name="Sarah Chen (PM)",
    )
    pm.set_password("pm123")
    db.session.add(pm)

    gc = User(
        username="gc",
        email="gc@capitalops.io",
        role="general_contractor",
        full_name="Mike Torres (GC)",
    )
    gc.set_password("gc123")
    db.session.add(gc)

    portfolio = Portfolio(name="Core Portfolio", description="Primary real estate development portfolio")
    db.session.add(portfolio)
    db.session.flush()

    asset1 = Asset(
        portfolio_id=portfolio.id,
        name="The Meridian",
        location="Austin, TX",
        asset_type="Multifamily",
        square_footage=185000,
        status="Active",
        asset_manager="Julian",
    )
    asset2 = Asset(
        portfolio_id=portfolio.id,
        name="Parkside Commons",
        location="Denver, CO",
        asset_type="Mixed-Use",
        square_footage=120000,
        status="Pre-dev",
        asset_manager="Julian",
    )
    asset3 = Asset(
        portfolio_id=portfolio.id,
        name="Harbor Point",
        location="Miami, FL",
        asset_type="Commercial",
        square_footage=95000,
        status="Active",
        asset_manager="Julian",
    )
    db.session.add_all([asset1, asset2, asset3])
    db.session.flush()

    from datetime import date, timedelta

    project1 = Project(
        asset_id=asset1.id,
        portfolio_id=portfolio.id,
        phase="Construction",
        start_date=date(2025, 6, 1),
        target_completion=date(2026, 12, 31),
        budget_total=28500000,
        budget_actual=12400000,
        status="On Track",
        pm_assigned="Sarah Chen",
    )
    project2 = Project(
        asset_id=asset2.id,
        portfolio_id=portfolio.id,
        phase="Pre-Development",
        start_date=date(2025, 9, 1),
        target_completion=date(2027, 6, 30),
        budget_total=18200000,
        budget_actual=1850000,
        status="On Track",
        pm_assigned="Sarah Chen",
    )
    project3 = Project(
        asset_id=asset3.id,
        portfolio_id=portfolio.id,
        phase="Stabilization",
        start_date=date(2024, 1, 15),
        target_completion=date(2026, 6, 30),
        budget_total=14800000,
        budget_actual=13200000,
        status="At Risk",
        pm_assigned="Mike Torres",
    )
    db.session.add_all([project1, project2, project3])
    db.session.flush()

    deal1 = Deal(
        project_id=project1.id,
        portfolio_id=portfolio.id,
        capital_required=28500000,
        capital_raised=19200000,
        return_profile="18-22% IRR",
        duration="36 months",
        risk_level="Medium",
        complexity="High",
        phase="Active Raise",
        status="Open",
    )
    deal2 = Deal(
        project_id=project2.id,
        portfolio_id=portfolio.id,
        capital_required=18200000,
        capital_raised=4500000,
        return_profile="15-18% IRR",
        duration="48 months",
        risk_level="Medium-High",
        complexity="Medium",
        phase="Early Stage",
        status="Open",
    )
    deal3 = Deal(
        project_id=project3.id,
        portfolio_id=portfolio.id,
        capital_required=14800000,
        capital_raised=14800000,
        return_profile="12-15% IRR",
        duration="24 months",
        risk_level="Low",
        complexity="Low",
        phase="Fully Allocated",
        status="Closed",
    )
    db.session.add_all([deal1, deal2, deal3])
    db.session.flush()

    investors = [
        Investor(name="Westfield Capital Partners", accreditation_status="Verified", check_size_min=500000, check_size_max=5000000, asset_preference="Multifamily", geography_preference="Sunbelt", risk_tolerance="Medium", structure_preference="LP Equity", timeline_preference="3-5 years", strategic_interest="Value-Add", tier_level="Tier 1", status="Active"),
        Investor(name="Horizon Family Office", accreditation_status="Verified", check_size_min=1000000, check_size_max=10000000, asset_preference="Mixed-Use", geography_preference="Top 25 MSA", risk_tolerance="Low-Medium", structure_preference="Preferred Equity", timeline_preference="5-7 years", strategic_interest="Core-Plus", tier_level="Tier 2", status="Active"),
        Investor(name="Apex Growth Fund", accreditation_status="Verified", check_size_min=250000, check_size_max=2000000, asset_preference="Commercial", geography_preference="Southeast", risk_tolerance="Medium-High", structure_preference="LP Equity", timeline_preference="2-4 years", strategic_interest="Opportunistic", tier_level="Tier 1", status="Active"),
        Investor(name="Sterling Ventures", accreditation_status="Pending", check_size_min=100000, check_size_max=1000000, asset_preference="Multifamily", geography_preference="Texas", risk_tolerance="Low", structure_preference="Debt", timeline_preference="1-3 years", strategic_interest="Income", tier_level="Tier 1", status="Pending"),
        Investor(name="Cascade Investment Group", accreditation_status="Verified", check_size_min=2000000, check_size_max=15000000, asset_preference="All", geography_preference="National", risk_tolerance="Medium", structure_preference="LP Equity", timeline_preference="3-7 years", strategic_interest="Value-Add", tier_level="Tier 2", status="Active"),
    ]
    db.session.add_all(investors)
    db.session.flush()

    milestones = [
        Milestone(project_id=project1.id, portfolio_id=portfolio.id, name="Foundation Complete", category="Construction", target_date=date(2025, 9, 15), completion_date=date(2025, 9, 20), status="Complete", delay_explanation="5-day weather delay", risk_flag=False),
        Milestone(project_id=project1.id, portfolio_id=portfolio.id, name="Framing Complete", category="Construction", target_date=date(2025, 12, 1), completion_date=None, status="In Progress", delay_explanation=None, risk_flag=False),
        Milestone(project_id=project1.id, portfolio_id=portfolio.id, name="MEP Rough-In", category="Construction", target_date=date(2026, 2, 15), completion_date=None, status="Not Started", delay_explanation=None, risk_flag=False),
        Milestone(project_id=project1.id, portfolio_id=portfolio.id, name="Exterior Envelope", category="Construction", target_date=date(2026, 5, 1), completion_date=None, status="Not Started", delay_explanation=None, risk_flag=False),
        Milestone(project_id=project2.id, portfolio_id=portfolio.id, name="Zoning Approval", category="Entitlements", target_date=date(2025, 11, 1), completion_date=None, status="In Progress", delay_explanation=None, risk_flag=True),
        Milestone(project_id=project2.id, portfolio_id=portfolio.id, name="Site Plan Approval", category="Entitlements", target_date=date(2026, 1, 15), completion_date=None, status="Not Started", delay_explanation=None, risk_flag=False),
        Milestone(project_id=project3.id, portfolio_id=portfolio.id, name="Tenant Buildout", category="Stabilization", target_date=date(2025, 8, 1), completion_date=None, status="In Progress", delay_explanation="Supply chain delays on HVAC units", risk_flag=True),
        Milestone(project_id=project3.id, portfolio_id=portfolio.id, name="Certificate of Occupancy", category="Compliance", target_date=date(2025, 10, 15), completion_date=None, status="Not Started", delay_explanation=None, risk_flag=True),
    ]
    db.session.add_all(milestones)

    vendors = [
        Vendor(asset_id=asset1.id, portfolio_id=portfolio.id, name="Summit Construction Co.", type="General Contractor", coi_status="Current", sla_type="Standard", performance_score=92),
        Vendor(asset_id=asset1.id, portfolio_id=portfolio.id, name="ProMech HVAC", type="Mechanical", coi_status="Current", sla_type="Priority", performance_score=88),
        Vendor(asset_id=asset2.id, portfolio_id=portfolio.id, name="Urban Electric LLC", type="Electrical", coi_status="Expired", sla_type="Standard", performance_score=75),
        Vendor(asset_id=asset3.id, portfolio_id=portfolio.id, name="Coastal Plumbing", type="Plumbing", coi_status="Current", sla_type="Standard", performance_score=85),
        Vendor(asset_id=asset3.id, portfolio_id=portfolio.id, name="SafeGuard Fire Systems", type="Fire Protection", coi_status="Current", sla_type="Priority", performance_score=95),
    ]
    db.session.add_all(vendors)

    db.session.commit()
