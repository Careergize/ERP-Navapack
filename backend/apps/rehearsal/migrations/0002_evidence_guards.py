from django.db import migrations

SQL = r'''
CREATE FUNCTION navapack_rehearsal_guard() RETURNS trigger AS $$
DECLARE stamp text;
BEGIN
 IF current_database() !~ '^test_phase3b_[0-9a-f]{32}$' OR to_regclass('public.navapack_synthetic_environment') IS NULL THEN
   RAISE EXCEPTION 'Rehearsal is synthetic only' USING ERRCODE='42501';
 END IF;
 SELECT nonce::text INTO stamp FROM public.navapack_synthetic_environment WHERE singleton;
 IF stamp IS NULL OR current_setting('navapack.ledger_nonce',true) IS DISTINCT FROM stamp THEN
   RAISE EXCEPTION 'Verified synthetic service context required' USING ERRCODE='42501';
 END IF;
 IF TG_OP='DELETE' OR (TG_TABLE_NAME='rehearsal_rehearsalrevision' AND TG_OP<>'INSERT') THEN
   RAISE EXCEPTION 'Rehearsal evidence is immutable' USING ERRCODE='23514';
 END IF;
 IF TG_TABLE_NAME='rehearsal_rehearsaljob' THEN
   IF NEW.status NOT IN ('DRAFT','REVIEWED','ISSUED','PRODUCTION','QC_FAILED','QC_PASSED','FINISHED','DISPATCHED') THEN
     RAISE EXCEPTION 'Unknown rehearsal status' USING ERRCODE='23514';
   END IF;
   IF TG_OP='UPDATE' AND (ROW(NEW.id,NEW.owner_id,NEW.sales_order_revision_id,NEW.warehouse_id,NEW.created_at)
     IS DISTINCT FROM ROW(OLD.id,OLD.owner_id,OLD.sales_order_revision_id,OLD.warehouse_id,OLD.created_at)
     OR NEW.version<>OLD.version+1 OR NEW.snapshot->'source' IS DISTINCT FROM OLD.snapshot->'source') THEN
     RAISE EXCEPTION 'Immutable source identity or invalid version' USING ERRCODE='23514';
   END IF;
 END IF;
 RETURN NEW;
END; $$ LANGUAGE plpgsql;
CREATE TRIGGER rehearsal_job_guard BEFORE INSERT OR UPDATE OR DELETE ON rehearsal_rehearsaljob
 FOR EACH ROW EXECUTE FUNCTION navapack_rehearsal_guard();
CREATE TRIGGER rehearsal_revision_guard BEFORE INSERT OR UPDATE OR DELETE ON rehearsal_rehearsalrevision
 FOR EACH ROW EXECUTE FUNCTION navapack_rehearsal_guard();

CREATE FUNCTION navapack_rehearsal_complete() RETURNS trigger AS $$
DECLARE job rehearsal_rehearsaljob; rev rehearsal_rehearsalrevision;
BEGIN
 IF TG_TABLE_NAME='rehearsal_rehearsalrevision' THEN
   SELECT * INTO job FROM rehearsal_rehearsaljob WHERE id=NEW.job_id;
   rev=NEW;
 ELSE
   SELECT * INTO job FROM rehearsal_rehearsaljob WHERE id=NEW.id;
   SELECT * INTO rev FROM rehearsal_rehearsalrevision WHERE job_id=job.id AND number=job.version;
 END IF;
 IF rev.id IS NULL OR rev.number>job.version OR rev.actor_id<>job.owner_id
   OR (rev.number=job.version AND (rev.snapshot->>'status'<>job.status OR rev.snapshot->'state'<>job.snapshot)) THEN
   RAISE EXCEPTION 'Coherent rehearsal revision required' USING ERRCODE='23514';
 END IF;
 IF NOT EXISTS(SELECT 1 FROM core_auditevent a JOIN core_auditevidence e ON e.event_id=a.id
   WHERE a.entity_type='rehearsal.rehearsaljob' AND a.entity_id=job.id::text
   AND a.source_version=rev.number AND a.actor_id=rev.actor_id AND a.action='rehearsal.use_simulation') THEN
   RAISE EXCEPTION 'Atomic rehearsal audit required' USING ERRCODE='23514';
 END IF;
 RETURN NULL;
END; $$ LANGUAGE plpgsql;
CREATE CONSTRAINT TRIGGER rehearsal_job_complete AFTER INSERT OR UPDATE ON rehearsal_rehearsaljob
 DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION navapack_rehearsal_complete();
CREATE CONSTRAINT TRIGGER rehearsal_revision_complete AFTER INSERT ON rehearsal_rehearsalrevision
 DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION navapack_rehearsal_complete();
'''


class Migration(migrations.Migration):
    dependencies = [('rehearsal', '0001_initial')]
    operations = [migrations.RunSQL(SQL, '''
DROP TRIGGER rehearsal_job_complete ON rehearsal_rehearsaljob;
DROP TRIGGER rehearsal_revision_complete ON rehearsal_rehearsalrevision;
DROP FUNCTION navapack_rehearsal_complete();
DROP TRIGGER rehearsal_job_guard ON rehearsal_rehearsaljob;
DROP TRIGGER rehearsal_revision_guard ON rehearsal_rehearsalrevision;
DROP FUNCTION navapack_rehearsal_guard();
''')]
