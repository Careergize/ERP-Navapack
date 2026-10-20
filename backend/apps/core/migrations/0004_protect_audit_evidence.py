from django.db import migrations

class Migration(migrations.Migration):
    dependencies=[('core','0003_auditevidence')]
    operations=[migrations.RunSQL('''
CREATE TRIGGER audit_evidence_no_mutation BEFORE UPDATE OR DELETE ON core_auditevidence
FOR EACH ROW EXECUTE FUNCTION navapack_audit_immutable();
ALTER TABLE core_auditevidence ADD CONSTRAINT audit_evidence_storage_bound CHECK (octet_length(payload::text)<=524288);
''','''
ALTER TABLE core_auditevidence DROP CONSTRAINT audit_evidence_storage_bound;
DROP TRIGGER audit_evidence_no_mutation ON core_auditevidence;
''')]
