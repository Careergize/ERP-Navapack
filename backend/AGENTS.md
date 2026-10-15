# Backend agent guidance

Phase 1 contains foundation infrastructure only. Read README.md, docs/ARCHITECTURE.md,
docs/DEVELOPMENT_STATUS.md and docs/DECISION_LOG.md before changes. The eight source
planning documents are in ../frontend/docs/backend-planning/; they are proposals,
not approved SOP or role authority. The user's task takes precedence over the
frontend's older default prohibition on backend work.

- Preserve the sibling frontend and its demo functionality. Do not integrate it implicitly.
- Do not add stock, sales, production, QC, costing, billing or integration models in this phase.
- Enforce active identity, server capabilities and explicit object scope. Never trust role labels or actor IDs from clients.
- Keep audit actor identities and independence checks in transactional services, including for superusers.
- Use PostgreSQL for migrations and concurrency tests. No SQLite fallback or concurrency pass claims.
- Add migrations for schema changes; never edit an applied migration.
- Secrets, .env, virtual environments, local PostgreSQL data and logs must stay ignored.
- Run `python manage.py check`, `python manage.py makemigrations --check --dry-run`,
  and `python manage.py test tests --settings=config.settings.test` from backend.
- Frontend regressions: typecheck, build and scripts/check-*.mjs from frontend.
- Document actual verification, limitations and pending policy decisions. No production/SOP certification claims.
