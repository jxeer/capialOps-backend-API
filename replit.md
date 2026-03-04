# CapitalOps API - Capital + Governance Operating Layer

## Overview
CapitalOps API is a pure JSON API backend for real estate development capital and governance operations. It provides investor alignment, deal distribution, governance interpretation, vendor/maintenance visibility, and structured reporting. Built to layer on top of Coral8's execution backbone.

This is the **API-only backend** (capitalops-api). The React frontend (capitalops-web) is a separate repo/Repl that communicates with this server via `Authorization: Bearer <JWT>`.

## Architecture
- **Backend**: Python/Flask — pure JSON API (no templates, no server-rendered HTML)
- **Database**: PostgreSQL (Replit-managed via DATABASE_URL)
- **Auth**: JWT (PyJWT) — stateless Bearer token authentication
- **CORS**: Flask-CORS configured for cross-origin React frontend requests

## Project Structure
```
main.py                          # Entry point (Flask API on port 5000)
app/
  __init__.py                    # App factory, DB init, CORS, seed data
  models.py                     # SQLAlchemy models (10 entities, all with to_dict())
  auth_utils.py                 # JWT token generation, validation, decorators
  routes/
    auth.py                     # POST /api/auth/login, GET /api/auth/me
    dashboard.py                # GET /api/dashboard/
    capital.py                  # Module 1: Capital Engine (/api/capital/*)
    execution.py                # Module 2: Execution Control (/api/execution/*)
    vendor.py                   # Module 3: Asset & Vendor Control (/api/vendor/*)
```

## API Authentication
All routes (except POST /api/auth/login) require a JWT in the Authorization header:
```
Authorization: Bearer <jwt_token>
```

Token payload: `{ user_id, role, exp, iat }`
Default expiration: 24 hours (configurable via JWT_EXPIRATION_HOURS env var)

## API Route Summary
- `POST /api/auth/login`       — Authenticate, returns JWT + user profile
- `GET  /api/auth/me`          — Current user profile (requires JWT)
- `GET  /api/dashboard/`       — Portfolio overview stats
- `GET  /api/capital/`         — Capital engine overview
- `GET  /api/capital/deals`    — Deal pipeline
- `GET  /api/capital/deals/<id>` — Deal detail + allocations
- `GET  /api/capital/investors`  — Investor listing
- `POST /api/capital/investors`  — Create investor (admin)
- `POST /api/capital/allocations` — Create allocation (admin)
- `GET  /api/capital/matching`   — Deal-investor matching
- `GET  /api/execution/`        — Project overview with metrics
- `GET  /api/execution/projects/<id>` — Project detail + milestones
- `PATCH /api/execution/milestones/<id>` — Update milestone
- `GET  /api/execution/governance` — Governance event log
- `GET  /api/vendor/`           — Vendor overview + stats
- `POST /api/vendor/`           — Register vendor (admin)
- `GET  /api/vendor/work-orders` — Work order listing
- `POST /api/vendor/work-orders` — Create work order
- `PATCH /api/vendor/work-orders/<id>` — Update work order

## Data Model (10 Core Entities)
All models have a `to_dict()` method for JSON serialization.
1. **User** - JWT authentication and role-based access
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

## Roles & Permissions
- **Sponsor Admin**: Full access to all modules
- **Project Manager**: Execution module only
- **General Contractor**: Confirm milestones, limited vendor access
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
- flask, flask-sqlalchemy, flask-cors
- pyjwt
- psycopg2-binary
- werkzeug, gunicorn

## Environment Variables
- `DATABASE_URL` — PostgreSQL connection string (required)
- `SECRET_KEY` — JWT signing key (defaults to dev key)
- `JWT_EXPIRATION_HOURS` — Token expiration in hours (default: 24)
- `CORS_ORIGINS` — Comma-separated allowed origins (default: *)

## Commenting Convention
All Python source files maintain comprehensive docstrings and inline comments.
This convention must be maintained for all new code going forward.
