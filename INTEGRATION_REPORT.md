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

## Current Backend Coverage

The backend now provides JWT login, refresh-token renewal, first-admin bootstrap, users, API credentials, notifications, logs, audit events, strategies, risk settings, market data, signals, backtests, AI analyses, AI model metadata, paper orders, positions, and portfolio endpoints.

The platform still uses a static role-to-permission map rather than database-backed dynamic RBAC. Super-admin, role CRUD, permission CRUD, broker/account management, and system settings management are still future modules.

## Broken Routes Fixed

- Removed unsupported sidebar menu promises for Markets, Forex, Equities, Watchlists, and standalone Risk pages.
- Top-level sidebar items now navigate to valid routes instead of only expanding submenus.
- Settings footer control now routes to `#/overview/settings`.
- `#/overview/settings` opens the inline strategy controls panel.

## Unimplemented Pages

- Dedicated CRUD pages for symbols and AI analyses are not implemented.
- Strategy, risk, users, API keys, backtests, AI models, logs, notifications, orders, and positions pages exist, but several are still operationally thin.
- Trading and Activity are functional module pages, but they do not have separate subpage components for every hash route.
- Login/register exists; logout is client-side token removal.

## Validation Issues

- Strategy and risk forms submit to backend validation, but field-level backend error display is not yet normalized from FastAPI `422` responses.
- Create/delete endpoints are partial: symbols can be created; strategies can be created, toggled, and deleted; risk settings can be updated but not created/deleted.
- Pagination is client-side for dashboard tables; backend list endpoints mostly expose `limit`, not full `page/sort/search` contracts.

## Recommended Fixes

- Add database-backed roles and permissions before expanding RBAC beyond the static role map.
- Add backend pagination, search, sorting, and export endpoints for orders, positions, signals, audit events, and analyses.
- Add CRUD endpoints where production workflows require them, especially strategies, risk policies, symbols, and AI analysis records.
- Split route-specific pages when distinct UX is needed for orders, positions, audit log, signals, and settings.
