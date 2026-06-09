# Frontend/Backend Integration Report

## Connected Modules

- Dashboard / Overview: symbols, candles, signals, strategies, risk settings, backtests, AI provider, AI analyses, paper orders, positions, portfolio summary, and audit events.
- Trading: paper orders, paper positions, portfolio summary, equity curve, cancel order, and close position.
- Activity: audit event timeline with severity and entity filters.
- Navigation: sidebar menu, submenu visibility, current user identity, and permissions are now loaded from backend endpoints.
- Navbar: current user and notification dropdown are backed by `/api/me` and `/api/audit/events`.

## Valid Frontend Routes

- `#/overview`
- `#/overview/portfolio`
- `#/overview/signals`
- `#/overview/settings`
- `#/trading`
- `#/trading/orders`
- `#/trading/positions`
- `#/activity`
- `#/activity/audit`

## Missing Backend Endpoints

The requested logistics/admin modules are not present in this Trading AI backend:

- Authentication sessions and logout
- Users, roles, and permissions CRUD
- Branches, provinces, districts, and stations
- Shipments, dispatch, and tracking
- Customers
- Support tickets
- Reports
- Notifications CRUD/read-state
- General settings management

The backend currently provides API-key protection and a static operator permission model through `/api/me` and `/api/navigation`.

## Broken Routes Fixed

- Removed unsupported sidebar menu promises for Markets, Forex, Equities, Watchlists, and standalone Risk pages.
- Top-level sidebar items now navigate to valid routes instead of only expanding submenus.
- Settings footer control now routes to `#/overview/settings`.
- `#/overview/settings` opens the inline strategy controls panel.

## Unimplemented Pages

- Dedicated CRUD pages for symbols, strategies, risk settings, AI analyses, and backtests are not implemented.
- Trading and Activity are functional module pages, but they do not have separate subpage components for each hash route.
- No login/logout pages exist because the backend has no session authentication endpoints.

## Validation Issues

- Strategy and risk forms submit to backend validation, but field-level backend error display is not yet normalized from FastAPI `422` responses.
- Create/delete endpoints are partial: symbols can be created; strategies and risk settings can be updated; delete endpoints are not provided by the backend.
- Pagination is client-side for dashboard tables; backend list endpoints mostly expose `limit`, not full `page/sort/search` contracts.

## Recommended Fixes

- Add real authentication and role/permission tables before expanding RBAC beyond the static operator profile.
- Add backend pagination, search, sorting, and export endpoints for orders, positions, signals, audit events, and analyses.
- Add CRUD endpoints where production workflows require them, especially strategies, risk policies, symbols, and AI analysis records.
- Add a notifications table/API if read/unread notification workflows are required.
- Split route-specific pages when distinct UX is needed for orders, positions, audit log, signals, and settings.
