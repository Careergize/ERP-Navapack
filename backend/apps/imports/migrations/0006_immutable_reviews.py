from django.db import migrations

SQL = """
CREATE FUNCTION protect_import_review() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'Canonical import reviews are append-only'; END $$;
CREATE TRIGGER immutable_import_review BEFORE UPDATE OR DELETE ON imports_importreview
FOR EACH ROW EXECUTE FUNCTION protect_import_review();
"""


class Migration(migrations.Migration):
    dependencies = [('imports','0005_importbatch_applied_plan_importreview_and_more')]
    operations = [migrations.RunSQL(SQL, 'DROP TRIGGER immutable_import_review ON imports_importreview; DROP FUNCTION protect_import_review();')]
