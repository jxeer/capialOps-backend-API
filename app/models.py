"""
CapitalOps API - Database Models

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
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date, timedelta
import secrets


class User(db.Model):
    """
    Application user with role-based access control.

    Used for JWT authentication — the user logs in via /api/auth/login
    and receives a JWT containing their user ID and role.

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
    password_hash = db.Column(db.String(256), nullable=True)   # Werkzeug-hashed password (nullable for Google-only accounts)
    role = db.Column(db.String(50), nullable=False)            # Role key from ROLE_PERMISSIONS
    full_name = db.Column(db.String(150))                      # Display name for the UI
    google_id = db.Column(db.String(255), unique=True, nullable=True)  # Google OAuth subject ID (set when user signs in via Google)

    # Profile fields (Phase 4 - Profile Enhancement)
    profile_type = db.Column(db.String(20))                    # "investor", "vendor", "developer"
    profile_status = db.Column(db.String(20), default="pending")  # "pending", "active", "inactive", "suspended"
    title = db.Column(db.String(100))
    organization = db.Column(db.String(200))
    linked_in_url = db.Column(db.String(500))
    bio = db.Column(db.Text)
    
    profile_image = db.Column(db.String(500))
    
    # Investor-specific fields
    geographic_focus = db.Column(db.String(200))
    investment_stage = db.Column(db.String(100))
    target_return = db.Column(db.String(100))
    check_size_min = db.Column(db.Numeric(15, 2))
    check_size_max = db.Column(db.Numeric(15, 2))
    risk_tolerance = db.Column(db.String(20))                  # "Conservative", "Moderate", "Aggressive"
    strategic_interest = db.Column(db.String(100))
    
    # Vendor-specific fields
    service_types = db.Column(db.String(200))
    geographic_service_area = db.Column(db.String(200))
    years_of_experience = db.Column(db.String(50))
    certifications = db.Column(db.Text)
    average_project_size = db.Column(db.Numeric(15, 2))
    
    # Developer-specific fields
    development_focus = db.Column(db.String(100))
    development_type = db.Column(db.String(100))
    team_size = db.Column(db.Integer)
    portfolio_value = db.Column(db.Numeric(15, 2))
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        """Hash and store a plaintext password using Werkzeug's secure hasher."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Verify a plaintext password against the stored hash.

        Returns False if the user has no password hash (Google-only account).
        """
        if not self.password_hash:
            return False
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
        """Return a human-readable label for the user's role."""
        labels = {
            "sponsor_admin": "Sponsor Admin",
            "project_manager": "Project Manager",
            "general_contractor": "General Contractor",
            "vendor": "Vendor",
            "investor_tier1": "Investor (Tier 1)",
            "investor_tier2": "Priority Investor (Tier 2)",
        }
        return labels.get(self.role, self.role)

    def to_dict(self):
        """Serialize user to a JSON-safe dictionary (excludes password hash)."""
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "role": self.role,
            "role_display": self.role_display,
            "full_name": self.full_name,
            "google_id": self.google_id,
            "has_password": self.password_hash is not None,

            # Profile fields (Phase 4)
            "profileType": self.profile_type,
            "profileStatus": self.profile_status,
            "title": self.title,
            "organization": self.organization,
            "linkedInUrl": self.linked_in_url,
            "bio": self.bio,
            "profileImage": self.profile_image,
            
            # Investor-specific
            "geographicFocus": self.geographic_focus,
            "investmentStage": self.investment_stage,
            "targetReturn": self.target_return,
            "checkSizeMin": float(self.check_size_min) if self.check_size_min else None,
            "checkSizeMax": float(self.check_size_max) if self.check_size_max else None,
            "riskTolerance": self.risk_tolerance,
            "strategicInterest": self.strategic_interest,
            
            # Vendor-specific
            "serviceTypes": self.service_types,
            "geographicServiceArea": self.geographic_service_area,
            "yearsOfExperience": self.years_of_experience,
            "certifications": self.certifications,
            "averageProjectSize": float(self.average_project_size) if self.average_project_size else None,
            
            # Developer-specific
            "developmentFocus": self.development_focus,
            "developmentType": self.development_type,
            "teamSize": self.team_size,
            "portfolioValue": float(self.portfolio_value) if self.portfolio_value else None,
            
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Portfolio(db.Model):
    """
    Top-level entity representing a real estate portfolio.

    Currently only one portfolio exists, but the schema is designed so that
    all downstream entities carry a portfolio_id for future multi-portfolio expansion
    without requiring a schema rewrite.
    
    Each portfolio is owned by a specific user (user_id).
    """
    __tablename__ = "portfolios"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)  # Owner
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # One portfolio has many assets
    assets = db.relationship("Asset", backref="portfolio", lazy=True)
    
    # Relationship to owner user
    owner = db.relationship("User", backref="portfolios")

    def to_dict(self):
        """Serialize portfolio to a JSON-safe dictionary."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "name": self.name,
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Asset(db.Model):
    """
    A real estate property within a portfolio.

    Represents a physical property with key attributes like location,
    asset type (Multifamily, Mixed-Use, Commercial, etc.), and status.

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
    
    # Media: JSON array of {url, type, name} objects (base64 data URLs or external URLs)
    media = db.Column(db.JSON, default=list)

    # One asset can have multiple development projects
    projects = db.relationship("Project", backref="asset", lazy=True)
    # One asset can have multiple vendors assigned
    vendors = db.relationship("Vendor", backref="asset", lazy=True)

    def to_dict(self):
        """Serialize asset to a JSON-safe dictionary."""
        return {
            "id": self.id,
            "portfolio_id": self.portfolio_id,
            "name": self.name,
            "location": self.location,
            "asset_type": self.asset_type,
            "square_footage": self.square_footage,
            "status": self.status,
            "asset_manager": self.asset_manager,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "media": self.media or [],
        }


class Project(db.Model):
    """
    A development project tied to a specific asset.

    Tracks the project lifecycle including phase, budget, timeline, and
    assigned project manager. Projects are the central hub connecting
    deals (capital) and milestones (execution) to an asset.
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
    
    # Media: JSON array of {url, type, name} objects (base64 data URLs or external URLs)
    media = db.Column(db.JSON, default=list)

    # One project can have multiple deals (capital raise structures)
    deals = db.relationship("Deal", backref="project", lazy=True)
    # One project has many milestones for progress tracking
    milestones = db.relationship("Milestone", backref="project", lazy=True)

    def to_dict(self):
        """Serialize project to a JSON-safe dictionary."""
        return {
            "id": self.id,
            "asset_id": self.asset_id,
            "asset_name": self.asset.name if self.asset else None,
            "portfolio_id": self.portfolio_id,
            "phase": self.phase,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "target_completion": self.target_completion.isoformat() if self.target_completion else None,
            "budget_total": float(self.budget_total or 0),
            "budget_actual": float(self.budget_actual or 0),
            "status": self.status,
            "pm_assigned": self.pm_assigned,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "media": self.media or [],
        }


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

    def to_dict(self):
        """Serialize deal to a JSON-safe dictionary."""
        return {
            "id": self.id,
            "project_id": self.project_id,
            "project_name": self.project.asset.name if self.project and self.project.asset else None,
            "portfolio_id": self.portfolio_id,
            "capital_required": float(self.capital_required or 0),
            "capital_raised": float(self.capital_raised or 0),
            "return_profile": self.return_profile,
            "duration": self.duration,
            "risk_level": self.risk_level,
            "complexity": self.complexity,
            "phase": self.phase,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Investor(db.Model):
    """
    An investor profile with preferences used for deal matching.

    Stores investor attributes that the Capital Engine's matching logic
    evaluates against open deals.

    Tier levels:
        - Tier 1: Standard investor access
        - Tier 2: Priority investor with early access and enhanced reporting
    """
    __tablename__ = "investors"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)  # Owner (optional for shared investors)
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

    def to_dict(self):
        """Serialize investor to a JSON-safe dictionary."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "name": self.name,
            "accreditation_status": self.accreditation_status,
            "check_size_min": float(self.check_size_min or 0),
            "check_size_max": float(self.check_size_max or 0),
            "asset_preference": self.asset_preference,
            "geography_preference": self.geography_preference,
            "risk_tolerance": self.risk_tolerance,
            "structure_preference": self.structure_preference,
            "timeline_preference": self.timeline_preference,
            "strategic_interest": self.strategic_interest,
            "tier_level": self.tier_level,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Allocation(db.Model):
    """
    An investor's capital commitment to a specific deal.

    Tracks both soft commits (verbal/preliminary) and hard commits (legally binding).
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

    def to_dict(self):
        """Serialize allocation to a JSON-safe dictionary."""
        return {
            "id": self.id,
            "investor_id": self.investor_id,
            "investor_name": self.investor.name if self.investor else None,
            "deal_id": self.deal_id,
            "soft_commit_amount": float(self.soft_commit_amount or 0),
            "hard_commit_amount": float(self.hard_commit_amount or 0),
            "status": self.status,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Milestone(db.Model):
    """
    A project milestone for tracking execution progress.

    Used by Module 2 (Execution Control) to provide governance-level
    visibility into project timelines.
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

    def to_dict(self):
        """Serialize milestone to a JSON-safe dictionary."""
        return {
            "id": self.id,
            "project_id": self.project_id,
            "portfolio_id": self.portfolio_id,
            "name": self.name,
            "category": self.category,
            "target_date": self.target_date.isoformat() if self.target_date else None,
            "completion_date": self.completion_date.isoformat() if self.completion_date else None,
            "status": self.status,
            "delay_explanation": self.delay_explanation,
            "risk_flag": self.risk_flag,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Vendor(db.Model):
    """
    A contractor or service provider assigned to an asset.

    Tracked in Module 3 (Asset & Vendor Control) for operational discipline.
    Includes COI compliance, SLA type, and performance scoring.
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

    def to_dict(self):
        """Serialize vendor to a JSON-safe dictionary."""
        return {
            "id": self.id,
            "asset_id": self.asset_id,
            "asset_name": self.asset.name if self.asset else None,
            "portfolio_id": self.portfolio_id,
            "name": self.name,
            "type": self.type,
            "coi_status": self.coi_status,
            "sla_type": self.sla_type,
            "performance_score": self.performance_score,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class WorkOrder(db.Model):
    """
    A work assignment for a vendor on a specific asset.

    Tracks vendor-assigned work including type, priority, cost, and
    CapEx vs OpEx classification.
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
    description = db.Column(db.Text)                 # Free-text description of the work to be done
    photo_url = db.Column(db.String(500))            # URL for completion photo documentation
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        """Serialize work order to a JSON-safe dictionary."""
        return {
            "id": self.id,
            "vendor_id": self.vendor_id,
            "vendor_name": self.vendor.name if self.vendor else None,
            "asset_id": self.asset_id,
            "portfolio_id": self.portfolio_id,
            "type": self.type,
            "priority": self.priority,
            "cost": float(self.cost or 0),
            "capex_flag": self.capex_flag,
            "status": self.status,
            "completion_date": self.completion_date.isoformat() if self.completion_date else None,
            "description": self.description,
            "photo_url": self.photo_url,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class RiskFlag(db.Model):
    """
    A risk event associated with a project.

    Provides category-based risk tracking for standardized risk reporting.
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

    def to_dict(self):
        """Serialize risk flag to a JSON-safe dictionary."""
        return {
            "id": self.id,
            "project_id": self.project_id,
            "portfolio_id": self.portfolio_id,
            "category": self.category,
            "severity": self.severity,
            "description": self.description,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
        }


class ConnectionRequest(db.Model):
    """
    A connection request between two users.
    
    Status flow: pending → accepted/declined
    """
    __tablename__ = "connection_requests"
    
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    status = db.Column(db.String(20), default="pending")  # "pending", "accepted", "declined"
    message = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    responded_at = db.Column(db.DateTime)
    
    sender = db.relationship("User", foreign_keys=[sender_id], backref="sent_connection_requests")
    receiver = db.relationship("User", foreign_keys=[receiver_id], backref="received_connection_requests")
    
    def to_dict(self):
        """Serialize connection request to a JSON-safe dictionary."""
        return {
            "id": self.id,
            "senderId": self.sender_id,
            "receiverId": self.receiver_id,
            "senderName": self.sender.full_name if self.sender else None,
            "receiverName": self.receiver.full_name if self.receiver else None,
            "status": self.status,
            "message": self.message,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
            "respondedAt": self.responded_at.isoformat() if self.responded_at else None,
        }


class Conversation(db.Model):
    """
    A 1-on-1 conversation between two users.
    """
    __tablename__ = "conversations"
    
    id = db.Column(db.Integer, primary_key=True)
    user_id1 = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    user_id2 = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user1 = db.relationship("User", foreign_keys=[user_id1])
    user2 = db.relationship("User", foreign_keys=[user_id2])
    
    def to_dict(self):
        """Serialize conversation to a JSON-safe dictionary."""
        return {
            "id": self.id,
            "userId1": self.user_id1,
            "userId2": self.user_id2,
            "user1Name": self.user1.full_name if self.user1 else None,
            "user2Name": self.user2.full_name if self.user2 else None,
            "updatedAt": self.updated_at.isoformat() if self.updated_at else None,
        }


class Message(db.Model):
    """
    An individual message in a conversation.
    """
    __tablename__ = "messages"
    
    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey("conversations.id"), nullable=False)
    sender_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    content = db.Column(db.Text, nullable=False)
    read_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    sender = db.relationship("User", foreign_keys=[sender_id])
    conversation = db.relationship("Conversation", backref="messages")
    
    def to_dict(self):
        """Serialize message to a JSON-safe dictionary."""
        return {
            "id": self.id,
            "conversationId": self.conversation_id,
            "senderId": self.sender_id,
            "senderName": self.sender.full_name if self.sender else None,
            "content": self.content,
            "readAt": self.read_at.isoformat() if self.read_at else None,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
        }


class PasswordResetToken(db.Model):
    """
    A single-use password reset token sent to a user's email.

    Tokens are generated when a user requests a password reset and are
    valid for a limited time (default: 30 minutes). They are deleted
    immediately after use or expiration.
    """
    __tablename__ = "password_reset_tokens"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    token = db.Column(db.String(64), unique=True, nullable=False, index=True)
    expires_at = db.Column(db.DateTime, nullable=False)
    used = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", backref="password_reset_tokens")

    @classmethod
    def generate_token(cls, user_id, expiry_minutes=30):
        """
        Create a new reset token for the given user.

        Args:
            user_id: The ID of the user requesting the reset.
            expiry_minutes: How long the token should be valid (default 30).

        Returns:
            PasswordResetToken: The newly created token instance.
        """
        token = secrets.token_urlsafe(48)
        expires_at = datetime.utcnow() + timedelta(minutes=expiry_minutes)
        return cls(
            user_id=user_id,
            token=token,
            expires_at=expires_at,
        )

    @property
    def is_valid(self):
        """Return True if the token has not expired and has not been used."""
        return not self.used and datetime.utcnow() < self.expires_at


class MfaCode(db.Model):
    """
    A single-use MFA verification code sent to user's email.
    Codes are valid for 5 minutes and deleted after use.
    """
    __tablename__ = "mfa_codes"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    code = db.Column(db.String(6), nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    used = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", backref="mfa_codes")

    @classmethod
    def generate_code(cls, user_id, expiry_minutes=5):
        """Create a new 6-digit MFA code for the given user."""
        import secrets
        code = "".join([str(secrets.randbelow(10)) for _ in range(6)])
        expires_at = datetime.utcnow() + timedelta(minutes=expiry_minutes)
        mfa_code = cls(user_id=user_id, code=code, expires_at=expires_at)
        db.session.add(mfa_code)
        db.session.commit()
        return mfa_code

    @property
    def is_valid(self):
        """Return True if the code has not expired and has not been used."""
        return not self.used and datetime.utcnow() < self.expires_at
