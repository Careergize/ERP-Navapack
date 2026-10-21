# Persistent local development storage — proposed, not executed

21 October 2026. Requires separate explicit authorization before provisioning.

1. Identify a new development database and dedicated owner/runtime roles. Do not reuse
   `navapack` or any application/test database. Use the existing reviewed persistent
   DEMO settings/boundary and required naming if that mode is chosen. It deliberately
   does not grant inventory-ledger authority; synthetic inventory stays disposable.
2. Review `showmigrations --plan`, forward migration SQL and current schema dependencies
   against the chosen fresh target. Record the exact Git revision and migration set.
   Never point migration commands at the configured application database.
3. Isolate listener/database access to loopback. Use independent secrets, a migration
   owner and the documented restricted runtime grants. Verify the runtime has no
   superuser, CREATEDB/CREATEROLE/BYPASSRLS, inherited owner membership or table ownership.
4. Adopt a development-data policy: synthetic identities only, no original workbook
   balance import, no real customer communication and no operational/financial posting.
   Provision only reviewed fixture capabilities/scopes and expiry, with clear labels.
5. Before any future upgrade, take a database backup, inventory role/grant metadata,
   verify the backup digest and restore into another isolated database. Keep dumps,
   credentials and logs outside Git. Confirm retention and deletion ownership.
6. Re-run JWT authorization, immutable audit/revision, guard, concurrency and real HTTP
   transport tests using the restricted runtime profile. Test restoration/relogin.
7. Record explicit approval of the target database, migration plan, runtime grants,
   data retention, backup/restore result and non-operational boundary before switching
   the local API. Keep the prior application configuration recoverable.

No action in this document creates persistent storage or changes an existing database.
