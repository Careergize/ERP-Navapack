-- Execute ONLY as the approved migration owner on the explicitly approved DEMO DB.
-- psql -X -v ON_ERROR_STOP=1 -v demo_database=... -v demo_runtime_role=... -f scripts/demo_runtime_grants.sql
-- Role creation/password delivery is separate; never use the managed owner as runtime.
\set ON_ERROR_STOP on
SELECT current_database() = :'demo_database' AND current_database() ~ '^navapack_demo_[a-z0-9_]{8,48}$' AS target_ok \gset
\if :target_ok
BEGIN;
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
REVOKE TEMPORARY ON DATABASE :"demo_database" FROM PUBLIC;
GRANT CONNECT ON DATABASE :"demo_database" TO :"demo_runtime_role";
GRANT USAGE ON SCHEMA public TO :"demo_runtime_role";
GRANT SELECT ON ALL TABLES IN SCHEMA public TO :"demo_runtime_role";
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO :"demo_runtime_role";
GRANT INSERT, UPDATE ON core_idempotencyrecord, core_throttlewindow TO :"demo_runtime_role";
GRANT INSERT ON core_auditevent, core_auditevidence TO :"demo_runtime_role";
GRANT INSERT, UPDATE, DELETE ON token_blacklist_outstandingtoken, token_blacklist_blacklistedtoken TO :"demo_runtime_role";
GRANT INSERT, UPDATE ON commercial_commercialdocument, commercial_governancerecord, rehearsal_rehearsaljob TO :"demo_runtime_role";
GRANT INSERT ON commercial_commercialrevision, commercial_governancerevision, rehearsal_rehearsalrevision TO :"demo_runtime_role";
GRANT INSERT ON masters_customer TO :"demo_runtime_role";
-- PostgreSQL SELECT FOR UPDATE requires UPDATE privilege on at least one column.
-- These grants support locked reference reads, not full catalog mutation.
GRANT UPDATE (version) ON masters_customer, masters_prospect, masters_unit, masters_material, masters_productvariant TO :"demo_runtime_role";
GRANT UPDATE (id) ON specifications_productmodelrevision TO :"demo_runtime_role";
GRANT UPDATE (id) ON commercial_commercialrevision TO :"demo_runtime_role";
COMMIT;
\else
\echo 'Refusing nonmatching DEMO database'
\quit 3
\endif
