from django.db import migrations


SQL = r'''
CREATE FUNCTION navapack_commercial_guard() RETURNS trigger AS $$
DECLARE stamp text;
BEGIN
 IF current_database() !~ '^test_phase3b_[0-9a-f]{32}$' OR to_regclass('public.navapack_synthetic_environment') IS NULL THEN
   RAISE EXCEPTION 'Commercial foundation is synthetic only' USING ERRCODE='42501';
 END IF;
 SELECT nonce::text INTO stamp FROM public.navapack_synthetic_environment WHERE singleton;
 IF stamp IS NULL OR current_setting('navapack.ledger_nonce',true) IS DISTINCT FROM stamp THEN
   RAISE EXCEPTION 'Verified synthetic command context required' USING ERRCODE='42501';
 END IF;
 IF TG_OP='DELETE' OR (TG_TABLE_NAME='commercial_commercialrevision' AND TG_OP<>'INSERT') THEN
   RAISE EXCEPTION 'Commercial evidence is immutable' USING ERRCODE='23514';
 END IF;
 IF TG_TABLE_NAME='commercial_commercialdocument' AND TG_OP='UPDATE' THEN
   IF ROW(NEW.id,NEW.kind,NEW.owner_id,NEW.created_at) IS DISTINCT FROM ROW(OLD.id,OLD.kind,OLD.owner_id,OLD.created_at)
      OR NEW.version<>OLD.version+1 OR OLD.status='CANCELLED'
      OR NOT ((OLD.status='DRAFT' AND NEW.status IN ('DRAFT','REVIEW','CANCELLED')) OR (OLD.status='REVIEW' AND NEW.status='DRAFT')) THEN
      RAISE EXCEPTION 'Invalid commercial amendment' USING ERRCODE='23514';
   END IF;
 END IF;
 RETURN NEW;
END; $$ LANGUAGE plpgsql;
CREATE TRIGGER commercial_document_guard BEFORE INSERT OR UPDATE OR DELETE ON commercial_commercialdocument
 FOR EACH ROW EXECUTE FUNCTION navapack_commercial_guard();
CREATE TRIGGER commercial_revision_guard BEFORE INSERT OR UPDATE OR DELETE ON commercial_commercialrevision
 FOR EACH ROW EXECUTE FUNCTION navapack_commercial_guard();

CREATE FUNCTION navapack_commercial_complete() RETURNS trigger AS $$
DECLARE doc commercial_commercialdocument; rev commercial_commercialrevision;
BEGIN
 IF TG_TABLE_NAME='commercial_commercialrevision' THEN
   SELECT * INTO doc FROM commercial_commercialdocument WHERE id=NEW.document_id;
   rev=NEW;
 ELSE
   SELECT * INTO doc FROM commercial_commercialdocument WHERE id=NEW.id;
   SELECT * INTO rev FROM commercial_commercialrevision WHERE document_id=NEW.id AND number=NEW.version;
 END IF;
 IF rev.id IS NULL OR rev.number>doc.version OR rev.status NOT IN ('DRAFT','REVIEW','CANCELLED') OR rev.actor_id<>doc.owner_id
    OR (rev.number=doc.version AND rev.status<>doc.status) THEN
   RAISE EXCEPTION 'Commercial command requires coherent revision evidence' USING ERRCODE='23514';
 END IF;
 IF NOT EXISTS(SELECT 1 FROM core_auditevent a JOIN core_auditevidence e ON e.event_id=a.id
     WHERE a.entity_type='commercial.commercialdocument' AND a.entity_id=doc.id::text
     AND a.actor_id=rev.actor_id AND a.source_version=rev.number AND a.action='commercial.use_foundation') THEN
   RAISE EXCEPTION 'Commercial command requires atomic audit evidence' USING ERRCODE='23514';
 END IF;
 RETURN NULL;
END; $$ LANGUAGE plpgsql;
CREATE CONSTRAINT TRIGGER commercial_document_complete AFTER INSERT OR UPDATE ON commercial_commercialdocument
 DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION navapack_commercial_complete();
CREATE CONSTRAINT TRIGGER commercial_revision_complete AFTER INSERT ON commercial_commercialrevision
 DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION navapack_commercial_complete();
'''


class Migration(migrations.Migration):
    dependencies = [('commercial', '0001_initial'), ('core', '0004_protect_audit_evidence')]
    operations = [migrations.RunSQL(SQL, '''
DROP TRIGGER commercial_document_complete ON commercial_commercialdocument;
DROP TRIGGER commercial_revision_complete ON commercial_commercialrevision;
DROP FUNCTION navapack_commercial_complete();
DROP TRIGGER commercial_document_guard ON commercial_commercialdocument;
DROP TRIGGER commercial_revision_guard ON commercial_commercialrevision;
DROP FUNCTION navapack_commercial_guard();
''')]
