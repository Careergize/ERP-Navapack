# AWS migration readiness

Prepared architecture, not an AWS deployment or production authorization.

## Portable implementation

The same Django WSGI/Gunicorn image can run on ECS/Fargate, App Runner or reviewed
EC2 infrastructure behind an HTTPS load balancer. PostgreSQL uses existing environment
fields and psycopg, with verify-full TLS. No Render SDK, proprietary database extension,
provider job runner or Render-dependent business logic was introduced. Vercel frontend
can retain the same HTTPS API contract or move to a reviewed static hosting/CDN setup.

Use private RDS networking/security groups and a restricted runtime role, a separate
migration role, encrypted Secrets Manager/Parameter Store values, RDS CA bundle,
CloudWatch JSON logs/request IDs, health/readiness probes and encrypted backups/PITR.
Keep owner credentials out of tasks and builds. Review ingress forwarded-header trust;
do not expose Gunicorn directly to the public internet. Pin reviewed base-image digest,
scan dependencies/image, load-test sizing, and establish patch/rotation procedures.

## PostgreSQL export/import

1. Approve source and destination identities, data classification, PostgreSQL versions,
   maintenance window, encryption, backup/restore evidence and plan.
2. Custom-format `pg_dump --no-owner --no-privileges` with matching/newer client; hash
   and encrypt export. Test restoring into isolated RDS-compatible PostgreSQL clone.
3. Apply reviewed migrations only using the owner; compare schema/migration heads,
   append-only triggers, counts/hashes and audit evidence. Provision restricted grants
   explicitly; dumps deliberately do not recreate provider users/privileges.
4. Use RDS hostname and current RDS CA bundle with verify-full. Validate connection
   limits, transaction locks, timeouts, backup/PITR and full HTTP journey under runtime.
5. Cutover DNS/API origin/CORS only after approval; keep rollback/export and block writes
   to the retired source to avoid split-brain. No automated cutover is supplied.

The DEMO marker binds logical DB name, runtime identity, UUID, secret and expiry. An
alternate restore fails closed, as tested. A like-for-like DEMO migration can preserve
approved logical identity on an isolated replacement, with separately approved secret
handling. A new identity requires approved re-provisioning; never weaken the gate.

## Production blockers

Production must **not** inherit demo accounts, example invoices, fake stock evidence
or simulation authority. Production settings do not enable the DEMO gate. Real stock,
QC releases, dispatch and invoice authority remain gated. P4-01–P4-08, Phase 3 source/
scope/independence decisions, tax/FX rules, operational reconciliation, runtime grants,
recovery/monitoring, security review, browser acceptance and deployment authorization
must be resolved independently. A hosted client demo is not production GO.

## Remaining platform validation

Docker CLI is present locally but Linux Docker daemon was unavailable during preparation.
Linux image build/start, Render external certificate chain, managed restricted-role
provisioning, hosted smoke/load tests and real RDS restore/cutover remain manual release
gates. No paid resource or live service was modified.
