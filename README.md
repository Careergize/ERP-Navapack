# Navapack ERP

ERP frontend for sales, production, finished-goods inventory and raw-material workflows.

Current modules: Dashboard, Sales Orders, Job Cards, Stock, Raw Material, Recycling, Costing, Track & Trace, Masters, Quality Control, and Quotations/Proforma Invoice. All have routed pages; this does not mean complete production workflows.

## Current phase

Frontend workflows are being implemented and validated. Sales Orders, Stock and Raw Material use frontend/reference data with in-memory changes that reset on refresh. Other pages use static data or API attempts with mock fallbacks. No backend implementation or database migrations are present in this repository; production persistence is not verified.

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

Vite uses port 5173. Set `VITE_ENABLE_MOCK_LOGIN=true` in .env for frontend testing; the example sets it to false. Demo credentials are shown on the login screen. Without an explicit value, development defaults to mock login. Production mock login also becomes enabled if explicitly set to true.

`VITE_API_BASE_URL` configures Axios. Defaults: http://localhost:8000/api in development, /api in production. These are client expectations, not evidence of a deployed backend. Do not put secrets in VITE variables.

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

Integrated stock/financial/trace/sales/quotation/QC behavior and limitations are in the existing [workflow report](docs/sales-fulfillment.md#integrated-operations-update--15-october-2026). Run `node scripts/check-integrated-operations.mjs` alongside existing regressions. No backend/public customer portal/email delivery/background scheduler is implemented.

Finance demo: run `npm run dev`, open `/finance/login`, and use `finance@navapack.com` / `test@123` when mock login is enabled. This opens the existing Accounts Finance Dashboard; operations login also offers Accounts / Finance. Development defaults to mock unless explicitly disabled; production demo requires `VITE_ENABLE_MOCK_LOGIN=true` at build time. No session restoration or backend account is created. Run `node scripts/check-led-finance.mjs` for confirmed LED MAX/snapshot/VAT and demo-auth regressions. [Rule, pending percentage base and demo boundaries](docs/sales-fulfillment.md#client-confirmed-led-max-and-finance-demo--15-october-2026).
