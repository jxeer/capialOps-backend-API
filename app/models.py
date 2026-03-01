from app import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date


class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(50), nullable=False)
    full_name = db.Column(db.String(150))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    ROLE_PERMISSIONS = {
        "sponsor_admin": ["capital", "execution", "vendor", "admin"],
        "project_manager": ["execution"],
        "general_contractor": ["execution_limited", "vendor_limited"],
        "vendor": ["vendor_self"],
        "investor_tier1": ["capital_view"],
        "investor_tier2": ["capital_view", "capital_priority"],
    }

    def has_permission(self, perm):
        return perm in self.ROLE_PERMISSIONS.get(self.role, [])

    @property
    def role_display(self):
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
    __tablename__ = "portfolios"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    assets = db.relationship("Asset", backref="portfolio", lazy=True)


class Asset(db.Model):
    __tablename__ = "assets"
    id = db.Column(db.Integer, primary_key=True)
    portfolio_id = db.Column(db.Integer, db.ForeignKey("portfolios.id"), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    location = db.Column(db.String(300))
    asset_type = db.Column(db.String(100))
    square_footage = db.Column(db.Integer)
    status = db.Column(db.String(50))
    asset_manager = db.Column(db.String(150))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    projects = db.relationship("Project", backref="asset", lazy=True)
    vendors = db.relationship("Vendor", backref="asset", lazy=True)


class Project(db.Model):
    __tablename__ = "projects"
    id = db.Column(db.Integer, primary_key=True)
    asset_id = db.Column(db.Integer, db.ForeignKey("assets.id"), nullable=False)
    portfolio_id = db.Column(db.Integer, db.ForeignKey("portfolios.id"), nullable=False)
    phase = db.Column(db.String(100))
    start_date = db.Column(db.Date)
    target_completion = db.Column(db.Date)
    budget_total = db.Column(db.Numeric(15, 2))
    budget_actual = db.Column(db.Numeric(15, 2))
    status = db.Column(db.String(50))
    pm_assigned = db.Column(db.String(150))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    deals = db.relationship("Deal", backref="project", lazy=True)
    milestones = db.relationship("Milestone", backref="project", lazy=True)


class Deal(db.Model):
    __tablename__ = "deals"
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=False)
    portfolio_id = db.Column(db.Integer, db.ForeignKey("portfolios.id"), nullable=False)
    capital_required = db.Column(db.Numeric(15, 2))
    capital_raised = db.Column(db.Numeric(15, 2))
    return_profile = db.Column(db.String(100))
    duration = db.Column(db.String(100))
    risk_level = db.Column(db.String(50))
    complexity = db.Column(db.String(50))
    phase = db.Column(db.String(100))
    status = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    allocations = db.relationship("Allocation", backref="deal", lazy=True)


class Investor(db.Model):
    __tablename__ = "investors"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    accreditation_status = db.Column(db.String(50))
    check_size_min = db.Column(db.Numeric(15, 2))
    check_size_max = db.Column(db.Numeric(15, 2))
    asset_preference = db.Column(db.String(100))
    geography_preference = db.Column(db.String(200))
    risk_tolerance = db.Column(db.String(50))
    structure_preference = db.Column(db.String(100))
    timeline_preference = db.Column(db.String(100))
    strategic_interest = db.Column(db.String(100))
    tier_level = db.Column(db.String(20))
    status = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    allocations = db.relationship("Allocation", backref="investor", lazy=True)


class Allocation(db.Model):
    __tablename__ = "allocations"
    id = db.Column(db.Integer, primary_key=True)
    investor_id = db.Column(db.Integer, db.ForeignKey("investors.id"), nullable=False)
    deal_id = db.Column(db.Integer, db.ForeignKey("deals.id"), nullable=False)
    soft_commit_amount = db.Column(db.Numeric(15, 2))
    hard_commit_amount = db.Column(db.Numeric(15, 2))
    status = db.Column(db.String(50))
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Milestone(db.Model):
    __tablename__ = "milestones"
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=False)
    portfolio_id = db.Column(db.Integer, db.ForeignKey("portfolios.id"), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(100))
    target_date = db.Column(db.Date)
    completion_date = db.Column(db.Date)
    status = db.Column(db.String(50))
    delay_explanation = db.Column(db.Text)
    risk_flag = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Vendor(db.Model):
    __tablename__ = "vendors"
    id = db.Column(db.Integer, primary_key=True)
    asset_id = db.Column(db.Integer, db.ForeignKey("assets.id"), nullable=False)
    portfolio_id = db.Column(db.Integer, db.ForeignKey("portfolios.id"), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    type = db.Column(db.String(100))
    coi_status = db.Column(db.String(50))
    sla_type = db.Column(db.String(50))
    performance_score = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    work_orders = db.relationship("WorkOrder", backref="vendor", lazy=True)


class WorkOrder(db.Model):
    __tablename__ = "work_orders"
    id = db.Column(db.Integer, primary_key=True)
    vendor_id = db.Column(db.Integer, db.ForeignKey("vendors.id"), nullable=False)
    asset_id = db.Column(db.Integer, db.ForeignKey("assets.id"), nullable=False)
    portfolio_id = db.Column(db.Integer, db.ForeignKey("portfolios.id"), nullable=False)
    type = db.Column(db.String(100))
    priority = db.Column(db.String(50))
    cost = db.Column(db.Numeric(15, 2))
    capex_flag = db.Column(db.Boolean, default=False)
    status = db.Column(db.String(50))
    completion_date = db.Column(db.Date)
    photo_url = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class RiskFlag(db.Model):
    __tablename__ = "risk_flags"
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=False)
    portfolio_id = db.Column(db.Integer, db.ForeignKey("portfolios.id"), nullable=False)
    category = db.Column(db.String(100))
    severity = db.Column(db.String(50))
    description = db.Column(db.Text)
    status = db.Column(db.String(50), default="Open")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    resolved_at = db.Column(db.DateTime)
