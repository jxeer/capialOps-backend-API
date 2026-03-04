# CAPITALOPS API

**Capital + Governance Operating Layer — Built on Coral8**

CapitalOps API is a pure JSON API backend for real estate development capital and governance operations. It handles investor alignment, deal distribution, governance interpretation, vendor and maintenance visibility, and structured reporting.

This is the **API backend** (`capitalops-api`). The React/TypeScript frontend (`capitalops-web`) is a separate project that communicates with this API via `Authorization: Bearer <JWT>`.

---

## Architecture

```
capitalops-api (this repo)          capitalops-web (separate repo)
┌───────────────────────┐           ┌───────────────────────┐
│  Flask JSON API       │◄──JWT───►│  React + TypeScript   │
│  PostgreSQL + SQLAlchemy│          │  Vite                 │
│  JWT Auth             │           │  Bearer Token Auth    │
└───────────────────────┘           └───────────────────────┘
```

Three modules reflect how operational data flows upward into investor-grade transparency:

```
Module 3: Asset & Vendor Control (/api/vendor)
         ↓
Module 2: Execution Control (/api/execution)
         ↓
Module 1: Capital Engine (/api/capital)
```

**Operational truth → Governance interpretation → Investor transparency**

---

## Authentication

All API routes (except login) require a JWT in the Authorization header:

```
POST /api/auth/login
Content-Type: application/json

{"username": "admin", "password": "admin123"}
```

Response:
```json
{
    "token": "eyJhbGciOiJIUzI1NiIs...",
    "user": {
        "id": 1,
        "username": "admin",
        "role": "sponsor_admin",
        "role_display": "Sponsor Admin",
        ...
    }
}
```

Use the token on all subsequent requests:
```
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
```

---

## API Endpoints

### Auth
| Method | Path | Description |
|---|---|---|
| POST | `/api/auth/login` | Authenticate, receive JWT |
| GET | `/api/auth/me` | Current user profile |

### Dashboard
| Method | Path | Description |
|---|---|---|
| GET | `/api/dashboard/` | Portfolio overview stats |

### Module 1: Capital Engine
| Method | Path | Description |
|---|---|---|
| GET | `/api/capital/` | Capital overview (stats + lists) |
| GET | `/api/capital/deals` | Deal pipeline |
| GET | `/api/capital/deals/:id` | Deal detail + allocations |
| GET | `/api/capital/investors` | Investor listing |
| POST | `/api/capital/investors` | Create investor (admin) |
| POST | `/api/capital/allocations` | Create allocation (admin) |
| GET | `/api/capital/matching` | Deal-investor matching engine |

### Module 2: Execution Control
| Method | Path | Description |
|---|---|---|
| GET | `/api/execution/` | All projects with metrics |
| GET | `/api/execution/projects/:id` | Project detail + milestones |
| PATCH | `/api/execution/milestones/:id` | Update milestone |
| GET | `/api/execution/governance` | Governance event log |

### Module 3: Asset & Vendor Control
| Method | Path | Description |
|---|---|---|
| GET | `/api/vendor/` | Vendor overview + stats |
| POST | `/api/vendor/` | Register vendor (admin) |
| GET | `/api/vendor/work-orders` | Work order listing |
| POST | `/api/vendor/work-orders` | Create work order |
| PATCH | `/api/vendor/work-orders/:id` | Update work order |

---

## Role-Based Access Control

Permissions are enforced at the route level via JWT role claims:

| Role | Access |
|---|---|
| **Sponsor Admin** | Full access to all three modules |
| **Project Manager** | Execution module only |
| **General Contractor** | Confirm milestones, limited vendor access |
| **Vendor** | Own work orders only |
| **Investor (Tier 1)** | View matched deals, submit allocations |
| **Priority Investor (Tier 2)** | Early access, enhanced reporting |

---

## Data Model

10 core entities, all with `to_dict()` serialization and `portfolio_id` for multi-portfolio scaling:

| Entity | Purpose |
|---|---|
| **User** | JWT auth with role-based access |
| **Portfolio** | Top-level grouping for all assets and projects |
| **Asset** | Real estate properties |
| **Project** | Development projects linked to assets |
| **Deal** | Capital raise structures per project |
| **Investor** | Investor profiles with preferences |
| **Allocation** | Investor commitments to deals |
| **Milestone** | Project milestones with risk flags |
| **Vendor** | Contractors and service providers |
| **WorkOrder** | Vendor work assignments with CapEx/OpEx classification |
| **RiskFlag** | Category-based risk tracking |

---

## Tech Stack

- **Backend**: Python / Flask
- **ORM**: SQLAlchemy
- **Database**: PostgreSQL
- **Auth**: PyJWT (stateless Bearer tokens)
- **CORS**: Flask-CORS (for React frontend cross-origin requests)

---

## Getting Started

### Prerequisites

- Python 3.11+
- PostgreSQL database
- `DATABASE_URL` environment variable set

### Running the API

```bash
python main.py
```

The API starts on `http://0.0.0.0:5000`.

### Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `DATABASE_URL` | Yes | — | PostgreSQL connection string |
| `SECRET_KEY` | No | dev key | JWT signing key |
| `JWT_EXPIRATION_HOURS` | No | 24 | Token expiration in hours |
| `CORS_ORIGINS` | No | * | Comma-separated allowed origins |

### Demo Accounts

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
  __init__.py                 App factory, DB init, CORS, seed data
  models.py                  SQLAlchemy models (10 entities, all serializable)
  auth_utils.py              JWT generation, validation, route decorators
  routes/
    auth.py                  Login + current user
    dashboard.py             Portfolio overview
    capital.py               Module 1: Capital Engine
    execution.py             Module 2: Execution Control
    vendor.py                Module 3: Asset & Vendor Control
```
