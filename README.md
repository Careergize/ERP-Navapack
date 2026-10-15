# Navapack ERP

One Git repository with independently built and deployed frontend and backend applications.

```text
Navapack-ERP/              Git root
  frontend/               React, TypeScript and Vite application
  backend/                Django/DRF Phase 1 foundation
  docs/                   Repository and deployment guidance
  AGENTS.md               Repository-wide agent guidance
```

## Frontend

Requires Node >=20.19 and npm >=10. Run from frontend, using its own package-lock.json:

```powershell
Set-Location frontend
npm ci
Copy-Item .env.example .env  # Fresh setup only; preserve an existing .env.
npm run dev
```

Build with `npm run build`; output is frontend/dist. Vite development uses port 5173.
See [frontend setup and demo boundaries](frontend/README.md).

## Backend

Requires Python 3.11+ and PostgreSQL 16+. Run from backend:

```powershell
Set-Location backend
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements/lock.txt
Copy-Item .env.example .env  # Fresh setup only; preserve an existing .env.
# Configure independent secrets and PostgreSQL credentials before continuing.
.venv/Scripts/python manage.py migrate
.venv/Scripts/python manage.py runserver 127.0.0.1:8000
```

See [backend setup](backend/README.md) for PostgreSQL provisioning, tests, production
settings and deployment. Phase 1 provides authentication and technical foundation;
stock, sales, production, QC and financial posting remain unimplemented. Frontend demo
and session workflows are preserved and are not automatically connected to the backend.

## Independent deployment

- Frontend: Vercel project Root Directory **frontend**, install `npm ci`, build
  `npm run build`, output `dist`; keep frontend/vercel.json beside the app.
- Backend: separate Python deployment using backend as its working directory, its own
  environment and PostgreSQL database; follow backend/README.md.

Coordinate the Vercel Root Directory cutover when the new layout reaches the deployed
branch. No remote settings or deployments are changed by the local migration.
[Migration and deployment instructions](docs/MONOREPO_MIGRATION.md).

## Repository conventions

Run Git commands from this directory or either application; both resolve to this root.
Run npm and Django commands from their respective application directories. There is no
root npm workspace, package.json or combined build. The pre-existing empty root npm
lockfile is retained locally and ignored; frontend/package-lock.json is authoritative.

Keep .env, virtual environments, local PostgreSQL data, dependencies, builds, caches and
history backups out of Git. Commit only sanitized environment examples. Each application
retains its own .gitignore in addition to repository-wide rules.

The existing frontend history and origin remote are preserved through an ordinary
layout commit; older commits retain their original root-relative paths. The eight
[backend-planning documents](frontend/docs/backend-planning/BACKEND_READINESS_REPORT.md)
remain historical proposals, not SOP approval or proof of production persistence.
