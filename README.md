# CAPITALOPS

**Capital + Governance Operating Layer — Built on Coral8**

CapitalOps is a capital and governance operating layer designed for real estate development firms. It handles investor alignment, deal distribution, governance interpretation, vendor and maintenance visibility, and structured reporting — all layered on top of Coral8's execution backbone.

---

## System Architecture

CapitalOps is organized into three modules that reflect how operational data flows upward into investor-grade transparency:

```
Module 3: Asset & Vendor Control
         ↓
Module 2: Execution Control
         ↓
Module 1: Capital Engine
```

**Operational truth → Governance interpretation → Investor transparency**

### Module 1: Capital Engine

Curated deal distribution and investor transparency.

- Investor profile management
- Deal tagging and pipeline tracking
- Rule-based deal-investor matching
- Sponsor-approved distribution
- Allocation tracking (soft commit / hard commit)
- Investor transparency dashboard

### Module 2: Execution Control

Translates raw project data into governance-level clarity.

- Milestone rollups and progress tracking
- Budget vs. actual summary with variance reporting
- Risk flag triggers
- Delay explanations
- Governance event log

### Module 3: Asset & Vendor Control

Operational discipline and asset protection.

- Vendor registration and management
- COI (Certificate of Insurance) status tracking
- Work order creation and tracking
- CapEx vs. OpEx classification
- SLA tagging
- Performance scoring

---

## Data Model

The system is built on 10 core entities, all linked to a top-level `Portfolio` for future multi-portfolio scaling:

| Entity | Purpose |
|---|---|
| **Portfolio** | Top-level grouping for all assets and projects |
| **Asset** | Real estate properties (location, type, square footage) |
| **Project** | Development projects linked to assets (budget, phase, timeline) |
| **Deal** | Capital raise structures per project |
| **Investor** | Investor profiles with preferences and accreditation |
| **Allocation** | Investor commitments to specific deals |
| **Milestone** | Project milestones with risk flags and delay tracking |
| **Vendor** | Contractors and service providers per asset |
| **WorkOrder** | Vendor work assignments with cost and priority |
| **RiskFlag** | Category-based risk tracking per project |

---

## Role-Based Access Control

Permissions are enforced at both the route and API level:

| Role | Access |
|---|---|
| **Sponsor Admin** | Full access to all three modules |
| **Project Manager** | Execution module — milestones, delays, budgets |
| **General Contractor** | Confirm milestone completion, limited vendor access |
| **Vendor** | Own work orders only |
| **Investor (Tier 1)** | View matched deals, submit allocation requests |
| **Priority Investor (Tier 2)** | Early access, enhanced reporting |

---

## Tech Stack

- **Backend**: Python / Flask
- **ORM**: SQLAlchemy
- **Database**: PostgreSQL
- **Auth**: Flask-Login with session-based authentication
- **Security**: CSRF protection (Flask-WTF), role-enforced API endpoints
- **Frontend**: Server-rendered Jinja2 templates, custom dark-theme CSS

---

## Getting Started

### Prerequisites

- Python 3.11+
- PostgreSQL database
- `DATABASE_URL` environment variable set

### Running the Application

```bash
python main.py
```

The application starts on `http://0.0.0.0:5000`.

### Demo Accounts

The application seeds demo data automatically in development:

| Role | Username | Password |
|---|---|---|
| Sponsor Admin | `admin` | `admin123` |
| Project Manager | `pm` | `pm123` |
| General Contractor | `gc` | `gc123` |

---

## Project Structure

```
main.py                       Entry point
app/
  __init__.py                 App factory, database init, seed data
  models.py                  SQLAlchemy models (10 entities)
  routes/
    auth.py                  Login / logout
    dashboard.py             Portfolio dashboard
    capital.py               Module 1: Capital Engine
    execution.py             Module 2: Execution Control
    vendor.py                Module 3: Asset & Vendor Control
    api.py                   JSON API endpoints (role-enforced)
  templates/
    base.html                Layout with sidebar navigation
    auth/                    Login page
    dashboard/               Portfolio overview
    capital/                 Deals, investors, matching, allocations
    execution/               Projects, milestones, governance log
    vendor/                  Vendors, work orders
  static/
    css/style.css            Dark theme stylesheet
```

---

## What This System Does Not Do

Per the operational blueprint, CapitalOps intentionally avoids:

- Full accounting engine
- Full property management system
- AI recommendation engine
- Marketplace functionality
- Public deal directory
- Tokenization
- CRM replacement

Scope discipline is survival.

---

## MVP Success Metrics

The system is working when:

- Investor conversations are shorter
- Allocation happens faster
- PM explanations are structured
- Vendor discipline improves
- No milestone drifts silently
- You stop chasing capital and start selecting it
