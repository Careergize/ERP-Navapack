from django.db import migrations

TABLES = ['inspectionplan','planapproval','inspection','inspectionreview','qualityauthorization',
          'qualityposting','qualityhold','nonconformance','nonconformanceaction']
SQL = r'''
CREATE FUNCTION navapack_qc_complete() RETURNS trigger AS $$
DECLARE actor uuid; head inventory_ledgertransaction; auth inventory_qualityauthorization;
        review inventory_inspectionreview; inspected inventory_inspection; source_quality text; dest_quality text;
BEGIN
 IF TG_TABLE_NAME='inventory_qualityposting' THEN
   SELECT * INTO auth FROM inventory_qualityauthorization WHERE id=NEW.authorization_id;
   SELECT * INTO head FROM inventory_ledgertransaction WHERE id=NEW.transaction_id;
   IF head.kind IS DISTINCT FROM 'QUALITY' OR head.actor_id<>auth.actor_id OR head.database_txid<>txid_current()
      OR head.reverses_id IS NOT NULL OR head.related_id IS NOT NULL THEN
     RAISE EXCEPTION 'QC requires its own same-transaction conserved posting' USING ERRCODE='23514'; END IF;
   IF auth.direction='RELEASE' THEN
     source_quality='HELD'; dest_quality='RELEASED';
     SELECT * INTO review FROM inventory_inspectionreview WHERE id=auth.review_id;
     SELECT * INTO inspected FROM inventory_inspection WHERE id=review.inspection_id;
     IF review.decision IS DISTINCT FROM 'ACCEPT' OR review.actor_id=inspected.inspector_id OR auth.actor_id=inspected.inspector_id
       OR auth.stock_id<>inspected.stock_id OR auth.location_id<>inspected.location_id OR auth.quantity<>inspected.quantity
       OR EXISTS(SELECT 1 FROM inventory_qualityhold WHERE stock_id=auth.stock_id)
       OR NOT EXISTS(SELECT 1 FROM inventory_planapproval WHERE plan_id=inspected.plan_id AND decision='APPROVED') THEN
       RAISE EXCEPTION 'Independent approved exact QC release required' USING ERRCODE='23514'; END IF;
   ELSE source_quality='RELEASED'; dest_quality='HELD'; END IF;
   IF (SELECT count(*) FROM inventory_ledgerentry WHERE transaction_id=head.id)<>2
     OR NOT EXISTS(SELECT 1 FROM inventory_ledgerentry WHERE transaction_id=head.id AND stock_id=auth.stock_id AND location_id=auth.location_id AND quality=source_quality AND delta=-auth.quantity)
     OR NOT EXISTS(SELECT 1 FROM inventory_ledgerentry WHERE transaction_id=head.id AND stock_id=auth.stock_id AND location_id=auth.location_id AND quality=dest_quality AND delta=auth.quantity)
     OR (SELECT count(*) FROM inventory_transactionline WHERE transaction_id=head.id)<>2 THEN
     RAISE EXCEPTION 'QC conserves physical quantity at exact identity and custody' USING ERRCODE='23514'; END IF;
   RETURN NULL;
 ELSIF TG_TABLE_NAME='inventory_qualityauthorization' THEN
   IF NOT EXISTS(SELECT 1 FROM inventory_qualityposting WHERE authorization_id=NEW.id) THEN
     RAISE EXCEPTION 'QC authority must commit with its posting' USING ERRCODE='23514'; END IF;
   IF NEW.direction='RELEASE' THEN
     IF NOT EXISTS(SELECT 1 FROM core_auditevent a JOIN core_auditevidence e ON e.event_id=a.id
       WHERE a.entity_type='inventory.qualityauthorization' AND a.entity_id=NEW.id::text AND a.actor_id=NEW.actor_id
       AND a.action='inventory.qc_release' AND a.source_version=1) THEN
       RAISE EXCEPTION 'QC release requires its atomic decision audit' USING ERRCODE='23514'; END IF;
   ELSE
     IF NOT EXISTS(SELECT 1 FROM inventory_qualityhold h JOIN core_auditevent a ON a.entity_id=h.id::text
       JOIN core_auditevidence e ON e.event_id=a.id WHERE h.authorization_id=NEW.id
       AND a.entity_type='inventory.qualityhold' AND a.actor_id=NEW.actor_id AND a.action='inventory.qc_hold') THEN
       RAISE EXCEPTION 'QC re-hold requires its atomic containment audit' USING ERRCODE='23514'; END IF;
   END IF;
   RETURN NULL;
 END IF;
 IF TG_TABLE_NAME='inventory_inspectionplan' THEN actor=NEW.author_id;
 ELSIF TG_TABLE_NAME='inventory_inspection' THEN actor=NEW.inspector_id;
 ELSE actor=NEW.actor_id; END IF;
 IF NOT EXISTS(SELECT 1 FROM core_auditevent a JOIN core_auditevidence e ON e.event_id=a.id
    WHERE a.entity_type=replace(TG_TABLE_NAME,'inventory_','inventory.') AND a.entity_id=NEW.id::text
      AND a.actor_id=actor AND a.source_version=1 AND a.action LIKE 'inventory.qc_%') THEN
    RAISE EXCEPTION 'QC evidence requires atomic attributed audit' USING ERRCODE='23514'; END IF;
 IF TG_TABLE_NAME='inventory_planapproval' THEN
   IF EXISTS(SELECT 1 FROM inventory_inspectionplan WHERE id=NEW.plan_id AND author_id=NEW.actor_id) THEN
     RAISE EXCEPTION 'Plan publication requires independence' USING ERRCODE='23514'; END IF;
 END IF;
 IF TG_TABLE_NAME='inventory_inspectionreview' THEN
   IF EXISTS(SELECT 1 FROM inventory_inspection WHERE id=NEW.inspection_id AND inspector_id=NEW.actor_id) THEN
     RAISE EXCEPTION 'QC review requires independence' USING ERRCODE='23514'; END IF;
 END IF;
 RETURN NULL;
END; $$ LANGUAGE plpgsql;

CREATE FUNCTION navapack_qc_ledger_complete() RETURNS trigger AS $$
DECLARE stamp text;
BEGIN
 IF NEW.kind IN ('OPENING','IN') AND EXISTS(SELECT 1 FROM inventory_ledgerentry WHERE transaction_id=NEW.id AND quality='RELEASED' AND delta>0) THEN
   SELECT nonce::text INTO stamp FROM public.navapack_synthetic_environment WHERE singleton;
   IF current_setting('navapack.legacy_quality_fixture',true) IS DISTINCT FROM stamp THEN
     RAISE EXCEPTION 'New stock remains held without QC release; legacy fixtures require explicit disposable-test context' USING ERRCODE='23514'; END IF;
 END IF;
 IF NEW.kind='QUALITY' AND NOT EXISTS(SELECT 1 FROM inventory_qualityposting WHERE transaction_id=NEW.id) THEN
   RAISE EXCEPTION 'Quality transition requires sealed QC authority' USING ERRCODE='23514'; END IF;
 IF NEW.kind='REVERSAL' AND EXISTS(SELECT 1 FROM inventory_ledgertransaction WHERE id=NEW.reverses_id AND kind='QUALITY') THEN
   RAISE EXCEPTION 'Generic reversal cannot undo QC controls' USING ERRCODE='23514'; END IF;
 RETURN NULL;
END; $$ LANGUAGE plpgsql;
CREATE CONSTRAINT TRIGGER qc_ledger_complete AFTER INSERT ON inventory_ledgertransaction
 DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION navapack_qc_ledger_complete();

CREATE FUNCTION navapack_qc_containment() RETURNS trigger AS $$
BEGIN
 IF NEW.delta<0 AND EXISTS(SELECT 1 FROM inventory_qualityhold WHERE stock_id=NEW.stock_id)
   AND NOT EXISTS(SELECT 1 FROM inventory_qualityposting p JOIN inventory_qualityauthorization a ON a.id=p.authorization_id
      WHERE p.transaction_id=NEW.transaction_id AND a.direction='HOLD') THEN
   RAISE EXCEPTION 'Explicit root containment prohibits use and transfer pending disposition' USING ERRCODE='23514'; END IF;
 RETURN NEW;
END; $$ LANGUAGE plpgsql;
CREATE TRIGGER qc_containment BEFORE INSERT ON inventory_ledgerentry FOR EACH ROW EXECUTE FUNCTION navapack_qc_containment();
'''
for table in TABLES:
    SQL += f'CREATE TRIGGER qc_guard BEFORE INSERT OR UPDATE OR DELETE ON inventory_{table} FOR EACH ROW EXECUTE FUNCTION navapack_ledger_guard();\n'
    SQL += f'CREATE CONSTRAINT TRIGGER qc_complete AFTER INSERT ON inventory_{table} DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION navapack_qc_complete();\n'
REVERSE = 'DROP TRIGGER qc_containment ON inventory_ledgerentry; DROP FUNCTION navapack_qc_containment(); DROP TRIGGER qc_ledger_complete ON inventory_ledgertransaction; DROP FUNCTION navapack_qc_ledger_complete();'
for table in TABLES:
    REVERSE += f'DROP TRIGGER qc_guard ON inventory_{table}; DROP TRIGGER qc_complete ON inventory_{table};'
REVERSE += 'DROP FUNCTION navapack_qc_complete();'

class Migration(migrations.Migration):
    dependencies = [('inventory','0012_qc_foundation')]
    operations = [migrations.RunSQL(SQL, REVERSE)]
