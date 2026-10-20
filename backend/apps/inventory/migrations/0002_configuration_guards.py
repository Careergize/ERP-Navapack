from django.db import migrations

SQL = r'''
CREATE FUNCTION navapack_inventory_guard() RETURNS trigger AS $$
DECLARE p inventory_storagelocation; s inventory_stockidentity; expected_unit uuid;
BEGIN
  PERFORM pg_advisory_xact_lock(70462030);
  IF TG_OP = 'DELETE' THEN
    RAISE EXCEPTION 'Inventory configuration history cannot be deleted' USING ERRCODE='23514';
  END IF;
  IF TG_TABLE_NAME = 'inventory_warehousescope' THEN
    IF TG_OP = 'UPDATE' THEN RAISE EXCEPTION 'Scope evidence is immutable' USING ERRCODE='23514'; END IF;
    IF NEW.expires_at <= NEW.created_at THEN RAISE EXCEPTION 'Scope expiry must follow creation' USING ERRCODE='23514'; END IF;
    RETURN NEW;
  END IF;
  IF TG_OP = 'UPDATE' AND (NEW.id <> OLD.id OR NEW.created_by_id <> OLD.created_by_id OR NEW.created_at <> OLD.created_at) THEN
    RAISE EXCEPTION 'Creation identity is immutable' USING ERRCODE='23514';
  END IF;
  IF TG_TABLE_NAME = 'inventory_warehouse' THEN
    IF NOT NEW.is_active AND (EXISTS (SELECT 1 FROM inventory_storagelocation WHERE warehouse_id=NEW.id AND is_active)
      OR EXISTS (SELECT 1 FROM inventory_stockidentity WHERE warehouse_id=NEW.id AND lifecycle='REGISTERED')) THEN
      RAISE EXCEPTION 'Retire identities and deactivate locations first' USING ERRCODE='23514';
    END IF;
  ELSIF TG_TABLE_NAME = 'inventory_storagelocation' THEN
    IF TG_OP='UPDATE' AND NEW.warehouse_id <> OLD.warehouse_id THEN RAISE EXCEPTION 'Warehouse is immutable' USING ERRCODE='23514'; END IF;
    IF NEW.is_active AND NOT EXISTS (SELECT 1 FROM inventory_warehouse WHERE id=NEW.warehouse_id AND is_active) THEN
      RAISE EXCEPTION 'Inactive warehouse' USING ERRCODE='23514';
    END IF;
    IF NEW.parent_id IS NOT NULL THEN
      SELECT * INTO p FROM inventory_storagelocation WHERE id=NEW.parent_id;
      IF p.warehouse_id <> NEW.warehouse_id OR (NEW.is_active AND NOT p.is_active) THEN RAISE EXCEPTION 'Invalid parent scope/status' USING ERRCODE='23514'; END IF;
      IF EXISTS (WITH RECURSIVE ancestors AS (
        SELECT id,parent_id FROM inventory_storagelocation WHERE id=NEW.parent_id
        UNION SELECT l.id,l.parent_id FROM inventory_storagelocation l JOIN ancestors a ON l.id=a.parent_id
      ) SELECT 1 FROM ancestors WHERE id=NEW.id) THEN RAISE EXCEPTION 'Location cycle' USING ERRCODE='23514'; END IF;
    END IF;
    IF NOT NEW.is_active AND (EXISTS(SELECT 1 FROM inventory_storagelocation WHERE parent_id=NEW.id AND is_active)
      OR EXISTS(SELECT 1 FROM inventory_stockidentity WHERE location_id=NEW.id AND lifecycle='REGISTERED')) THEN
      RAISE EXCEPTION 'Active dependents' USING ERRCODE='23514';
    END IF;
  ELSE
    IF TG_OP='UPDATE' AND (to_jsonb(NEW) - ARRAY['version','updated_at','lifecycle']) IS DISTINCT FROM (to_jsonb(OLD) - ARRAY['version','updated_at','lifecycle']) THEN
      RAISE EXCEPTION 'Stock identity is immutable' USING ERRCODE='23514';
    END IF;
    IF TG_OP='UPDATE' AND OLD.lifecycle='RETIRED' AND NEW.lifecycle<>'RETIRED' THEN RAISE EXCEPTION 'Retirement is terminal' USING ERRCODE='23514'; END IF;
    IF TG_OP='INSERT' THEN
      IF NEW.reference <> 'STK-' || upper(replace(NEW.id::text,'-','')) THEN RAISE EXCEPTION 'Invalid generated reference' USING ERRCODE='23514'; END IF;
      IF NOT EXISTS (SELECT 1 FROM inventory_warehouse WHERE id=NEW.warehouse_id AND is_active) THEN RAISE EXCEPTION 'Inactive warehouse' USING ERRCODE='23514'; END IF;
      IF NEW.location_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM inventory_storagelocation WHERE id=NEW.location_id AND warehouse_id=NEW.warehouse_id AND is_active) THEN RAISE EXCEPTION 'Invalid location' USING ERRCODE='23514'; END IF;
      IF NEW.material_id IS NOT NULL THEN SELECT unit_id INTO expected_unit FROM masters_material WHERE id=NEW.material_id AND is_active;
      ELSIF NEW.variant_id IS NOT NULL THEN SELECT unit_id INTO expected_unit FROM masters_productvariant WHERE id=NEW.variant_id AND is_active;
      ELSE SELECT unit_id INTO expected_unit FROM masters_consumable WHERE id=NEW.consumable_id AND is_active; END IF;
      IF expected_unit IS NULL OR expected_unit <> NEW.unit_id THEN RAISE EXCEPTION 'Item unit mismatch' USING ERRCODE='23514'; END IF;
      IF NOT EXISTS (SELECT 1 FROM masters_unit WHERE id=NEW.unit_id AND is_active) THEN RAISE EXCEPTION 'Inactive unit' USING ERRCODE='23514'; END IF;
      IF NEW.parent_id IS NOT NULL THEN
        SELECT * INTO s FROM inventory_stockidentity WHERE id=NEW.parent_id;
        IF s.id IS NULL OR s.lifecycle <> 'REGISTERED' OR
          ROW(NEW.warehouse_id,NEW.material_id,NEW.variant_id,NEW.consumable_id,NEW.unit_id,NEW.ownership,NEW.owner_customer_id,NEW.owner_supplier_id,NEW.ownership_evidence)
          IS DISTINCT FROM ROW(s.warehouse_id,s.material_id,s.variant_id,s.consumable_id,s.unit_id,s.ownership,s.owner_customer_id,s.owner_supplier_id,s.ownership_evidence)
        THEN RAISE EXCEPTION 'Parent identity mismatch' USING ERRCODE='23514'; END IF;
      END IF;
    END IF;
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;
CREATE TRIGGER inventory_warehouse_guard BEFORE INSERT OR UPDATE OR DELETE ON inventory_warehouse FOR EACH ROW EXECUTE FUNCTION navapack_inventory_guard();
CREATE TRIGGER inventory_location_guard BEFORE INSERT OR UPDATE OR DELETE ON inventory_storagelocation FOR EACH ROW EXECUTE FUNCTION navapack_inventory_guard();
CREATE TRIGGER inventory_identity_guard BEFORE INSERT OR UPDATE OR DELETE ON inventory_stockidentity FOR EACH ROW EXECUTE FUNCTION navapack_inventory_guard();
CREATE TRIGGER inventory_scope_guard BEFORE INSERT OR UPDATE OR DELETE ON inventory_warehousescope FOR EACH ROW EXECUTE FUNCTION navapack_inventory_guard();
'''
REVERSE = '''
DROP TRIGGER inventory_scope_guard ON inventory_warehousescope;
DROP TRIGGER inventory_identity_guard ON inventory_stockidentity;
DROP TRIGGER inventory_location_guard ON inventory_storagelocation;
DROP TRIGGER inventory_warehouse_guard ON inventory_warehouse;
DROP FUNCTION navapack_inventory_guard();
'''

class Migration(migrations.Migration):
    dependencies=[('inventory','0001_initial')]
    operations=[migrations.RunSQL(SQL,REVERSE)]
