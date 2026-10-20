from django.db import migrations

SQL=r'''
CREATE FUNCTION navapack_ledger_guard() RETURNS trigger AS $$
DECLARE stamp text; parent_tx inventory_ledgertransaction; ident inventory_stockidentity; expected_owner text; expected_key text;
BEGIN
 IF current_database() !~ '^test_phase3b_[0-9a-f]{32}$' OR to_regclass('public.navapack_synthetic_environment') IS NULL THEN
   RAISE EXCEPTION 'Operational ledger writes are disabled' USING ERRCODE='42501';
 END IF;
 SELECT nonce::text INTO stamp FROM public.navapack_synthetic_environment WHERE singleton;
 IF current_setting('navapack.ledger_nonce',true) IS DISTINCT FROM stamp THEN
   RAISE EXCEPTION 'Verified synthetic service context required' USING ERRCODE='42501';
 END IF;
 IF TG_TABLE_NAME='inventory_balanceprojection' THEN
   IF TG_OP='DELETE' THEN
     IF current_setting('navapack.ledger_rebuild',true) IS DISTINCT FROM 'on' THEN RAISE EXCEPTION 'Projection deletion requires rebuild' USING ERRCODE='23514'; END IF;
     RETURN OLD;
   END IF;
   IF TG_OP='UPDATE' THEN
     IF ROW(NEW.id,NEW.balance_key,NEW.stock_id,NEW.location_id,NEW.unit_id,NEW.owner_key,NEW.quality,NEW.created_at)
       IS DISTINCT FROM ROW(OLD.id,OLD.balance_key,OLD.stock_id,OLD.location_id,OLD.unit_id,OLD.owner_key,OLD.quality,OLD.created_at)
     THEN RAISE EXCEPTION 'Custody key is immutable' USING ERRCODE='23514'; END IF;
     IF NEW.version<>OLD.version+1 THEN RAISE EXCEPTION 'Projection version must advance' USING ERRCODE='23514'; END IF;
   END IF;
 ELSIF TG_TABLE_NAME='inventory_openingcoverage' THEN
   IF TG_OP='DELETE' OR (TG_OP='UPDATE' AND OLD.status='KNOWN') THEN RAISE EXCEPTION 'Opening coverage history is immutable' USING ERRCODE='23514'; END IF;
   IF TG_OP='UPDATE' AND ROW(NEW.stock_id,NEW.location_id,NEW.unit_id,NEW.owner_key,NEW.id,NEW.created_at)
      IS DISTINCT FROM ROW(OLD.stock_id,OLD.location_id,OLD.unit_id,OLD.owner_key,OLD.id,OLD.created_at)
   THEN RAISE EXCEPTION 'Opening scope is immutable' USING ERRCODE='23514'; END IF;
   IF NEW.status='KNOWN' THEN
      SELECT * INTO parent_tx FROM inventory_ledgertransaction WHERE id=NEW.transaction_id;
      IF parent_tx.kind IS DISTINCT FROM 'OPENING' OR parent_tx.database_txid<>txid_current() THEN RAISE EXCEPTION 'Coverage requires its new opening transaction' USING ERRCODE='23514'; END IF;
   END IF;
 ELSE
   IF TG_OP<>'INSERT' THEN RAISE EXCEPTION 'Posted ledger evidence is append-only' USING ERRCODE='23514'; END IF;
 END IF;
 IF TG_TABLE_NAME='inventory_postingpolicy' THEN
   IF NOT NEW.synthetic OR NEW.reference NOT LIKE 'synthetic:%' THEN RAISE EXCEPTION 'Synthetic policies only' USING ERRCODE='23514'; END IF;
 END IF;
 IF TG_TABLE_NAME='inventory_sourceevent' THEN
   IF NEW.system NOT LIKE 'synthetic:%' THEN RAISE EXCEPTION 'Synthetic source only' USING ERRCODE='23514'; END IF;
 END IF;
 IF TG_TABLE_NAME='inventory_ledgertransaction' THEN NEW.database_txid=txid_current(); END IF;
 IF TG_TABLE_NAME IN ('inventory_transactionline','inventory_ledgerentry') THEN
   SELECT * INTO parent_tx FROM inventory_ledgertransaction WHERE id=NEW.transaction_id;
   IF parent_tx.id IS NULL OR parent_tx.database_txid<>txid_current() THEN RAISE EXCEPTION 'Cannot append to a previously posted transaction' USING ERRCODE='23514'; END IF;
 END IF;
 IF TG_TABLE_NAME IN ('inventory_transactionline','inventory_ledgerentry','inventory_balanceprojection','inventory_openingcoverage') THEN
   SELECT * INTO ident FROM inventory_stockidentity WHERE id=NEW.stock_id;
   IF ident.id IS NULL OR NEW.unit_id<>ident.unit_id OR ident.ownership='UNRESOLVED' OR ident.parent_id IS NOT NULL THEN
     RAISE EXCEPTION 'Identity/unit/ownership/lineage is unavailable' USING ERRCODE='23514';
   END IF;
   IF TG_TABLE_NAME<>'inventory_transactionline' THEN
     expected_owner=ident.ownership||':'||CASE WHEN ident.ownership='CUSTOMER' THEN ident.owner_customer_id::text WHEN ident.ownership='SUPPLIER' THEN ident.owner_supplier_id::text ELSE ident.ownership_evidence END;
     IF NEW.owner_key IS DISTINCT FROM expected_owner THEN RAISE EXCEPTION 'Ownership key mismatch' USING ERRCODE='23514'; END IF;
     IF TG_TABLE_NAME<>'inventory_openingcoverage' THEN
       expected_key=encode(sha256(convert_to(ident.id::text||'|'||NEW.location_id::text||'|'||ident.unit_id::text||'|'||expected_owner||'|'||NEW.quality,'UTF8')),'hex');
       IF NEW.balance_key<>expected_key THEN RAISE EXCEPTION 'Custody fingerprint mismatch' USING ERRCODE='23514'; END IF;
     END IF;
   END IF;
 END IF;
 RETURN NEW;
END; $$ LANGUAGE plpgsql;

CREATE FUNCTION navapack_ledger_complete() RETURNS trigger AS $$
DECLARE head inventory_ledgertransaction; ln inventory_transactionline; n integer; expected integer; acct record; total numeric; approval inventory_ledgerapproval;
BEGIN
 IF TG_TABLE_NAME='inventory_sourceevent' THEN
   SELECT * INTO head FROM inventory_ledgertransaction WHERE source_id=NEW.id;
 ELSE SELECT * INTO head FROM inventory_ledgertransaction WHERE id=NEW.id; END IF;
 IF head.id IS NULL THEN RAISE EXCEPTION 'Physical source must commit with one posting' USING ERRCODE='23514'; END IF;
 IF NOT EXISTS(SELECT 1 FROM core_auditevent a JOIN core_auditevidence e ON e.event_id=a.id WHERE a.entity_type='inventory.ledgertransaction' AND a.entity_id=head.id::text AND a.actor_id=head.actor_id AND a.action='inventory.post_synthetic_transaction' AND a.source_version=1) THEN
   RAISE EXCEPTION 'Posting requires its atomic audit event' USING ERRCODE='23514';
 END IF;
 IF NOT EXISTS(SELECT 1 FROM inventory_transactionline WHERE transaction_id=head.id) THEN RAISE EXCEPTION 'Posting needs lines' USING ERRCODE='23514'; END IF;
 IF head.kind IN ('ADJUSTMENT','CORRECTION','REVERSAL') OR EXISTS(SELECT 1 FROM inventory_postingpolicy p WHERE p.id=head.policy_id AND p.rules->'approval_kinds' ? head.kind) THEN
   SELECT * INTO approval FROM inventory_ledgerapproval WHERE id=head.approval_id;
   IF approval.id IS NULL OR approval.maker_id<>head.actor_id OR approval.approver_id=head.actor_id OR approval.decision<>'APPROVED' OR approval.policy_id<>head.policy_id
     OR approval.intent_hash<>(SELECT intent_hash FROM inventory_sourceevent WHERE id=head.source_id) THEN RAISE EXCEPTION 'Exact independent approval is missing' USING ERRCODE='23514'; END IF;
 END IF;
 IF head.kind='REVERSAL' AND (head.reverses_id IS NULL OR EXISTS(SELECT 1 FROM inventory_ledgertransaction WHERE id=head.reverses_id AND kind IN ('OPENING','REVERSAL'))) THEN RAISE EXCEPTION 'Unsupported reversal' USING ERRCODE='23514'; END IF;
 FOR ln IN SELECT * FROM inventory_transactionline WHERE transaction_id=head.id LOOP
   IF ln.quantity=0 AND head.kind<>'OPENING' THEN RAISE EXCEPTION 'Only explicit zero opening is allowed' USING ERRCODE='23514'; END IF;
   IF head.kind='TRANSFER' AND (ln.from_location_id IS NULL OR ln.to_location_id IS NULL) THEN RAISE EXCEPTION 'Unbalanced transfer' USING ERRCODE='23514'; END IF;
   IF head.kind IN ('OPENING','IN','RETURN') AND (ln.from_location_id IS NOT NULL OR ln.to_location_id IS NULL) THEN RAISE EXCEPTION 'Receipt endpoints' USING ERRCODE='23514'; END IF;
   IF head.kind='OUT' AND (ln.from_location_id IS NULL OR ln.to_location_id IS NOT NULL OR ln.quality<>'RELEASED') THEN RAISE EXCEPTION 'Unavailable issue' USING ERRCODE='23514'; END IF;
   expected=CASE WHEN ln.quantity=0 THEN 0 ELSE (ln.from_location_id IS NOT NULL)::int+(ln.to_location_id IS NOT NULL)::int END;
   SELECT count(*) INTO n FROM inventory_ledgerentry WHERE line_id=ln.id;
   IF n<>expected OR EXISTS(SELECT 1 FROM inventory_ledgerentry e WHERE e.line_id=ln.id AND
      (e.transaction_id<>head.id OR e.stock_id<>ln.stock_id OR e.unit_id<>ln.unit_id OR e.event_at<>head.event_at OR e.quality<>ln.quality OR NOT
       ((e.location_id=ln.from_location_id AND e.delta=-ln.quantity) OR (e.location_id=ln.to_location_id AND e.delta=ln.quantity)) IS TRUE)) THEN
     RAISE EXCEPTION 'Ledger entries do not match sealed movement lines' USING ERRCODE='23514';
   END IF;
   IF ln.quantity>0 AND ln.from_location_id IS NOT NULL AND (SELECT count(*) FROM inventory_ledgerentry WHERE line_id=ln.id AND location_id=ln.from_location_id)<>1 THEN RAISE EXCEPTION 'Missing source leg' USING ERRCODE='23514'; END IF;
   IF ln.quantity>0 AND ln.to_location_id IS NOT NULL AND (SELECT count(*) FROM inventory_ledgerentry WHERE line_id=ln.id AND location_id=ln.to_location_id)<>1 THEN RAISE EXCEPTION 'Missing destination leg' USING ERRCODE='23514'; END IF;
   IF EXISTS(SELECT 1 FROM inventory_ledgerentry e WHERE e.line_id=ln.id AND NOT EXISTS(SELECT 1 FROM inventory_openingcoverage c WHERE c.stock_id=e.stock_id AND c.location_id=e.location_id AND c.unit_id=e.unit_id AND c.owner_key=e.owner_key AND c.status='KNOWN')) THEN RAISE EXCEPTION 'Unknown opening coverage' USING ERRCODE='23514'; END IF;
   IF head.kind='OPENING' AND NOT EXISTS(SELECT 1 FROM inventory_openingcoverage c WHERE c.stock_id=ln.stock_id AND c.location_id=ln.to_location_id AND c.transaction_id=head.id AND c.opening_quantity=ln.quantity AND c.status='KNOWN') THEN RAISE EXCEPTION 'Opening coverage mismatch' USING ERRCODE='23514'; END IF;
 END LOOP;
 FOR acct IN SELECT DISTINCT balance_key FROM inventory_ledgerentry WHERE transaction_id=head.id LOOP
   SELECT sum(delta) INTO total FROM inventory_ledgerentry WHERE balance_key=acct.balance_key;
   IF total<0 OR NOT EXISTS(SELECT 1 FROM inventory_balanceprojection b WHERE b.balance_key=acct.balance_key AND b.quantity=total) THEN RAISE EXCEPTION 'Projection differs from immutable ledger' USING ERRCODE='23514'; END IF;
 END LOOP;
 IF head.kind='REVERSAL' AND EXISTS(
   SELECT stock_id,location_id FROM inventory_ledgerentry WHERE transaction_id IN (head.id,head.reverses_id)
   GROUP BY stock_id,location_id HAVING sum(delta)<>0
 ) THEN RAISE EXCEPTION 'Reversal does not compensate original custody' USING ERRCODE='23514'; END IF;
 RETURN NULL;
END; $$ LANGUAGE plpgsql;

CREATE FUNCTION navapack_custody_activity_guard() RETURNS trigger AS $$
BEGIN
 IF TG_TABLE_NAME='inventory_stockidentity' THEN
   IF NEW.lifecycle='RETIRED' AND EXISTS(SELECT 1 FROM inventory_balanceprojection WHERE stock_id=NEW.id AND quantity>0) THEN RAISE EXCEPTION 'Identity retains physical custody' USING ERRCODE='23514'; END IF;
 ELSIF TG_TABLE_NAME='inventory_storagelocation' THEN
   IF NOT NEW.is_active AND EXISTS(SELECT 1 FROM inventory_balanceprojection WHERE location_id=NEW.id AND quantity>0) THEN RAISE EXCEPTION 'Location retains physical custody' USING ERRCODE='23514'; END IF;
 ELSE
   IF NOT NEW.is_active AND EXISTS(SELECT 1 FROM inventory_balanceprojection b JOIN inventory_storagelocation l ON l.id=b.location_id WHERE l.warehouse_id=NEW.id AND b.quantity>0) THEN RAISE EXCEPTION 'Warehouse retains physical custody' USING ERRCODE='23514'; END IF;
 END IF;
 RETURN NEW;
END; $$ LANGUAGE plpgsql;
'''
TABLES=['postingpolicy','sourceevent','ledgerapproval','ledgertransaction','transactionline','ledgerentry','balanceprojection','openingcoverage']
for table in TABLES:
    SQL+=f'CREATE TRIGGER ledger_guard BEFORE INSERT OR UPDATE OR DELETE ON inventory_{table} FOR EACH ROW EXECUTE FUNCTION navapack_ledger_guard();\n'
for table in ['ledgertransaction','sourceevent']:
    SQL+=f'CREATE CONSTRAINT TRIGGER ledger_complete AFTER INSERT ON inventory_{table} DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION navapack_ledger_complete();\n'
for table in ['stockidentity','storagelocation','warehouse']:
    SQL+=f'CREATE TRIGGER ledger_custody_activity_guard BEFORE UPDATE ON inventory_{table} FOR EACH ROW EXECUTE FUNCTION navapack_custody_activity_guard();\n'
REVERSE=''
for table in ['stockidentity','storagelocation','warehouse']:REVERSE+=f'DROP TRIGGER ledger_custody_activity_guard ON inventory_{table};\n'
for table in ['ledgertransaction','sourceevent']:REVERSE+=f'DROP TRIGGER ledger_complete ON inventory_{table};\n'
for table in TABLES:REVERSE+=f'DROP TRIGGER ledger_guard ON inventory_{table};\n'
REVERSE+='DROP FUNCTION navapack_custody_activity_guard(); DROP FUNCTION navapack_ledger_complete(); DROP FUNCTION navapack_ledger_guard();'

class Migration(migrations.Migration):
    dependencies=[('inventory','0006_postingpolicy_ledgerapproval_sourceevent_and_more'),('core','0004_protect_audit_evidence')]
    operations=[migrations.RunSQL(SQL,REVERSE)]
