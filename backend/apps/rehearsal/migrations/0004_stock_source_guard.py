from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [('rehearsal', '0003_rehearsaljob_costing_revision_and_more')]
    operations = [migrations.RunSQL(r'''
CREATE FUNCTION navapack_rehearsal_source_guard() RETURNS trigger AS $$
BEGIN
 IF TG_OP='UPDATE' AND NEW.costing_revision_id IS DISTINCT FROM OLD.costing_revision_id THEN
   RAISE EXCEPTION 'Immutable stock costing source' USING ERRCODE='23514';
 END IF;
 IF TG_OP='INSERT' AND NOT EXISTS (
   SELECT 1 FROM commercial_commercialrevision r JOIN commercial_commercialdocument d ON d.id=r.document_id
   WHERE r.id=COALESCE(NEW.sales_order_revision_id,NEW.costing_revision_id) AND d.owner_id=NEW.owner_id
   AND d.kind=CASE WHEN NEW.sales_order_revision_id IS NULL THEN 'COSTING' ELSE 'SALES_ORDER' END
   AND r.snapshot=NEW.snapshot->'source'
 ) THEN
   RAISE EXCEPTION 'Exact owned commercial source required' USING ERRCODE='23514';
 END IF;
 IF NEW.costing_revision_id IS NOT NULL AND NEW.status='DISPATCHED' THEN
   RAISE EXCEPTION 'Stock production cannot dispatch to a customer' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END; $$ LANGUAGE plpgsql;
CREATE TRIGGER rehearsal_stock_source_guard BEFORE INSERT OR UPDATE ON rehearsal_rehearsaljob
 FOR EACH ROW EXECUTE FUNCTION navapack_rehearsal_source_guard();
''', '''DROP TRIGGER rehearsal_stock_source_guard ON rehearsal_rehearsaljob;
DROP FUNCTION navapack_rehearsal_source_guard();''')]
