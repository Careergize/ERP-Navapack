from django.db import migrations

FORWARD = """
CREATE FUNCTION navapack_audit_immutable() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'Audit events are append-only';
END;
$$ LANGUAGE plpgsql;
CREATE TRIGGER audit_no_mutation BEFORE UPDATE OR DELETE ON core_auditevent
FOR EACH ROW EXECUTE FUNCTION navapack_audit_immutable();
"""
REVERSE = """
DROP TRIGGER audit_no_mutation ON core_auditevent;
DROP FUNCTION navapack_audit_immutable();
"""


class Migration(migrations.Migration):
    dependencies = [('core', '0001_initial')]
    operations = [migrations.RunSQL(FORWARD, REVERSE)]
