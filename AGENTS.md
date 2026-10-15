# Navapack ERP monorepo guidance

This directory is the Git repository root. Read README.md and relevant application
documentation before changes. frontend/AGENTS.md applies to frontend work;
backend/AGENTS.md applies to backend work.

- Preserve existing source, uncommitted work and independently deployable applications.
- Run frontend npm commands from frontend; run Django commands from backend.
- Do not introduce a root package manager, combined build or automatic API integration
  without an explicit task. Keep frontend demos and backend authorization separate.
- Never stage .env files, credentials, .venv, .local/PostgreSQL data, node_modules,
  build output, logs or .migration-backup. Environment examples must contain placeholders.
- Existing backend Phase 1 is authorized infrastructure; future domain work requires
  its own scope. Planning documents do not establish approved SOP or authority rules.
- For frontend changes run typecheck/build and relevant scripts/check-*.mjs. For backend
  changes run Django checks, migration drift checks and relevant PostgreSQL tests.
- For repository structure changes verify source preservation, ignore rules, history,
  remote identity and each application's independent checks. Document exact results.
- Preserve history. No forced pushes, history rewriting, nested repositories or destructive
  Git operations. Deployment settings and pushes require the user's authorization.

Vercel uses frontend as Root Directory after the production branch migration. See
docs/MONOREPO_MIGRATION.md; coordinate cutover before triggering production builds.
