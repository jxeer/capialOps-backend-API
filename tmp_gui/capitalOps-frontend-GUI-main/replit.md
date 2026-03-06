# CapitalOps - Capital Infrastructure Platform

## Overview
CapitalOps is a capital + governance operating layer for real estate development, built on Coral8. It provides three core modules:
1. **Capital Engine** - Investor alignment, deal distribution, allocation tracking
2. **Execution Control** - Project milestones, budget tracking, risk flags
3. **Asset & Vendor Control** - Vendor management, work orders, asset health

## Architecture
- **Frontend**: React + TypeScript with Vite, TanStack Query, wouter routing, shadcn/ui components
- **Backend Proxy**: Express.js proxies API requests to external backend at `BACKEND_URL` env var (https://capital-ops.replit.app). Falls back to local in-memory seed data when the backend route returns a non-200 response.
- **Local Storage**: In-memory storage with realistic seed data used as fallback
- **Design**: Dark mode by default, Inter font, blue primary theme (217 91% 35%)

## Backend Connection
- `BACKEND_URL` environment variable points to `https://capital-ops.replit.app`
- Every `/api/*` request first tries the external backend
- If the backend returns a non-200 response, falls back to local in-memory data
- Dashboard shows connection status indicator (Backend Connected / Local Mode)
- `/api/backend-status` endpoint reports connection state

## Data Model (10 Core Entities)
- Portfolio, Asset, Project, Deal, Investor, Allocation, Milestone, Vendor, WorkOrder, RiskFlag

## File Structure
- `shared/schema.ts` - Zod schemas and TypeScript types for all entities
- `server/storage.ts` - In-memory storage with seed data (fallback)
- `server/routes.ts` - API routes with proxy-to-backend logic + local fallback
- `client/src/App.tsx` - Main app with sidebar layout and routing
- `client/src/components/` - Shared components (app-sidebar, stat-card, page-header, theme-provider)
- `client/src/pages/` - All page components (dashboard, assets, projects, deals, investors, allocations, milestones, risk-flags, vendors, work-orders)
- `client/src/lib/formatters.ts` - Currency, date, number formatting utilities

## Pages
- `/` - Dashboard (portfolio overview with KPIs + backend connection status)
- `/deals` - Deal pipeline and capital distribution
- `/investors` - Investor profiles and alignment
- `/allocations` - Commitment tracking
- `/projects` - Project execution tracking
- `/milestones` - Milestone timeline per project
- `/risk-flags` - Risk monitoring
- `/assets` - Portfolio assets
- `/vendors` - Vendor management
- `/work-orders` - Work order tracking

## Running
`npm run dev` starts Express backend + Vite frontend on port 5000
