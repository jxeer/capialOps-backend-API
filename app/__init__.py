"""
CapitalOps - Application Factory & Initialization

This module defines the Flask application factory (create_app), which:
  1. Configures the app (secret key, database URI, SQLAlchemy options)
  2. Initializes extensions (SQLAlchemy, Flask-Login, CSRF protection)
  3. Registers all route blueprints organized by module
  4. Creates database tables and seeds demo data in development

The application follows a modular blueprint architecture:
  - auth_bp:      Authentication (login/logout)
  - dashboard_bp: Portfolio-level overview dashboard (root /)
  - capital_bp:   Module 1 — Capital Engine (/capital)
  - execution_bp: Module 2 — Execution Control (/execution)
  - vendor_bp:    Module 3 — Asset & Vendor Control (/vendor)
  - api_bp:       JSON API endpoints (/api)

Extensions are declared at module level so they can be imported
by other modules (e.g., `from app import db`).
"""

import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect

# --- Extension Instances (module-level for shared access) ---

# SQLAlchemy ORM instance — manages all database models and sessions
db = SQLAlchemy()

# Flask-Login manager — handles user session management and authentication
login_manager = LoginManager()

# CSRF protection — prevents cross-site request forgery on all POST forms
csrf = CSRFProtect()


def create_app():
    """
    Application factory function.

    Creates and configures the Flask app, initializes extensions,
    registers blueprints, and sets up the database.

    Returns:
        Flask: The fully configured Flask application instance.
    """
    app = Flask(__name__)

    # --- App Configuration ---

    # Secret key for session signing and CSRF tokens.
    # Uses a stable default in development so tokens survive server restarts.
    # In production, set the SECRET_KEY environment variable to a secure random value.
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "capitalops-dev-secret-key-change-in-production")

    # PostgreSQL connection string provided by Replit's managed database
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")

    # Disable modification tracking to save memory (we don't use this feature)
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # Connection pool settings to handle database reconnections gracefully
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_recycle": 300,   # Recycle connections every 5 minutes
        "pool_pre_ping": True, # Test connections before use to avoid stale connections
    }

    # --- Initialize Extensions ---

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    # Redirect unauthenticated users to the login page
    login_manager.login_view = "auth.login"

    # --- User Loader Callback ---
    # Flask-Login calls this to reload the user object from the session's stored user ID
    from app.models import User

    @login_manager.user_loader
    def load_user(user_id):
        """Load a user by their primary key ID for Flask-Login session management."""
        return db.session.get(User, int(user_id))

    # --- Register Blueprints ---
    # Each blueprint corresponds to a functional area of the application.
    # URL prefixes keep module routes cleanly separated.

    from app.routes.auth import auth_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.capital import capital_bp
    from app.routes.execution import execution_bp
    from app.routes.vendor import vendor_bp
    from app.routes.api import api_bp

    app.register_blueprint(auth_bp)                              # /login, /logout
    app.register_blueprint(dashboard_bp)                         # / (root dashboard)
    app.register_blueprint(capital_bp, url_prefix="/capital")     # Module 1
    app.register_blueprint(execution_bp, url_prefix="/execution") # Module 2
    app.register_blueprint(vendor_bp, url_prefix="/vendor")       # Module 3
    app.register_blueprint(api_bp, url_prefix="/api")             # JSON API

    # --- Database Initialization ---
    with app.app_context():
        # Create all tables defined by SQLAlchemy models (safe to call repeatedly)
        db.create_all()

        # Only seed demo data in Replit development environments.
        # Production deployments should not auto-seed demo accounts.
        if os.environ.get("REPL_SLUG") or os.environ.get("REPLIT_DEV_DOMAIN"):
            seed_demo_data()

    return app


def seed_demo_data():
    """
    Populate the database with demo data for development and testing.

    Seeds the following:
      - 3 user accounts (Sponsor Admin, Project Manager, General Contractor)
      - 1 portfolio with 3 assets across different markets
      - 3 projects in different phases (Construction, Pre-Dev, Stabilization)
      - 3 deals with varying capital raise progress
      - 5 investor profiles with diverse preferences
      - 8 milestones across all projects (some with risk flags)
      - 5 vendors across all assets

    Skips seeding if any users already exist (idempotent).
    """
    from app.models import User, Portfolio, Asset, Project, Deal, Investor, Milestone, Vendor

    # Guard: Only seed if the database is empty (no existing users)
    if User.query.first():
        return

    # --- Demo User Accounts ---
    # Each account represents a different role for testing role-based access

    # Sponsor Admin — full access to all three modules
    admin = User(
        username="admin",
        email="admin@capitalops.io",
        role="sponsor_admin",
        full_name="Julian (Sponsor Admin)",
    )
    admin.set_password("admin123")
    db.session.add(admin)

    # Project Manager — access to Execution Control only
    pm = User(
        username="pm",
        email="pm@capitalops.io",
        role="project_manager",
        full_name="Sarah Chen (PM)",
    )
    pm.set_password("pm123")
    db.session.add(pm)

    # General Contractor — limited execution + vendor access
    gc = User(
        username="gc",
        email="gc@capitalops.io",
        role="general_contractor",
        full_name="Mike Torres (GC)",
    )
    gc.set_password("gc123")
    db.session.add(gc)

    # --- Portfolio ---
    # Top-level entity; all assets/projects belong to a portfolio.
    # PortfolioID is included on all entities to enable future multi-portfolio scaling.
    portfolio = Portfolio(name="Core Portfolio", description="Primary real estate development portfolio")
    db.session.add(portfolio)
    db.session.flush()  # Flush to generate portfolio.id for foreign keys

    # --- Assets ---
    # Three real estate properties across different markets and asset types

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
    db.session.flush()  # Flush to generate asset IDs

    # --- Projects ---
    # Each project is linked to one asset and represents a development effort

    from datetime import date, timedelta

    # Project 1: Active construction, on track
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
    # Project 2: Early-stage pre-development
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
    # Project 3: Stabilization phase, flagged as at risk
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
    db.session.flush()  # Flush to generate project IDs

    # --- Deals ---
    # Each deal represents a capital raise structure tied to a project

    # Deal 1: Active raise, 67% funded
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
    # Deal 2: Early stage raise, 25% funded
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
    # Deal 3: Fully allocated and closed
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
    db.session.flush()  # Flush to generate deal IDs

    # --- Investors ---
    # Five investor profiles with varying preferences, check sizes, and tiers.
    # These are used by the deal-investor matching engine in Module 1.

    investors = [
        Investor(name="Westfield Capital Partners", accreditation_status="Verified", check_size_min=500000, check_size_max=5000000, asset_preference="Multifamily", geography_preference="Sunbelt", risk_tolerance="Medium", structure_preference="LP Equity", timeline_preference="3-5 years", strategic_interest="Value-Add", tier_level="Tier 1", status="Active"),
        Investor(name="Horizon Family Office", accreditation_status="Verified", check_size_min=1000000, check_size_max=10000000, asset_preference="Mixed-Use", geography_preference="Top 25 MSA", risk_tolerance="Low-Medium", structure_preference="Preferred Equity", timeline_preference="5-7 years", strategic_interest="Core-Plus", tier_level="Tier 2", status="Active"),
        Investor(name="Apex Growth Fund", accreditation_status="Verified", check_size_min=250000, check_size_max=2000000, asset_preference="Commercial", geography_preference="Southeast", risk_tolerance="Medium-High", structure_preference="LP Equity", timeline_preference="2-4 years", strategic_interest="Opportunistic", tier_level="Tier 1", status="Active"),
        Investor(name="Sterling Ventures", accreditation_status="Pending", check_size_min=100000, check_size_max=1000000, asset_preference="Multifamily", geography_preference="Texas", risk_tolerance="Low", structure_preference="Debt", timeline_preference="1-3 years", strategic_interest="Income", tier_level="Tier 1", status="Pending"),
        Investor(name="Cascade Investment Group", accreditation_status="Verified", check_size_min=2000000, check_size_max=15000000, asset_preference="All", geography_preference="National", risk_tolerance="Medium", structure_preference="LP Equity", timeline_preference="3-7 years", strategic_interest="Value-Add", tier_level="Tier 2", status="Active"),
    ]
    db.session.add_all(investors)
    db.session.flush()

    # --- Milestones ---
    # Construction and development milestones across all three projects.
    # Some are flagged with risk_flag=True to demonstrate the risk monitoring system.

    milestones = [
        # Project 1 (The Meridian) — Construction milestones
        Milestone(project_id=project1.id, portfolio_id=portfolio.id, name="Foundation Complete", category="Construction", target_date=date(2025, 9, 15), completion_date=date(2025, 9, 20), status="Complete", delay_explanation="5-day weather delay", risk_flag=False),
        Milestone(project_id=project1.id, portfolio_id=portfolio.id, name="Framing Complete", category="Construction", target_date=date(2025, 12, 1), completion_date=None, status="In Progress", delay_explanation=None, risk_flag=False),
        Milestone(project_id=project1.id, portfolio_id=portfolio.id, name="MEP Rough-In", category="Construction", target_date=date(2026, 2, 15), completion_date=None, status="Not Started", delay_explanation=None, risk_flag=False),
        Milestone(project_id=project1.id, portfolio_id=portfolio.id, name="Exterior Envelope", category="Construction", target_date=date(2026, 5, 1), completion_date=None, status="Not Started", delay_explanation=None, risk_flag=False),
        # Project 2 (Parkside Commons) — Entitlements milestones
        Milestone(project_id=project2.id, portfolio_id=portfolio.id, name="Zoning Approval", category="Entitlements", target_date=date(2025, 11, 1), completion_date=None, status="In Progress", delay_explanation=None, risk_flag=True),
        Milestone(project_id=project2.id, portfolio_id=portfolio.id, name="Site Plan Approval", category="Entitlements", target_date=date(2026, 1, 15), completion_date=None, status="Not Started", delay_explanation=None, risk_flag=False),
        # Project 3 (Harbor Point) — Stabilization milestones (both flagged as at-risk)
        Milestone(project_id=project3.id, portfolio_id=portfolio.id, name="Tenant Buildout", category="Stabilization", target_date=date(2025, 8, 1), completion_date=None, status="In Progress", delay_explanation="Supply chain delays on HVAC units", risk_flag=True),
        Milestone(project_id=project3.id, portfolio_id=portfolio.id, name="Certificate of Occupancy", category="Compliance", target_date=date(2025, 10, 15), completion_date=None, status="Not Started", delay_explanation=None, risk_flag=True),
    ]
    db.session.add_all(milestones)

    # --- Vendors ---
    # Service providers assigned to specific assets. Includes COI status
    # and SLA type to demonstrate vendor compliance tracking.

    vendors = [
        Vendor(asset_id=asset1.id, portfolio_id=portfolio.id, name="Summit Construction Co.", type="General Contractor", coi_status="Current", sla_type="Standard", performance_score=92),
        Vendor(asset_id=asset1.id, portfolio_id=portfolio.id, name="ProMech HVAC", type="Mechanical", coi_status="Current", sla_type="Priority", performance_score=88),
        Vendor(asset_id=asset2.id, portfolio_id=portfolio.id, name="Urban Electric LLC", type="Electrical", coi_status="Expired", sla_type="Standard", performance_score=75),
        Vendor(asset_id=asset3.id, portfolio_id=portfolio.id, name="Coastal Plumbing", type="Plumbing", coi_status="Current", sla_type="Standard", performance_score=85),
        Vendor(asset_id=asset3.id, portfolio_id=portfolio.id, name="SafeGuard Fire Systems", type="Fire Protection", coi_status="Current", sla_type="Priority", performance_score=95),
    ]
    db.session.add_all(vendors)

    # Commit all seeded data in a single transaction
    db.session.commit()
