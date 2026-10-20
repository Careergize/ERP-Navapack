from django.db import migrations

SQL = """
CREATE FUNCTION protect_import_row_insert() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE state text;
BEGIN
 SELECT status INTO state FROM imports_importbatch WHERE id=NEW.batch_id FOR UPDATE;
 IF state <> 'staged' THEN RAISE EXCEPTION 'Cannot append to reviewed import source'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER immutable_import_row_insert BEFORE INSERT ON imports_importrow FOR EACH ROW EXECUTE FUNCTION protect_import_row_insert();
"""
class Migration(migrations.Migration):
    dependencies=[('imports','0002_preserve_source_evidence')]
    operations=[migrations.RunSQL(SQL,'DROP TRIGGER immutable_import_row_insert ON imports_importrow; DROP FUNCTION protect_import_row_insert();')]
