from django.db import migrations
SQL = """
CREATE FUNCTION protect_import_batch() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF TG_OP='DELETE' THEN RAISE EXCEPTION 'Import evidence cannot be deleted'; END IF;
 IF OLD.status='applied' THEN RAISE EXCEPTION 'Applied import is immutable'; END IF;
 IF (NEW.filename, NEW.digest, NEW.source_system, NEW.source_kind, NEW.target, NEW.source_attestation, NEW.created_by_id)
 IS DISTINCT FROM (OLD.filename, OLD.digest, OLD.source_system, OLD.source_kind, OLD.target, OLD.source_attestation, OLD.created_by_id)
 THEN RAISE EXCEPTION 'Import source evidence is immutable'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER immutable_import_batch BEFORE UPDATE OR DELETE ON imports_importbatch FOR EACH ROW EXECUTE FUNCTION protect_import_batch();
CREATE FUNCTION protect_import_row() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF TG_OP='DELETE' THEN RAISE EXCEPTION 'Source rows cannot be deleted'; END IF;
 IF (NEW.batch_id,NEW.sheet,NEW.row_number,NEW.raw) IS DISTINCT FROM (OLD.batch_id,OLD.sheet,OLD.row_number,OLD.raw)
 THEN RAISE EXCEPTION 'Source rows are immutable'; END IF;
 IF OLD.result_id IS NOT NULL OR (SELECT status FROM imports_importbatch WHERE id=OLD.batch_id) <> 'reviewed'
 THEN RAISE EXCEPTION 'Import row cannot be changed'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER immutable_import_row BEFORE UPDATE OR DELETE ON imports_importrow FOR EACH ROW EXECUTE FUNCTION protect_import_row();
"""
class Migration(migrations.Migration):
    dependencies = [('imports','0001_initial')]
    operations = [migrations.RunSQL(SQL, 'DROP TRIGGER immutable_import_row ON imports_importrow; DROP FUNCTION protect_import_row(); DROP TRIGGER immutable_import_batch ON imports_importbatch; DROP FUNCTION protect_import_batch();')]
