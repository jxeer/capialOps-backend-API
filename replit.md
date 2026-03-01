# CapitalOps - Capital + Governance Operating Layer

## Overview
CapitalOps is a capital and governance operating layer designed for real estate development. It provides investor alignment, deal distribution, governance interpretation, vendor/maintenance visibility, and structured reporting. Built to layer on top of Coral8's execution backbone.

## Architecture
- **Backend**: Python/Flask with SQLAlchemy ORM
- **Database**: PostgreSQL (Replit-managed via DATABASE_URL)
- **Auth**: Flask-Login with role-based access control
- **Frontend**: Server-rendered Jinja2 templates with custom CSS (dark theme)

## Project Structure
```
main.py                          # Entry point (Flask app on port 5000)
app/
  __init__.py                    # App factory, DB init, seed data
  models.py                     # SQLAlchemy models (10 entities)
  routes/
    auth.py                     # Login/logout
    dashboard.py                # Portfolio dashboard
    capital.py                  # Module 1: Capital Engine
    execution.py                # Module 2: Execution Control
    vendor.py                   # Module 3: Asset & Vendor Control
    api.py                      # JSON API endpoints
  templates/
    base.html                   # Layout with sidebar navigation
    auth/login.html
    dashboard/index.html
    capital/{index,deals,deal_detail,investors,add_investor,matching}.html
    execution/{index,project_detail,governance}.html
    vendor/{index,add_vendor,create_work_order}.html
  static/css/style.css          # Full dark theme CSS
```

## Data Model (10 Core Entities)
1. **User** - Authentication and role-based access
2. **Portfolio** - Top-level grouping (PortfolioID on all entities for future scale)
3. **Asset** - Real estate properties
4. **Project** - Development projects linked to assets
5. **Deal** - Capital raise structures per project
6. **Investor** - Investor profiles with preferences
7. **Allocation** - Investor commitments to deals
8. **Milestone** - Project milestones with risk flags
9. **Vendor** - Contractors and service providers
10. **WorkOrder** - Vendor work assignments
11. **RiskFlag** - Category-based risk tracking

## Three Modules
- **Module 1 (Capital Engine)**: Investor profiles, deal tagging, rule-based matching, allocation tracking, transparency dashboard
- **Module 2 (Execution Control)**: Milestone rollups, budget vs actual, risk flags, delay explanations, governance log
- **Module 3 (Asset & Vendor Control)**: Vendor management, work orders, COI tracking, CapEx/OpEx classification, SLA tagging

## Roles & Permissions
- **Sponsor Admin**: Full access to all modules
- **Project Manager**: Execution module only (milestones, delays)
- **General Contractor**: Confirm milestones, submit change orders, vendor-limited
- **Vendor**: Own work orders only
- **Investor Tier 1**: View matched deals, allocation requests
- **Investor Tier 2**: Priority access, enhanced reporting

## Demo Accounts
- admin / admin123 (Sponsor Admin)
- pm / pm123 (Project Manager)
- gc / gc123 (General Contractor)

## Data Flow
Module 3 (Vendor) → Module 2 (Execution) → Module 1 (Capital)
Operational truth → Governance interpretation → Investor transparency

## Key Dependencies
- flask, flask-sqlalchemy, flask-login
- psycopg2-binary
- werkzeug
