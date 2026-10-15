# Decision log — 15 October 2026

- D001 Implement only explicitly requested Phase 1 in the existing empty backend sibling.
  Preserve frontend source/demo behavior. Source: current user request.
- D002 Django 5.2 LTS on Python 3.11; exact installed dependencies in requirements/lock.txt.
  PostgreSQL only, with psycopg 3. No SQLite concurrency substitution.
- D003 Email-only login uses email request field. Frontend username adapter is proposed
  separately. No guessed receptionist fallback or public account registration.
- D004 Roles grant Django permissions through multiple server-managed memberships;
  no seeded business matrix or tenant schema. The audit's proposed mappings are unapproved.
- D005 Access 5 minutes, refresh 8 hours; rotate and blacklist refresh; serialize refresh
  and logout. Logout does not immediately revoke access or other sessions. These defaults
  need operational approval before production.
- D006 Generic server-resolved command scope permits future company/action/aggregate
  mapping; not a tenancy implementation. Retain successful idempotency results indefinitely
  pending an approved retry window and retention policy.
- D007 Append-only audit enforced through ORM and PostgreSQL mutation trigger, plus
  restricted runtime DB privileges. No claim of protection from a privileged DBA.
- D008 Production rejects debug, wildcard/implicit hosts, shared signing secrets, HTTP
  origins and database TLS weaker than verify-full. Trusted ingress and certificates
  require deployment configuration.
- D009 Throttling uses PostgreSQL fixed windows, avoiding process-local cache races;
  ingress must supply trustworthy REMOTE_ADDR and additional abuse controls.
- D010 Move the existing frontend Git metadata to the parent workspace and include both
  applications in one repository, retaining history and origin. Keep application builds
  independent and coordinate Vercel Root Directory frontend separately from local work.
  Source: user-requested monorepo migration and user-executed metadata move.

## Outstanding decisions

Obtain controlled SOP originals, role/action/object authority and maker/checker rules;
company/tenancy and warehouse scope; browser refresh storage and revocation breadth;
deployment domains/ingress/TLS/secret management; runtime DB grants and migration ownership;
audit reason/evidence privacy, retention/export and idempotency retention; MFA/SSO/recovery;
authoritative account provisioning/delegation. No production approval is implied.

Phase 2 should establish approved masters, stable source identities and import staging
with provenance/null openings, explicit authorization and safe adapters. Obtain original
reference workbooks/photos and reconcile variants/units before importing operational
stock. No stock, QC, commercial or financial posting should be added implicitly.
