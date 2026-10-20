from django.db import migrations
SQL=r'''
CREATE FUNCTION navapack_operation_guard() RETURNS trigger AS $$
DECLARE stamp text; req inventory_operationrequest;
BEGIN
 IF current_database() !~ '^test_phase3b_[0-9a-f]{32}$' OR to_regclass('public.navapack_synthetic_environment') IS NULL THEN
  RAISE EXCEPTION 'Operational workflows are disabled' USING ERRCODE='42501';
 END IF;
 SELECT nonce::text INTO stamp FROM public.navapack_synthetic_environment WHERE singleton;
 IF current_setting('navapack.ledger_nonce',true) IS DISTINCT FROM stamp THEN RAISE EXCEPTION 'Synthetic workflow context required' USING ERRCODE='42501'; END IF;
 IF TG_OP='DELETE' THEN RAISE EXCEPTION 'Workflow history cannot be deleted' USING ERRCODE='23514'; END IF;
 IF TG_TABLE_NAME<>'inventory_operationrequest' THEN
  IF TG_OP<>'INSERT' THEN RAISE EXCEPTION 'Workflow evidence is immutable' USING ERRCODE='23514'; END IF;
  SELECT * INTO req FROM inventory_operationrequest WHERE id=NEW.request_id;
  IF TG_TABLE_NAME='inventory_operationline' AND (req.version<>1 OR req.status<>'SUBMITTED' OR req.submission_txid<>txid_current()) THEN RAISE EXCEPTION 'Submitted lines are sealed' USING ERRCODE='23514'; END IF;
  IF TG_TABLE_NAME='inventory_operationdecision' THEN
   IF req.mutation_txid<>txid_current() OR NEW.version<>req.version OR NEW.to_status<>req.status THEN RAISE EXCEPTION 'Decision must seal the current atomic transition' USING ERRCODE='23514'; END IF;
  END IF;
  RETURN NEW;
 END IF;
 IF NEW.source_system NOT LIKE 'synthetic:%' THEN RAISE EXCEPTION 'Synthetic source required' USING ERRCODE='23514'; END IF;
 IF TG_OP='INSERT' THEN NEW.submission_txid=txid_current(); NEW.mutation_txid=txid_current(); END IF;
 IF TG_OP='UPDATE' THEN
  IF NEW.submission_txid<>OLD.submission_txid THEN RAISE EXCEPTION 'Submission transaction is immutable' USING ERRCODE='23514'; END IF;
  NEW.mutation_txid=txid_current();
  IF OLD.status IN ('POSTED','REJECTED') OR NEW.version<>OLD.version+1 THEN RAISE EXCEPTION 'Terminal/version protection' USING ERRCODE='23514'; END IF;
  IF ROW(NEW.id,NEW.kind,NEW.warehouse_id,NEW.destination_warehouse_id,NEW.requested_by_id,NEW.policy_id,NEW.source_system,NEW.source_event,NEW.source_reference,NEW.evidence_reference,NEW.counterparty_reference,NEW.reason,NEW.cutoff,NEW.related_id,NEW.count_session_id,NEW.created_at)
    IS DISTINCT FROM ROW(OLD.id,OLD.kind,OLD.warehouse_id,OLD.destination_warehouse_id,OLD.requested_by_id,OLD.policy_id,OLD.source_system,OLD.source_event,OLD.source_reference,OLD.evidence_reference,OLD.counterparty_reference,OLD.reason,OLD.cutoff,OLD.related_id,OLD.count_session_id,OLD.created_at) THEN RAISE EXCEPTION 'Submitted evidence is sealed' USING ERRCODE='23514'; END IF;
  IF NOT ((OLD.status='SUBMITTED' AND NEW.status IN ('VERIFIED','REJECTED')) OR (OLD.status='VERIFIED' AND NEW.status IN ('INVESTIGATED','CONFIRMED','REJECTED')) OR (OLD.status='INVESTIGATED' AND NEW.status IN ('CONFIRMED','REJECTED')) OR (OLD.status='CONFIRMED' AND NEW.status IN ('APPROVED','REJECTED')) OR (OLD.status='APPROVED' AND NEW.status IN ('POSTED','REJECTED'))) THEN RAISE EXCEPTION 'Invalid workflow transition' USING ERRCODE='23514'; END IF;
  IF NEW.status<>'APPROVED' AND ROW(NEW.recording_employee_id,NEW.sealed_intent) IS DISTINCT FROM ROW(OLD.recording_employee_id,OLD.sealed_intent) THEN RAISE EXCEPTION 'Approval content is sealed' USING ERRCODE='23514'; END IF;
 END IF;
 RETURN NEW;
END; $$ LANGUAGE plpgsql;
CREATE FUNCTION navapack_operation_complete() RETURNS trigger AS $$
DECLARE req inventory_operationrequest; decision inventory_operationdecision;
BEGIN
 SELECT * INTO req FROM inventory_operationrequest WHERE id=NEW.id;
 SELECT * INTO decision FROM inventory_operationdecision WHERE request_id=NEW.id AND version=NEW.version;
 IF decision.id IS NULL OR decision.to_status<>NEW.status OR NOT EXISTS(SELECT 1 FROM inventory_operationline WHERE request_id=NEW.id) THEN RAISE EXCEPTION 'Workflow requires sealed lines and decision' USING ERRCODE='23514'; END IF;
 IF NOT EXISTS(SELECT 1 FROM core_auditevent a JOIN core_auditevidence e ON e.event_id=a.id WHERE a.entity_type='inventory.operationrequest' AND a.entity_id=NEW.id::text AND a.source_version=NEW.version AND a.actor_id=decision.actor_id) THEN RAISE EXCEPTION 'Workflow requires atomic attributed audit' USING ERRCODE='23514'; END IF;
 IF NEW.status='APPROVED' AND (NEW.sealed_intent IS NULL OR NEW.recording_employee_id IS NULL OR decision.actor_id=NEW.requested_by_id OR decision.actor_id=NEW.recording_employee_id) THEN RAISE EXCEPTION 'Independent sealed approval required' USING ERRCODE='23514'; END IF;
 RETURN NULL;
END; $$ LANGUAGE plpgsql;
'''
for table in ['operationrequest','operationline','operationdecision']:
 SQL+=f'CREATE TRIGGER operation_guard BEFORE INSERT OR UPDATE OR DELETE ON inventory_{table} FOR EACH ROW EXECUTE FUNCTION navapack_operation_guard();\n'
SQL+='CREATE CONSTRAINT TRIGGER operation_complete AFTER INSERT OR UPDATE ON inventory_operationrequest DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION navapack_operation_complete();'
REVERSE='DROP TRIGGER operation_complete ON inventory_operationrequest;'
for table in ['operationrequest','operationline','operationdecision']:REVERSE+=f'DROP TRIGGER operation_guard ON inventory_{table};'
REVERSE+='DROP FUNCTION navapack_operation_complete(); DROP FUNCTION navapack_operation_guard();'
class Migration(migrations.Migration):
 dependencies=[('inventory','0008_operationrequest_operationline_operationdecision_and_more')]
 operations=[migrations.RunSQL(SQL,REVERSE)]
