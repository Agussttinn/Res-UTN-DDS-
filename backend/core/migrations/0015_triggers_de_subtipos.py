from django.db import migrations

# Triggers de MariaDB: mantienen alumnos, tutores y administradores alineados con usuarios.rol_id sin importar
# desde dónde se cambie el rol (la app, el panel de Django, DBeaver, un UPDATE a mano...).
#
# - Al crear un usuario o cambiarle el rol se crea su fila en la tabla del rol nuevo.
# - Al cambiarle el rol se intenta borrar su fila de los otros roles; si esa fila tiene registros asociados
#   (materiales, clases, etc.) la base lo impide y la fila se conserva, sin cortar el cambio de rol.

CREAR = [
    """
    CREATE TRIGGER usuarios_subtipo_ai AFTER INSERT ON usuarios FOR EACH ROW
    BEGIN
        DECLARE rol_nuevo VARCHAR(30);
        SELECT nombre INTO rol_nuevo FROM roles WHERE id = NEW.rol_id;
        IF rol_nuevo = 'alumno' THEN
            INSERT IGNORE INTO alumnos (legajo) VALUES (NEW.legajo);
        ELSEIF rol_nuevo = 'tutor' THEN
            INSERT IGNORE INTO tutores (legajo) VALUES (NEW.legajo);
        ELSEIF rol_nuevo = 'administrador' THEN
            INSERT IGNORE INTO administradores (legajo) VALUES (NEW.legajo);
        END IF;
    END
    """,
    """
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
    """,
]

BORRAR = [
    'DROP TRIGGER IF EXISTS usuarios_subtipo_au',
    'DROP TRIGGER IF EXISTS usuarios_subtipo_ai',
]


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0014_claves_hacia_alumnos_y_tutores'),
    ]

    operations = [
        # Cada sentencia va como un elemento de la lista para que Django no las parta en los ";" de adentro.
        migrations.RunSQL(sql=BORRAR + CREAR, reverse_sql=BORRAR),
    ]
