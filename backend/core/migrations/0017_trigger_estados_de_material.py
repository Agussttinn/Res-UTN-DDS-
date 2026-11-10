from django.db import migrations

# Trigger que cuida los estados de un apunte aunque el cambio no venga de la app (DBeaver, SQL a mano...):
#
# - Solo se permiten las transiciones que existen en la aplicación:
#       pendiente -> aprobado | rechazado
#       aprobado  -> pendiente | rechazado | archivado
#       rechazado -> pendiente            (el autor lo corrige y lo reenvía)
#   Un archivado es definitivo. Cualquier otro cambio se RECHAZA con un mensaje claro.
# - El motivo del rechazo solo tiene sentido mientras el apunte está rechazado: al pasar a cualquier otro estado
#   se borra solo, para que no quede un motivo viejo.

MENSAJE = 'Cambio de estado no permitido. Se puede: pendiente a aprobado o rechazado; aprobado a pendiente, rechazado o archivado; rechazado a pendiente.'

BORRAR = 'DROP TRIGGER IF EXISTS materiales_estado_bu'

CREAR = f"""
CREATE TRIGGER materiales_estado_bu BEFORE UPDATE ON materiales FOR EACH ROW
BEGIN
    DECLARE estado_viejo VARCHAR(30);
    DECLARE estado_nuevo VARCHAR(30);
    IF NEW.estado_id <> OLD.estado_id THEN
        SELECT nombre INTO estado_viejo FROM estados_material WHERE id = OLD.estado_id;
        SELECT nombre INTO estado_nuevo FROM estados_material WHERE id = NEW.estado_id;

        IF NOT ((estado_viejo = 'pendiente' AND estado_nuevo IN ('aprobado', 'rechazado'))
                OR (estado_viejo = 'aprobado' AND estado_nuevo IN ('pendiente', 'rechazado', 'archivado'))
                OR (estado_viejo = 'rechazado' AND estado_nuevo = 'pendiente')) THEN
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = '{MENSAJE}';
        END IF;

        IF estado_nuevo <> 'rechazado' THEN
            SET NEW.motivo_rechazo = NULL;
        END IF;
    END IF;
END
"""


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0016_triggers_cambio_de_rol_estricto'),
    ]

    operations = [
        migrations.RunSQL(sql=[BORRAR, CREAR], reverse_sql=[BORRAR]),
    ]
