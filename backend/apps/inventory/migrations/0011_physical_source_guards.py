from django.db import migrations
SQL=r'''
CREATE FUNCTION navapack_physical_source_contract() RETURNS trigger AS $$
DECLARE doc inventory_physicalsourcedocument; src inventory_physicalsourceline; req inventory_operationrequest; ident inventory_stockidentity;
BEGIN
 IF TG_TABLE_NAME='inventory_physicalsourceline' THEN
  SELECT * INTO doc FROM inventory_physicalsourcedocument WHERE id=NEW.document_id;
  SELECT * INTO ident FROM inventory_stockidentity WHERE id=NEW.stock_id;
  IF NEW.unit_id IS DISTINCT FROM ident.unit_id OR NOT EXISTS(SELECT 1 FROM inventory_storagelocation WHERE id=NEW.location_id AND warehouse_id=doc.warehouse_id) THEN RAISE EXCEPTION 'Physical source unit/custody mismatch' USING ERRCODE='23514'; END IF;
 ELSIF TG_TABLE_NAME='inventory_operationrequest' THEN
  IF TG_OP='UPDATE' AND NEW.cutoff_basis IS DISTINCT FROM OLD.cutoff_basis THEN RAISE EXCEPTION 'Cutoff basis is immutable' USING ERRCODE='23514'; END IF;
  IF TG_OP='INSERT' THEN
   IF NEW.kind IN ('COUNT','OPENING') AND (NEW.cutoff_basis<>'CURRENT_LOCKED' OR NEW.cutoff<transaction_timestamp() OR NEW.cutoff>clock_timestamp()) THEN RAISE EXCEPTION 'Historical/custom count cutoff unsupported' USING ERRCODE='23514'; END IF;
   IF NEW.kind NOT IN ('COUNT','OPENING') AND NEW.cutoff_basis<>'EVIDENCE_ONLY' THEN RAISE EXCEPTION 'Explicit physical evidence basis required' USING ERRCODE='23514'; END IF;
  END IF;
 ELSE
  SELECT * INTO req FROM inventory_operationrequest WHERE id=NEW.request_id;
  IF req.kind IN ('IN','COUNT','OPENING') THEN
   SELECT * INTO src FROM inventory_physicalsourceline WHERE id=NEW.source_line_id;
   SELECT * INTO doc FROM inventory_physicalsourcedocument WHERE id=src.document_id;
   IF src.id IS NULL OR doc.namespace IS DISTINCT FROM req.source_system OR doc.reference IS DISTINCT FROM req.source_reference OR doc.warehouse_id IS DISTINCT FROM req.warehouse_id
     OR doc.kind IS DISTINCT FROM (CASE WHEN req.kind='IN' THEN 'RECEIPT' ELSE 'COUNT' END)
     OR ROW(src.stock_id,src.location_id,src.unit_id,src.quantity) IS DISTINCT FROM ROW(NEW.stock_id,NEW.location_id,NEW.unit_id,NEW.quantity) THEN
    RAISE EXCEPTION 'Pre-registered matching physical source line required' USING ERRCODE='23514';
   END IF;
  ELSIF NEW.source_line_id IS NOT NULL THEN RAISE EXCEPTION 'Unexpected physical source claim' USING ERRCODE='23514'; END IF;
 END IF;
 RETURN NEW;
END; $$ LANGUAGE plpgsql;
CREATE TRIGGER physical_registry_immutable BEFORE INSERT OR UPDATE OR DELETE ON inventory_physicalsourcedocument FOR EACH ROW EXECUTE FUNCTION navapack_ledger_guard();
CREATE TRIGGER physical_registry_immutable BEFORE INSERT OR UPDATE OR DELETE ON inventory_physicalsourceline FOR EACH ROW EXECUTE FUNCTION navapack_ledger_guard();
CREATE TRIGGER physical_source_contract BEFORE INSERT ON inventory_physicalsourceline FOR EACH ROW EXECUTE FUNCTION navapack_physical_source_contract();
CREATE TRIGGER physical_source_contract BEFORE INSERT ON inventory_operationline FOR EACH ROW EXECUTE FUNCTION navapack_physical_source_contract();
CREATE TRIGGER physical_source_contract BEFORE INSERT OR UPDATE ON inventory_operationrequest FOR EACH ROW EXECUTE FUNCTION navapack_physical_source_contract();
'''
REVERSE='''
DROP TRIGGER physical_source_contract ON inventory_operationrequest;
DROP TRIGGER physical_source_contract ON inventory_operationline;
DROP TRIGGER physical_source_contract ON inventory_physicalsourceline;
DROP TRIGGER physical_registry_immutable ON inventory_physicalsourceline;
DROP TRIGGER physical_registry_immutable ON inventory_physicalsourcedocument;
DROP FUNCTION navapack_physical_source_contract();
'''
class Migration(migrations.Migration):
 dependencies=[('inventory','0010_operationrequest_cutoff_basis_physicalsourcedocument_and_more')]
 operations=[migrations.RunSQL(SQL,REVERSE)]
