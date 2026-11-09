from django.db import migrations

# Reemplaza el trigger de UPDATE de la 0015. Ahora las tablas alumnos, tutores y administradores solo tienen
# a quienes cumplen ese rol:
#
# - Al cambiarle el rol a un usuario se crea su fila en el rol nuevo y se borra la del rol anterior.
# - Si como alumno tiene apuntes o puntuaciones, o como tutor tiene clases de apoyo o mensajes, el cambio se
#   RECHAZA con un mensaje claro: esos registros dependen de su rol y no hay que perderlos sin querer.
#   (Hay que borrarlos o pasarlos a otra persona primero.)
# - Sus suscripciones y avisos de alumno, que no sirven para otro rol, se borran junto con su fila.

MSG_ALUMNO = 'No se puede cambiar el rol: como alumno tiene apuntes o puntuaciones. Borralos o reasignalos primero.'
MSG_TUTOR = 'No se puede cambiar el rol: como tutor tiene clases de apoyo o mensajes. Borralos o reasignalos primero.'

BORRAR = 'DROP TRIGGER IF EXISTS usuarios_subtipo_au'

CREAR = f"""
CREATE TRIGGER usuarios_subtipo_au AFTER UPDATE ON usuarios FOR EACH ROW
BEGIN
    DECLARE rol_viejo VARCHAR(30);
    DECLARE rol_nuevo VARCHAR(30);
    IF NEW.rol_id <> OLD.rol_id THEN
        SELECT nombre INTO rol_viejo FROM roles WHERE id = OLD.rol_id;
        SELECT nombre INTO rol_nuevo FROM roles WHERE id = NEW.rol_id;

        IF rol_viejo = 'alumno' AND (EXISTS (SELECT 1 FROM materiales WHERE alumno_id = NEW.legajo)
                                     OR EXISTS (SELECT 1 FROM ponderaciones WHERE alumno_id = NEW.legajo)) THEN
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = '{MSG_ALUMNO}';
        END IF;
        IF rol_viejo = 'tutor' AND (EXISTS (SELECT 1 FROM clases_apoyo WHERE tutor_id = NEW.legajo)
                                    OR EXISTS (SELECT 1 FROM mensajes_clase WHERE tutor_id = NEW.legajo)) THEN
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = '{MSG_TUTOR}';
        END IF;

        IF rol_nuevo = 'alumno' THEN
            INSERT IGNORE INTO alumnos (legajo) VALUES (NEW.legajo);
        ELSEIF rol_nuevo = 'tutor' THEN
            INSERT IGNORE INTO tutores (legajo) VALUES (NEW.legajo);
        ELSEIF rol_nuevo = 'administrador' THEN
            INSERT IGNORE INTO administradores (legajo) VALUES (NEW.legajo);
        END IF;

        IF rol_nuevo <> 'alumno' THEN
            BEGIN
                DECLARE CONTINUE HANDLER FOR SQLEXCEPTION BEGIN END;
                DELETE FROM suscripciones WHERE alumno_id = NEW.legajo;
                DELETE FROM notificaciones WHERE alumno_id = NEW.legajo;
                DELETE FROM alumnos WHERE legajo = NEW.legajo;
            END;
        END IF;
        IF rol_nuevo <> 'tutor' THEN
            BEGIN DECLARE CONTINUE HANDLER FOR SQLEXCEPTION BEGIN END; DELETE FROM tutores WHERE legajo = NEW.legajo; END;
        END IF;
        IF rol_nuevo <> 'administrador' THEN
            BEGIN DECLARE CONTINUE HANDLER FOR SQLEXCEPTION BEGIN END; DELETE FROM administradores WHERE legajo = NEW.legajo; END;
        END IF;
    END IF;
END
"""

# Para volver atrás: el trigger de la 0015 (que conserva la fila vieja en vez de rechazar el cambio).
VIEJO = """
CREATE TRIGGER usuarios_subtipo_au AFTER UPDATE ON usuarios FOR EACH ROW
BEGIN
    DECLARE rol_nuevo VARCHAR(30);
    IF NEW.rol_id <> OLD.rol_id THEN
        SELECT nombre INTO rol_nuevo FROM roles WHERE id = NEW.rol_id;
        IF rol_nuevo = 'alumno' THEN
            INSERT IGNORE INTO alumnos (legajo) VALUES (NEW.legajo);
            BEGIN DECLARE CONTINUE HANDLER FOR SQLEXCEPTION BEGIN END; DELETE FROM tutores WHERE legajo = NEW.legajo; END;
            BEGIN DECLARE CONTINUE HANDLER FOR SQLEXCEPTION BEGIN END; DELETE FROM administradores WHERE legajo = NEW.legajo; END;
        ELSEIF rol_nuevo = 'tutor' THEN
            INSERT IGNORE INTO tutores (legajo) VALUES (NEW.legajo);
            BEGIN DECLARE CONTINUE HANDLER FOR SQLEXCEPTION BEGIN END; DELETE FROM alumnos WHERE legajo = NEW.legajo; END;
            BEGIN DECLARE CONTINUE HANDLER FOR SQLEXCEPTION BEGIN END; DELETE FROM administradores WHERE legajo = NEW.legajo; END;
        ELSEIF rol_nuevo = 'administrador' THEN
            INSERT IGNORE INTO administradores (legajo) VALUES (NEW.legajo);
            BEGIN DECLARE CONTINUE HANDLER FOR SQLEXCEPTION BEGIN END; DELETE FROM alumnos WHERE legajo = NEW.legajo; END;
            BEGIN DECLARE CONTINUE HANDLER FOR SQLEXCEPTION BEGIN END; DELETE FROM tutores WHERE legajo = NEW.legajo; END;
        END IF;
    END IF;
END
"""


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0015_triggers_de_subtipos'),
    ]

    operations = [
        migrations.RunSQL(sql=[BORRAR, CREAR], reverse_sql=[BORRAR, VIEJO]),
    ]
