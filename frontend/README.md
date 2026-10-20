# Navapack ERP

ERP frontend for sales, production, finished-goods inventory and raw-material workflows.

Current modules: Dashboard, Sales Orders, Job Cards, Stock, Raw Material, Recycling, Costing, Track & Trace, Masters, Quality Control, and Quotations/Proforma Invoice. All have routed pages; this does not mean complete production workflows.

## Current phase

Frontend workflows are being implemented and validated. Sales Orders, Stock and Raw Material use frontend/reference data with in-memory changes that reset on refresh. Other pages use static data or API attempts with mock fallbacks. The monorepo includes a separate [Django Phase 1 foundation](../backend/README.md); this frontend is not automatically integrated with it and production domain persistence is not verified.

## Stack and structure

React 18, TypeScript, Vite, React Router, Tailwind CSS, Axios and Lucide icons. Capacitor packages and a sync script exist, but no native Android project or Capacitor configuration is checked in.

- `src/pages/`: module screens.
- `src/components/`: layout, login and reusable UI.
- `src/context/`: authentication, sales-order and inventory state.
- `src/lib/`: API client, calculations, mock and workbook-derived reference data.
- `src/types/index.ts`: shared frontend types.
- `scripts/`: workbook extraction and finished-goods checks.
- `public/assets/`: branding.
- `docs/`: architecture, business rules, models, status and integration work.

## Development

Run commands from this directory (`frontend`). Requires Node >=20.19 and npm >=10, as declared in package.json.

```powershell
npm ci
Copy-Item .env.example .env
npm run dev
```

Vite uses port 5173. Real Django login is the default; set
`VITE_ENABLE_MOCK_LOGIN=true` in .env to explicitly enable demo login. Demo credentials
are shown on the login screen only when demo mode is enabled. Demo identities remain
local to the browser and never authenticate backend requests.

`VITE_API_BASE_URL` configures Axios. Defaults: http://localhost:8000/api/v1 in development, /api/v1 in production. Legacy values ending in /api are upgraded to /api/v1. These are client expectations, not evidence of a deployed backend. Do not put secrets in VITE variables.

```powershell
npm run build
npm run preview
node ./node_modules/typescript/bin/tsc --noEmit
node scripts/check-finished-goods.mjs
```

Build runs TypeScript then Vite. There is no lint script or lint configuration. Python/openpyxl is needed only to regenerate workbook references, not to run the app.

## Documentation

Start with [development status](docs/DEVELOPMENT_STATUS.md) and [architecture](docs/ARCHITECTURE.md).
See [business rules](docs/BUSINESS_RULES.md), [frontend models](docs/DATA_MODELS.md), [backend TODO](docs/BACKEND_TODO.md), [changelog](docs/CHANGELOG.md) and [finished-goods source interpretation](docs/finished-goods-reference.md).
Quality Control routes, provisional source templates, frontend limits and proposed Django/DRF contracts are in [quality.md](docs/quality.md). QC Inspector/Supervisor use the existing login; mock mode includes a role selector. QC state resets on refresh and the eight reference photos remain outstanding. Run `node scripts/check-quality.mjs` for focused QC checks.

Quotations, quotation-origin costing, tax/revision/conversion rules and proposed sales backend contracts are in [quotations.md](docs/quotations.md). Run `node scripts/check-quotations.mjs` for focused checks. The two referenced client documents remain outstanding; new commercial state resets on refresh.

Agent guidance is in [AGENTS.md](AGENTS.md).

Integrated stock/financial/trace/sales/quotation/QC behavior and limitations are in the existing [workflow report](docs/sales-fulfillment.md#integrated-operations-update--15-october-2026). Run `node scripts/check-integrated-operations.mjs` alongside existing regressions. No domain backend integration, public customer portal, email delivery or background scheduler is implemented.

## Monorepo deployment

The Git root is the parent directory; run frontend npm commands here. Vercel must use
Root Directory `frontend`, install `npm ci`, build `npm run build`, output `dist` after
the layout reaches its deployed branch. Keep vercel.json here and preserve existing
environment scopes/domains. Coordinate the setting change with the deployed branch;
see [migration and cutover](../docs/MONOREPO_MIGRATION.md). No Vercel settings were
changed by the local restructure, and the backend remains independently deployable.

Finance demo: run `npm run dev`, open `/finance/login`, and use
`finance@navapack.com` / `test@123` when mock login is enabled. This opens the existing
Accounts Finance Dashboard; operations login also offers Accounts / Finance. Demo mode
requires `VITE_ENABLE_MOCK_LOGIN=true` in development and production. No backend account
is created. Run `node scripts/check-led-finance.mjs` for confirmed LED MAX/snapshot/VAT
and demo-auth regressions. [Rule, pending percentage base and demo boundaries](docs/sales-fulfillment.md#client-confirmed-led-max-and-finance-demo--15-october-2026).
