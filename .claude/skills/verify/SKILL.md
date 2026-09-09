---
name: verify
description: Build, launch, and drive this app end to end to verify a change at its real surface (browser for Vue views, HTTP for FastAPI routes). Use before committing any change to client/ or server/.
---

# Verify: Factory Inventory Management System

## Launch

Backend (FastAPI, port 8001):
```bash
cd server && uv venv && uv sync          # first time only
cd server && uv run python main.py       # foreground; Ctrl-C to stop
```
Data is in-memory: restart the backend to reset submitted orders and pick up route changes.

Frontend (Vite, port 3000):
```bash
cd client && npm install --ignore-scripts   # first time only
cd client && npm run dev
```
Vite hot-reloads `.vue` edits; no restart needed. Note that HMR invalidates browser element refs, so re-find elements after saving a file.

## Surfaces

- API: `curl http://localhost:8001/api/...`; Swagger at `http://localhost:8001/docs` lists every route.
- UI: `http://localhost:3000` (routes: `/`, `/inventory`, `/orders`, `/spending`, `/demand`, `/restocking`, `/reports`). Drive with the Chrome browser tools; `find` gives element refs, `form_input` sets range sliders and selects directly (more reliable than clicking a native `<select>`).

## Flows worth driving

- Global FilterBar: changing Location / Category / Status / Time Period re-fetches every view. Check the affected table and stat cards change.
- Restocking: slider at 0 shows the empty state and a disabled Place Order; 10,000 skips WDG-001; 25,000 buys all eight items. Place Order shows a banner with the RST order number and lead time; `/orders` then shows it under "Submitted Orders" with the Location filter applied.
- Language switcher (header): flip to 日本語 and check every new string localizes and currency converts (JPY is USD x150 via `utils/currency.js`).

## API probes that should hold

- `?budget=abc` and `?budget=-5` on recommendations -> 422.
- POST `/api/restocking/orders` with missing field / string budget / fractional quantity -> 422; negative quantity, unknown SKU, empty items, total over budget -> 400.
- Wrong method -> 405.
