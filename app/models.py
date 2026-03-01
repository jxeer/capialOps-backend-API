"""
CapitalOps - Database Models

Defines all SQLAlchemy ORM models for the CapitalOps data layer.
The schema follows the operational blueprint's 10 core entities, with every
entity carrying a portfolio_id foreign key to support future multi-portfolio scaling.

Entity Hierarchy:
    Portfolio (top-level)
      └── Asset (real estate property)
            ├── Project (development effort)
            │     ├── Deal (capital raise structure)
            │     │     └── Allocation (investor commitment)
            │     ├── Milestone (progress tracking)
            │     └── RiskFlag (risk event tracking)
            └── Vendor (service provider)
                  └── WorkOrder (assigned work)

Data Flow (per blueprint):
    Module 3 (Vendor/WorkOrder) → Module 2 (Milestone/RiskFlag) → Module 1 (Deal/Allocation)
    Operational truth → Governance interpretation → Investor transparency
"""

from app import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date


class User(UserMixin, db.Model):
    """
    Application user with role-based access control.

    Inherits from UserMixin to provide Flask-Login compatibility
    (is_authenticated, is_active, get_id, etc.).

    Roles and their module access:
        - sponsor_admin:      Full access to all three modules + admin actions
        - project_manager:    Module 2 (Execution Control) only
        - general_contractor: Limited Module 2 + limited Module 3
        - vendor:             Module 3 (own work orders only)
        - investor_tier1:     Module 1 (view matched deals, submit allocations)
        - investor_tier2:     Module 1 with priority access and enhanced reporting
    """
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)  # Werkzeug-hashed password
    role = db.Column(db.String(50), nullable=False)            # Role key from ROLE_PERMISSIONS
    full_name = db.Column(db.String(150))                      # Display name for the UI
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        """Hash and store a plaintext password using Werkzeug's secure hasher."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Verify a plaintext password against the stored hash."""
        return check_password_hash(self.password_hash, password)

    # Maps each role to a list of permission keys.
    # Used by has_permission() to check access at the route level.
    ROLE_PERMISSIONS = {
        "sponsor_admin": ["capital", "execution", "vendor", "admin"],
        "project_manager": ["execution"],
        "general_contractor": ["execution_limited", "vendor_limited"],
        "vendor": ["vendor_self"],
        "investor_tier1": ["capital_view"],
        "investor_tier2": ["capital_view", "capital_priority"],
    }

    def has_permission(self, perm):
        """Check if the user's role includes a specific permission key."""
        return perm in self.ROLE_PERMISSIONS.get(self.role, [])

    @property
    def role_display(self):
        """Return a human-readable label for the user's role (used in sidebar/UI)."""
        labels = {
            "sponsor_admin": "Sponsor Admin",
            "project_manager": "Project Manager",
            "general_contractor": "General Contractor",
            "vendor": "Vendor",
            "investor_tier1": "Investor (Tier 1)",
            "investor_tier2": "Priority Investor (Tier 2)",
        }
        return labels.get(self.role, self.role)


class Portfolio(db.Model):
    """
    Top-level entity representing a real estate portfolio.

    Currently only one portfolio exists, but the schema is designed so that
    all downstream entities carry a portfolio_id for future multi-portfolio expansion
    without requiring a schema rewrite (per the blueprint's scalability directive).
    """
    __tablename__ = "portfolios"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # One portfolio has many assets
    assets = db.relationship("Asset", backref="portfolio", lazy=True)


class Asset(db.Model):
    """
    A real estate property within a portfolio.

    Represents a physical property with key attributes like location,
    asset type (Multifamily, Mixed-Use, Commercial, etc.), and status
    (Pre-dev, Active, Stabilized).

    Each asset can have multiple projects and vendors assigned to it.
    """
    __tablename__ = "assets"

    id = db.Column(db.Integer, primary_key=True)
    portfolio_id = db.Column(db.Integer, db.ForeignKey("portfolios.id"), nullable=False)
    name = db.Column(db.String(200), nullable=False)        # Property name (e.g., "The Meridian")
    location = db.Column(db.String(300))                     # City, State
    asset_type = db.Column(db.String(100))                   # Multifamily, Mixed-Use, Commercial, etc.
    square_footage = db.Column(db.Integer)                   # Total building square footage
    status = db.Column(db.String(50))                        # Pre-dev, Active, or Stabilized
    asset_manager = db.Column(db.String(150))                # Name of assigned asset manager
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # One asset can have multiple development projects
    projects = db.relationship("Project", backref="asset", lazy=True)
    # One asset can have multiple vendors assigned
    vendors = db.relationship("Vendor", backref="asset", lazy=True)


class Project(db.Model):
    """
    A development project tied to a specific asset.

    Tracks the project lifecycle including phase, budget, timeline, and
    assigned project manager. Projects are the central hub connecting
    deals (capital) and milestones (execution) to an asset.

    Budget fields use Numeric(15,2) to handle values up to $9.99 trillion
    with cent-level precision.
    """
    __tablename__ = "projects"

    id = db.Column(db.Integer, primary_key=True)
    asset_id = db.Column(db.Integer, db.ForeignKey("assets.id"), nullable=False)
    portfolio_id = db.Column(db.Integer, db.ForeignKey("portfolios.id"), nullable=False)
    phase = db.Column(db.String(100))           # Construction, Pre-Development, Stabilization, etc.
    start_date = db.Column(db.Date)
    target_completion = db.Column(db.Date)
    budget_total = db.Column(db.Numeric(15, 2)) # Total approved budget
    budget_actual = db.Column(db.Numeric(15, 2)) # Actual spend to date
    status = db.Column(db.String(50))           # On Track, At Risk, Complete, etc.
    pm_assigned = db.Column(db.String(150))     # Name of assigned project manager
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # One project can have multiple deals (capital raise structures)
    deals = db.relationship("Deal", backref="project", lazy=True)
    # One project has many milestones for progress tracking
    milestones = db.relationship("Milestone", backref="project", lazy=True)


class Deal(db.Model):
    """
    A capital raise structure tied to a project.

    Represents the investment opportunity presented to investors.
    Tracks how much capital is needed, how much has been raised,
    the return profile, risk level, and current status.

    This is the core entity in Module 1 (Capital Engine) that gets
    matched to investors and receives allocations.
    """
    __tablename__ = "deals"

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=False)
    portfolio_id = db.Column(db.Integer, db.ForeignKey("portfolios.id"), nullable=False)
    capital_required = db.Column(db.Numeric(15, 2))  # Total capital needed for the deal
    capital_raised = db.Column(db.Numeric(15, 2))    # Capital committed/raised so far
    return_profile = db.Column(db.String(100))       # Expected returns (e.g., "18-22% IRR")
    duration = db.Column(db.String(100))             # Investment duration (e.g., "36 months")
    risk_level = db.Column(db.String(50))            # Low, Medium, Medium-High, High
    complexity = db.Column(db.String(50))            # Low, Medium, High
    phase = db.Column(db.String(100))                # Active Raise, Early Stage, Fully Allocated
    status = db.Column(db.String(50))                # Open or Closed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # One deal can have many investor allocations
    allocations = db.relationship("Allocation", backref="deal", lazy=True)


class Investor(db.Model):
    """
    An investor profile with preferences used for deal matching.

    Stores investor attributes that the Capital Engine's matching logic
    evaluates against open deals. Includes accreditation status, check
    size range, asset/geography/risk preferences, and tier level.

    Tier levels:
        - Tier 1: Standard investor access
        - Tier 2: Priority investor with early access and enhanced reporting
    """
    __tablename__ = "investors"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    accreditation_status = db.Column(db.String(50))     # Verified or Pending
    check_size_min = db.Column(db.Numeric(15, 2))       # Minimum investment amount
    check_size_max = db.Column(db.Numeric(15, 2))       # Maximum investment amount
    asset_preference = db.Column(db.String(100))        # Preferred asset type (or "All")
    geography_preference = db.Column(db.String(200))    # Preferred geography/market
    risk_tolerance = db.Column(db.String(50))           # Low, Low-Medium, Medium, Medium-High, High
    structure_preference = db.Column(db.String(100))    # LP Equity, Preferred Equity, Debt, Mezzanine
    timeline_preference = db.Column(db.String(100))     # Preferred hold period (e.g., "3-5 years")
    strategic_interest = db.Column(db.String(100))      # Value-Add, Core-Plus, Opportunistic, Income
    tier_level = db.Column(db.String(20))               # "Tier 1" or "Tier 2"
    status = db.Column(db.String(50))                   # Active or Pending
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # One investor can have multiple allocations across deals
    allocations = db.relationship("Allocation", backref="investor", lazy=True)


class Allocation(db.Model):
    """
    An investor's capital commitment to a specific deal.

    Tracks both soft commits (verbal/preliminary) and hard commits (legally binding).
    Created by the Sponsor Admin through the deal detail page in Module 1.

    Status flow: Pending → Approved → Funded (or Declined)
    """
    __tablename__ = "allocations"

    id = db.Column(db.Integer, primary_key=True)
    investor_id = db.Column(db.Integer, db.ForeignKey("investors.id"), nullable=False)
    deal_id = db.Column(db.Integer, db.ForeignKey("deals.id"), nullable=False)
    soft_commit_amount = db.Column(db.Numeric(15, 2))   # Preliminary/verbal commitment amount
    hard_commit_amount = db.Column(db.Numeric(15, 2))   # Legally binding commitment amount
    status = db.Column(db.String(50))                    # Pending, Approved, Funded, Declined
    notes = db.Column(db.Text)                           # Free-text notes from sponsor
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Milestone(db.Model):
    """
    A project milestone for tracking execution progress.

    Used by Module 2 (Execution Control) to provide governance-level
    visibility into project timelines. Supports risk flagging and
    delay explanation logging for structured PM reporting.

    Categories are standardized from day one (per blueprint) even with
    only 3 projects, to enable consistent cross-project reporting.

    Status flow: Not Started → In Progress → Complete
    """
    __tablename__ = "milestones"

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=False)
    portfolio_id = db.Column(db.Integer, db.ForeignKey("portfolios.id"), nullable=False)
    name = db.Column(db.String(200), nullable=False)     # Milestone name (e.g., "Foundation Complete")
    category = db.Column(db.String(100))                  # Standardized category (Construction, Entitlements, etc.)
    target_date = db.Column(db.Date)                      # Planned completion date
    completion_date = db.Column(db.Date)                  # Actual completion date (null if not complete)
    status = db.Column(db.String(50))                     # Not Started, In Progress, Complete
    delay_explanation = db.Column(db.Text)                # PM's structured explanation for any delays
    risk_flag = db.Column(db.Boolean, default=False)      # True if milestone is flagged as a risk
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Vendor(db.Model):
    """
    A contractor or service provider assigned to an asset.

    Tracked in Module 3 (Asset & Vendor Control) for operational discipline.
    Includes COI (Certificate of Insurance) compliance status, SLA type,
    and a performance score for vendor accountability.
    """
    __tablename__ = "vendors"

    id = db.Column(db.Integer, primary_key=True)
    asset_id = db.Column(db.Integer, db.ForeignKey("assets.id"), nullable=False)
    portfolio_id = db.Column(db.Integer, db.ForeignKey("portfolios.id"), nullable=False)
    name = db.Column(db.String(200), nullable=False)     # Vendor/company name
    type = db.Column(db.String(100))                      # Trade type (Electrical, Mechanical, Plumbing, etc.)
    coi_status = db.Column(db.String(50))                 # Current, Expired, or Pending
    sla_type = db.Column(db.String(50))                   # Standard or Priority
    performance_score = db.Column(db.Integer)             # 0-100 score for vendor performance
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # One vendor can have multiple work orders
    work_orders = db.relationship("WorkOrder", backref="vendor", lazy=True)


class WorkOrder(db.Model):
    """
    A work assignment for a vendor on a specific asset.

    Tracks vendor-assigned work including type, priority, cost, and
    CapEx vs OpEx classification. Used in Module 3 for operational
    cost tracking and vendor accountability.
    """
    __tablename__ = "work_orders"

    id = db.Column(db.Integer, primary_key=True)
    vendor_id = db.Column(db.Integer, db.ForeignKey("vendors.id"), nullable=False)
    asset_id = db.Column(db.Integer, db.ForeignKey("assets.id"), nullable=False)
    portfolio_id = db.Column(db.Integer, db.ForeignKey("portfolios.id"), nullable=False)
    type = db.Column(db.String(100))                 # Work type (Maintenance, Repair, Installation, etc.)
    priority = db.Column(db.String(50))              # Normal, High, or Urgent
    cost = db.Column(db.Numeric(15, 2))              # Estimated or actual cost
    capex_flag = db.Column(db.Boolean, default=False) # True = Capital Expenditure, False = Operating Expense
    status = db.Column(db.String(50))                # Open, In Progress, Complete, Cancelled
    completion_date = db.Column(db.Date)             # Date work was completed
    photo_url = db.Column(db.String(500))            # URL for completion photo documentation
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class RiskFlag(db.Model):
    """
    A risk event associated with a project.

    Provides category-based risk tracking (not custom per project)
    to enable standardized risk reporting across the portfolio.
    Used by Module 2 (Execution Control) in the governance event log.

    Status flow: Open → Resolved
    """
    __tablename__ = "risk_flags"

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=False)
    portfolio_id = db.Column(db.Integer, db.ForeignKey("portfolios.id"), nullable=False)
    category = db.Column(db.String(100))             # Risk category (Schedule, Budget, Compliance, etc.)
    severity = db.Column(db.String(50))              # Low, Medium, or High
    description = db.Column(db.Text)                 # Detailed description of the risk
    status = db.Column(db.String(50), default="Open") # Open or Resolved
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    resolved_at = db.Column(db.DateTime)             # Timestamp when the risk was resolved
