# DEMO environment variables

Use secret stores. Never commit `.env`, passwords, dump files or execution secrets.
No actual hosted identities or credentials are supplied by this template.

## Backend runtime — Render environment or AWS secret injection

- `DJANGO_SETTINGS_MODULE=config.settings.demo`
- `APP_ENV=DEMO`
- `DJANGO_DEBUG=false`
- `DJANGO_ALLOWED_HOSTS=<approved-exact-demo-api-host>` (no scheme/path/wildcard)
- `DJANGO_SECRET_KEY=<independent-random-secret-at-least-50-characters>`
- `JWT_SIGNING_KEY=<different-random-secret-at-least-50-characters>`
- `DEMO_EXECUTION_SECRET=<third-independent-64-character-random-secret>`
- `DEMO_INSTANCE_ID=<approved-UUID>`
- `DEMO_DATABASE_NAME=navapack_demo_<approved_unique_suffix>`
- `POSTGRES_DB=<exact-same-DEMO-database-name>`
- `POSTGRES_USER=<dedicated-restricted-demo-runtime-role>`
- `POSTGRES_PASSWORD=<runtime-secret>`
- `POSTGRES_HOST=<certificate-verified-external-Render-PostgreSQL-host>`
- `POSTGRES_PORT=5432`
- `POSTGRES_SSLMODE=verify-full`
- `PGSSLROOTCERT=/etc/ssl/certs/ca-certificates.crt` in prepared Linux image.
  Validate the issuer against that trust store before release; mount a reviewed CA
  bundle and change this path when needed. RDS uses the reviewed RDS CA bundle.
- `CORS_ALLOWED_ORIGINS=https://<approved-demo-frontend-host>`
- `CSRF_TRUSTED_ORIGINS=https://<approved-demo-frontend-host>`
- `TRUST_PROXY_HTTPS=true` only behind reviewed ingress sanitizing forwarding headers.
- `PORT` supplied by Render; local default 8000.
- `WEB_CONCURRENCY=2`, `GUNICORN_THREADS=2` initially; load/memory-test before resizing.
- `FORWARDED_ALLOW_IPS=127.0.0.1,::1` default. Do not set `*` without validating ingress
  isolation; application proxy trust must not expose the service directly to clients.
- `LOG_LEVEL=INFO`.

Existing `POSTGRES_*` fields are used directly; no hardcoded credentials or provider
URL parsing is needed. Do not give the app the managed migration-owner connection.
Never set SYNTHETIC_LEDGER_* flags in a hosted environment: these are not environment
feature switches and the original test gate remains unchanged.

Generate the three independent secrets with `python -c "import secrets; print(secrets.token_hex(32))"`
three separate times in a protected operator terminal. Generate UUID with Python's
uuid4. Do not paste secrets into tickets, logs or this document.

## Owner/operator environment

Use the same approved DEMO name/instance/secret/HTTPS settings, but temporary owner
`POSTGRES_USER`/password only for approved migration, stamp, grants and seed commands.
The web service must never inherit those owner credentials. Seed password files are
operator-only ephemeral secret files with independent strong values; remove them
through the operator's approved secret-handling procedure after use.

## Vercel demo project

`VITE_API_BASE_URL=https://<approved-demo-api-host>/api/v1`

`VITE_ENABLE_MOCK_LOGIN=false`

`VITE_HOSTED_DEMO=true` enables strict build-time HTTPS/API-prefix/mock-login validation.

These are public build-time variables. No Django secret, DB credential or execution
nonce belongs in any VITE variable. Scope only to the demo project's approved
environments; preserve existing production/preview domains and settings.


Temporary Render native Python deployment: see [Render demo setup](RENDER_DEMO_SETUP.md).
Its explicit render_demo profile uses required TLS without a custom CA; the strict
demo/production and recovery profiles retain their original TLS policies.
