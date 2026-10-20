from django.db import migrations

SQL = """
CREATE FUNCTION protect_model_revision() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF OLD.sealed THEN RAISE EXCEPTION 'Sealed model revision is immutable'; END IF;
 IF TG_OP = 'DELETE' THEN RETURN OLD; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER immutable_revision BEFORE UPDATE OR DELETE ON specifications_productmodelrevision
 FOR EACH ROW EXECUTE FUNCTION protect_model_revision();
CREATE FUNCTION protect_revision_line() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE rid uuid; locked boolean;
BEGIN
 IF TG_OP = 'INSERT' THEN rid := NEW.revision_id; ELSE rid := OLD.revision_id; END IF;
 SELECT sealed INTO locked FROM specifications_productmodelrevision WHERE id = rid FOR UPDATE;
 IF locked THEN RAISE EXCEPTION 'Sealed revision lines are immutable'; END IF;
 IF TG_OP = 'UPDATE' AND NEW.revision_id <> OLD.revision_id THEN RAISE EXCEPTION 'Cannot move revision line'; END IF;
 IF TG_OP = 'DELETE' THEN RETURN OLD; END IF;
 RETURN NEW;
END $$;
"""
for table in ['recipeline','processcostline','modelroutestage']:
    SQL += f'CREATE TRIGGER immutable_revision_line BEFORE INSERT OR UPDATE OR DELETE ON specifications_{table} FOR EACH ROW EXECUTE FUNCTION protect_revision_line();'
REVERSE = ''.join(f'DROP TRIGGER immutable_revision_line ON specifications_{t};' for t in ['recipeline','processcostline','modelroutestage']) + 'DROP FUNCTION protect_revision_line(); DROP TRIGGER immutable_revision ON specifications_productmodelrevision; DROP FUNCTION protect_model_revision();'
class Migration(migrations.Migration):
    dependencies = [('specifications','0002_modelroutestage_modelroutestage_expected_input_range_and_more')]
    operations = [migrations.RunSQL(SQL, REVERSE)]
