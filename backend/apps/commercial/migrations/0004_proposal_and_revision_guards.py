from django.db import migrations

SQL = r'''
CREATE FUNCTION navapack_governance_guard() RETURNS trigger AS $$
DECLARE stamp text; head commercial_governancerecord;
BEGIN
 IF current_database() !~ '^test_phase3b_[0-9a-f]{32}$' OR to_regclass('public.navapack_synthetic_environment') IS NULL THEN
   RAISE EXCEPTION 'Proposals are synthetic only' USING ERRCODE='42501';
 END IF;
 SELECT nonce::text INTO stamp FROM public.navapack_synthetic_environment WHERE singleton;
 IF stamp IS NULL OR current_setting('navapack.ledger_nonce',true) IS DISTINCT FROM stamp THEN
   RAISE EXCEPTION 'Verified synthetic proposal context required' USING ERRCODE='42501';
 END IF;
 IF TG_OP='DELETE' OR (TG_TABLE_NAME='commercial_governancerevision' AND TG_OP<>'INSERT') THEN
   RAISE EXCEPTION 'Proposal evidence is append-only' USING ERRCODE='23514';
 END IF;
 IF TG_TABLE_NAME='commercial_governancerecord' THEN
   IF TG_OP='INSERT' AND NEW.version<>1 THEN RAISE EXCEPTION 'Initial proposal version must be one' USING ERRCODE='23514'; END IF;
   IF TG_OP='UPDATE' AND (ROW(NEW.id,NEW.owner_id,NEW.kind,NEW.key,NEW.created_at) IS DISTINCT FROM ROW(OLD.id,OLD.owner_id,OLD.kind,OLD.key,OLD.created_at) OR NEW.version<>OLD.version+1) THEN
      RAISE EXCEPTION 'Proposal identity is immutable; advance one version' USING ERRCODE='23514';
   END IF;
   IF (NEW.kind='DECISION' AND NEW.key !~ '^P4-0[1-8]$') OR (NEW.kind='POLICY' AND NEW.key NOT IN ('PRICING_DISCOUNT','APPROVAL_MATRIX','CURRENCY_ROUNDING','VAT_LED','CUSTOMER_ACCEPTANCE','DOCUMENT_NUMBERING','QUOTATION_VALIDITY','ORDER_AMENDMENT','COSTING_UNIT_GOVERNANCE')) THEN
      RAISE EXCEPTION 'Unknown proposal identity' USING ERRCODE='23514';
   END IF;
 ELSE
   SELECT * INTO head FROM commercial_governancerecord WHERE id=NEW.record_id;
   IF head.id IS NULL OR NEW.number<>head.version OR NEW.author_id<>head.owner_id
      OR NEW.sha256 !~ '^[0-9a-f]{64}$' OR octet_length(NEW.content::text)>131072
      OR jsonb_typeof(NEW.content) IS DISTINCT FROM 'object'
      OR jsonb_typeof(NEW.content->'evidence') IS DISTINCT FROM 'array' THEN
      RAISE EXCEPTION 'Incoherent proposal revision' USING ERRCODE='23514';
   END IF;
   IF head.kind='POLICY' AND (NEW.status<>'PROPOSED_UNVERIFIED' OR NEW.content->>'policy_type' IS DISTINCT FROM head.key)
      OR head.kind='DECISION' AND (NEW.status<>'PENDING_VERIFICATION' OR NEW.content->>'decision_id' IS DISTINCT FROM head.key) THEN
      RAISE EXCEPTION 'Proposal cannot become approved or resolved' USING ERRCODE='23514';
   END IF;
 END IF;
 RETURN NEW;
END; $$ LANGUAGE plpgsql;
CREATE TRIGGER governance_head_guard BEFORE INSERT OR UPDATE OR DELETE ON commercial_governancerecord FOR EACH ROW EXECUTE FUNCTION navapack_governance_guard();
CREATE TRIGGER governance_revision_guard BEFORE INSERT OR UPDATE OR DELETE ON commercial_governancerevision FOR EACH ROW EXECUTE FUNCTION navapack_governance_guard();

CREATE FUNCTION navapack_governance_complete() RETURNS trigger AS $$
DECLARE head commercial_governancerecord; rev commercial_governancerevision;
BEGIN
 IF TG_TABLE_NAME='commercial_governancerevision' THEN
   SELECT * INTO head FROM commercial_governancerecord WHERE id=NEW.record_id; rev=NEW;
 ELSE
   SELECT * INTO head FROM commercial_governancerecord WHERE id=NEW.id;
   SELECT * INTO rev FROM commercial_governancerevision WHERE record_id=NEW.id AND number=NEW.version;
 END IF;
 IF rev.id IS NULL OR rev.number>head.version OR NOT EXISTS (
   SELECT 1 FROM core_auditevent a JOIN core_auditevidence e ON e.event_id=a.id
   WHERE a.entity_type='commercial.governancerecord' AND a.entity_id=head.id::text AND a.actor_id=rev.author_id
     AND a.source_version=rev.number AND a.action='commercial.manage_proposals' AND a.reason=rev.reason
     AND a.summary->'outcome'->>'revision'=rev.id::text AND a.summary->'outcome'->>'sha256'=rev.sha256) THEN
   RAISE EXCEPTION 'Proposal requires atomic linked audit evidence' USING ERRCODE='23514';
 END IF;
 RETURN NULL;
END; $$ LANGUAGE plpgsql;
CREATE CONSTRAINT TRIGGER governance_head_complete AFTER INSERT OR UPDATE ON commercial_governancerecord DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION navapack_governance_complete();
CREATE CONSTRAINT TRIGGER governance_revision_complete AFTER INSERT ON commercial_governancerevision DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION navapack_governance_complete();

CREATE FUNCTION navapack_commercial_revision_harden() RETURNS trigger AS $$
DECLARE head commercial_commercialdocument;
BEGIN
 IF TG_TABLE_NAME='commercial_commercialdocument' THEN
   IF NEW.version<>1 OR NEW.status<>'DRAFT' THEN RAISE EXCEPTION 'Commercial documents start as draft version one' USING ERRCODE='23514'; END IF;
 ELSE
   SELECT * INTO head FROM commercial_commercialdocument WHERE id=NEW.document_id;
   IF NEW.number<>head.version OR NEW.actor_id<>head.owner_id OR NEW.status<>head.status OR NEW.sha256 !~ '^[0-9a-f]{64}$'
      OR octet_length(NEW.snapshot::text)>524288 OR NEW.snapshot->'estimate'->'authoritative' IS DISTINCT FROM 'false'::jsonb
      OR NEW.snapshot->'estimate'->'vat' IS DISTINCT FROM 'null'::jsonb OR NEW.snapshot->'estimate'->'led' IS DISTINCT FROM 'null'::jsonb
      OR NEW.snapshot->'estimate'->'payable_total' IS DISTINCT FROM 'null'::jsonb THEN
      RAISE EXCEPTION 'Commercial revision must be current and nonauthoritative with blocked tax totals' USING ERRCODE='23514';
   END IF;
 END IF;
 RETURN NEW;
END; $$ LANGUAGE plpgsql;
CREATE TRIGGER commercial_initial_guard BEFORE INSERT ON commercial_commercialdocument FOR EACH ROW EXECUTE FUNCTION navapack_commercial_revision_harden();
CREATE TRIGGER commercial_current_revision_guard BEFORE INSERT ON commercial_commercialrevision FOR EACH ROW EXECUTE FUNCTION navapack_commercial_revision_harden();
CREATE FUNCTION navapack_commercial_linked_audit() RETURNS trigger AS $$
BEGIN
 IF NOT EXISTS(SELECT 1 FROM core_auditevent a JOIN core_auditevidence e ON e.event_id=a.id WHERE
   a.entity_type='commercial.commercialdocument' AND a.entity_id=NEW.document_id::text AND a.actor_id=NEW.actor_id
   AND a.source_version=NEW.number AND a.action='commercial.use_foundation' AND a.reason=NEW.reason
   AND a.summary->'outcome'->>'revision'=NEW.id::text AND a.summary->'outcome'->>'sha256'=NEW.sha256) THEN
   RAISE EXCEPTION 'Commercial revision requires linked audit evidence and reason' USING ERRCODE='23514';
 END IF;
 RETURN NULL;
END; $$ LANGUAGE plpgsql;
CREATE CONSTRAINT TRIGGER commercial_linked_audit AFTER INSERT ON commercial_commercialrevision DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION navapack_commercial_linked_audit();
'''


class Migration(migrations.Migration):
    dependencies = [('commercial', '0003_governancerecord_governancerevision_and_more')]
    operations = [migrations.RunSQL(SQL, '''
DROP TRIGGER commercial_linked_audit ON commercial_commercialrevision;
DROP FUNCTION navapack_commercial_linked_audit();
DROP TRIGGER commercial_initial_guard ON commercial_commercialdocument;
DROP TRIGGER commercial_current_revision_guard ON commercial_commercialrevision;
DROP FUNCTION navapack_commercial_revision_harden();
DROP TRIGGER governance_head_complete ON commercial_governancerecord;
DROP TRIGGER governance_revision_complete ON commercial_governancerevision;
DROP FUNCTION navapack_governance_complete();
DROP TRIGGER governance_head_guard ON commercial_governancerecord;
DROP TRIGGER governance_revision_guard ON commercial_governancerevision;
DROP FUNCTION navapack_governance_guard();
''')]
