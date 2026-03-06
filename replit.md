# CapitalOps - Capital + Governance Operating Layer

## Overview
CapitalOps is a full-stack application for real estate development capital and governance operations. It provides investor alignment, deal distribution, governance interpretation, vendor/maintenance visibility, and structured reporting.

The project runs as two processes in a single Repl:
- **capitalops-api** (Flask JSON API on port 3001)
- **capitalops-web** (React + TypeScript frontend on port 5000 via Vite)

Vite proxies all `/api` requests to the Flask backend automatically.

## Architecture
- **Frontend**: React + TypeScript + Vite (port 5000, webview)
- **Backend**: Python/Flask — pure JSON API (port 3001, console)
- **Database**: PostgreSQL (Replit-managed via DATABASE_URL)
- **Auth**: flask-jwt-extended — stateless Bearer token authentication (1h access tokens)
- **CORS**: Flask-CORS configured for cross-origin requests
- **API Versioning**: Authenticated routes under `/api/v1/`; GUI compatibility layer at `/api/`

## Project Structure
```
main.py                          # Flask API entry point (port 3001)
app/
  __init__.py                    # App factory, DB init, CORS, JWT, seed data
  models.py                     # SQLAlchemy models (11 entities, all with to_dict())
  auth_utils.py                 # get_current_user(), role_required() (flask-jwt-extended)
  routes/
    auth.py                     # POST /api/v1/auth/login, GET /api/v1/auth/me
    dashboard.py                # GET /api/v1/dashboard/
    capital.py                  # Module 1: Capital Engine (/api/v1/capital/*)
    execution.py                # Module 2: Execution Control (/api/v1/execution/*)
    vendor.py                   # Module 3: Asset & Vendor Control (/api/v1/vendor/*)
    compat.py                   # GUI Compatibility Layer (/api/*) — camelCase, string IDs, no auth
client/
  vite.config.ts                # Vite config (port 5000, proxy /api → localhost:3001)
  index.html                    # HTML entry point
  .env                          # VITE_API_BASE_URL=/api/v1
  src/
    main.tsx                    # React entry point
    App.tsx                     # Router: /login, /dashboard, catch-all → /dashboard
    index.css                   # Global styles (dark theme matching GUI)
    vite-env.d.ts               # Vite env type declarations
    lib/
      api.ts                    # API client (token storage, auth header, typed requests)
    components/
      ProtectedRoute.tsx        # Redirects to /login if no token in localStorage
    pages/
      LoginPage.tsx             # Username/password login form
      DashboardPage.tsx         # Project table with metrics (calls /api/v1/execution/)
```

## Workflows
- **Start application**: `npx vite --config client/vite.config.ts` (port 5000, webview)
- **API Server**: `python main.py` (port 3001, console)

## Two API Layers

### Authenticated API (`/api/v1/`) — snake_case, integer IDs, JWT required
Used by the local React frontend and any direct API consumers.
All routes require `Authorization: Bearer <jwt>` header.

### GUI Compatibility API (`/api/`) — camelCase, string IDs, no auth
Used by the external CapitalOps GUI Repl (Express proxy → Flask).
The GUI's Express server sets `BACKEND_URL` and proxies requests directly.
Returns flat arrays with camelCase keys and string-typed IDs matching the
frontend's Zod schemas.

**Compat route file**: `app/routes/compat.py`

## Frontend Routes
- `/login` — Login page (username/password form)
- `/dashboard` — Protected project dashboard (requires JWT)
- `/*` — Redirects to `/dashboard`

## API Authentication
All `/api/v1/` routes (except POST /api/v1/auth/login) require a JWT in the Authorization header:
```
Authorization: Bearer <jwt_token>
```

Token identity: `str(user.id)` (stringified integer — PyJWT 2.x requires string subjects)
Additional claims: `{ role: "sponsor_admin" }`
Default expiration: 1 hour (configurable via JWT_ACCESS_TOKEN_EXPIRES_MINUTES env var)

## API Route Summary

### v1 Authenticated Routes (snake_case)
- `POST /api/v1/auth/login`       — Authenticate, returns `{ accessToken, user }`
- `GET  /api/v1/auth/me`          — Current user profile (requires JWT)
- `GET  /api/v1/dashboard/`       — Portfolio overview stats
- `GET  /api/v1/capital/`         — Capital engine overview
- `GET  /api/v1/capital/deals`    — Deal pipeline
- `GET  /api/v1/capital/deals/<id>` — Deal detail + allocations
- `GET  /api/v1/capital/investors`  — Investor listing
- `POST /api/v1/capital/investors`  — Create investor (admin)
- `POST /api/v1/capital/allocations` — Create allocation (admin)
- `GET  /api/v1/capital/matching`   — Deal-investor matching
- `GET  /api/v1/execution/`        — Project overview with metrics
- `GET  /api/v1/execution/projects/<id>` — Project detail + milestones
- `PATCH /api/v1/execution/milestones/<id>` — Update milestone
- `GET  /api/v1/execution/governance` — Governance event log
- `GET  /api/v1/vendor/`           — Vendor overview + stats
- `POST /api/v1/vendor/`           — Register vendor (admin)
- `GET  /api/v1/vendor/work-orders` — Work order listing
- `POST /api/v1/vendor/work-orders` — Create work order
- `PATCH /api/v1/vendor/work-orders/<id>` — Update work order

### GUI Compatibility Routes (camelCase, no auth)
- `GET  /api/backend-status`     — Backend connectivity info
- `GET  /api/dashboard/stats`    — Dashboard stat cards
- `GET  /api/portfolios`         — All portfolios
- `GET  /api/assets`             — All assets
- `GET  /api/assets/<id>`        — Single asset
- `POST /api/assets`             — Create asset
- `GET  /api/projects`           — All projects
- `GET  /api/projects/<id>`      — Single project
- `POST /api/projects`           — Create project
- `GET  /api/deals`              — All deals
- `GET  /api/deals/<id>`         — Single deal
- `POST /api/deals`              — Create deal
- `GET  /api/investors`          — All investors
- `GET  /api/investors/<id>`     — Single investor
- `POST /api/investors`          — Create investor
- `GET  /api/allocations`        — All allocations
- `POST /api/allocations`        — Create allocation
- `GET  /api/milestones`         — All milestones
- `GET  /api/milestones/project/<id>` — Milestones by project
- `POST /api/milestones`         — Create milestone
- `GET  /api/vendors`            — All vendors
- `GET  /api/vendors/<id>`       — Single vendor
- `POST /api/vendors`            — Create vendor
- `GET  /api/work-orders`        — All work orders
- `GET  /api/work-orders/vendor/<id>` — Work orders by vendor
- `POST /api/work-orders`        — Create work order
- `GET  /api/risk-flags`         — All risk flags
- `GET  /api/risk-flags/project/<id>` — Risk flags by project

## Data Model (11 Core Entities)
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
### Backend (Python)
- flask, flask-sqlalchemy, flask-cors, flask-jwt-extended
- psycopg2-binary, werkzeug, gunicorn

### Frontend (Node.js)
- react, react-dom, react-router-dom
- vite, @vitejs/plugin-react, typescript

## Environment Variables
- `DATABASE_URL` — PostgreSQL connection string (required)
- `JWT_SECRET_KEY` — JWT signing key (falls back to SECRET_KEY, then dev default)
- `JWT_ACCESS_TOKEN_EXPIRES_MINUTES` — Token expiration in minutes (default: 60)
- `FRONTEND_ORIGIN` — Comma-separated allowed origins for CORS (default: `http://localhost:5173,http://localhost:3000`)
- `FLASK_ENV` — Set to `development` to enable auto-seeding; `production` to block it
- `VITE_API_BASE_URL` — API base URL for frontend (default: `/api/v1`)

## Dev Seed
- Auto-seeds on startup when `FLASK_ENV=development` or inside a Replit dev workspace
- Never seeds when `FLASK_ENV=production` (hard safety guard)
- Manual seed via Flask CLI: `FLASK_APP=main.py flask seed`
- Idempotent: skips if users already exist in the database
- Seeds: 3 users, 1 portfolio, 3 assets, 3 projects, 3 deals, 5 investors, 7 allocations, 8 milestones, 5 vendors, 4 work orders, 4 risk flags

## Deployment
- **Target**: Autoscale
- **Command**: `gunicorn --bind=0.0.0.0:5000 --reuse-port main:app`
- **Health check**: `GET /` returns `{"status": "ok", "service": "capitalops-api"}`
- **Production env**: `FLASK_ENV=production` (blocks seeding), `JWT_SECRET_KEY` (random 32-byte hex)

## GUI Repl Integration
The external GUI Repl (capitalOps-frontend-GUI) connects by setting:
- `BACKEND_URL` env var on the GUI Repl pointing to this API's deployed URL
- The GUI's Express server proxies all `/api/*` requests to the backend
- The compat layer (`/api/`) returns data in the exact format the GUI expects

## Commenting Convention
All Python source files maintain comprehensive docstrings and inline comments.
This convention must be maintained for all new code going forward.
