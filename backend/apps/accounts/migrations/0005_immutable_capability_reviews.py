from django.db import migrations

SQL = """
CREATE FUNCTION protect_capability_revision() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF TG_OP='DELETE' THEN RAISE EXCEPTION 'Capability reviews cannot be deleted'; END IF;
 IF OLD.status <> 'pending' THEN RAISE EXCEPTION 'Completed capability review is immutable'; END IF;
 IF (NEW.role_id,NEW.permission_codes,NEW.requires_independent_approval,NEW.expected_role_version,NEW.baseline,NEW.requested_by_id,NEW.created_at)
 IS DISTINCT FROM (OLD.role_id,OLD.permission_codes,OLD.requires_independent_approval,OLD.expected_role_version,OLD.baseline,OLD.requested_by_id,OLD.created_at)
 THEN RAISE EXCEPTION 'Capability proposal is immutable'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER immutable_capability_review BEFORE UPDATE OR DELETE ON accounts_rolecapabilityrevision
FOR EACH ROW EXECUTE FUNCTION protect_capability_revision();
"""


class Migration(migrations.Migration):
    dependencies = [('accounts','0004_alter_role_options_role_governed_role_updated_at_and_more')]
    operations = [migrations.RunSQL(SQL, 'DROP TRIGGER immutable_capability_review ON accounts_rolecapabilityrevision; DROP FUNCTION protect_capability_revision();')]
