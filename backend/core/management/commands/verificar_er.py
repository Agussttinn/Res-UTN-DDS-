"""Compara la base de datos REAL con el diagrama Entidad-Relación del proyecto.

Revisa tablas, columnas, claves primarias, claves foráneas, triggers y que cada usuario esté en la tabla de su
rol (y solo en esa). Muestra un ✔ o un ✘ por cada punto y, si algo no coincide, termina con error (código 1).
Solo lee: no modifica nada. Se puede correr las veces que haga falta:

    python manage.py verificar_er
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import connection

# El diagrama E-R: tabla -> columnas (con la clave primaria marcada aparte).
TABLAS = {
    'roles': {'pk': 'id', 'columnas': ['id', 'nombre']},
    'estados_material': {'pk': 'id', 'columnas': ['id', 'nombre']},
    'especialidades': {'pk': 'id', 'columnas': ['id', 'nombre', 'codigo_sysacad']},
    'materias': {'pk': 'id', 'columnas': ['id', 'nombre', 'anio', 'especialidad_id', 'id_sysacad', 'electiva']},
    'usuarios': {'pk': 'legajo', 'columnas': ['legajo', 'nombre_y_apellido', 'correo', 'contraseña', 'rol_id']},
    'alumnos': {'pk': 'legajo', 'columnas': ['legajo']},
    'tutores': {'pk': 'legajo', 'columnas': ['legajo']},
    'administradores': {'pk': 'legajo', 'columnas': ['legajo']},
    'materiales': {'pk': 'id', 'columnas': [
        'id', 'titulo', 'fecha_de_carga', 'tipo', 'comentario', 'archivo', 'materia_id', 'alumno_id', 'estado_id',
        'cantidad_ponderaciones', 'promedio_ponderacion', 'motivo_rechazo']},
    'ponderaciones': {'pk': 'id', 'columnas': ['id', 'valor', 'fecha', 'material_id', 'alumno_id']},
    'clases_apoyo': {'pk': 'id', 'columnas': ['id', 'dia', 'hora_inicio', 'hora_fin', 'aula', 'materia_id', 'tutor_id']},
    'suscripciones': {'pk': 'id', 'columnas': ['id', 'fecha', 'clase_id', 'alumno_id']},
    'mensajes_clase': {'pk': 'id', 'columnas': ['id', 'texto', 'fecha', 'clase_id', 'tutor_id']},
    'notificaciones': {'pk': 'id', 'columnas': ['id', 'tipo', 'titulo', 'texto', 'fecha', 'leida', 'clase_id', 'alumno_id']},
}

# Las relaciones del diagrama: (tabla, columna) -> (tabla referenciada, columna referenciada).
RELACIONES = {
    ('usuarios', 'rol_id'): ('roles', 'id'),
    ('alumnos', 'legajo'): ('usuarios', 'legajo'),
    ('tutores', 'legajo'): ('usuarios', 'legajo'),
    ('administradores', 'legajo'): ('usuarios', 'legajo'),
    ('materias', 'especialidad_id'): ('especialidades', 'id'),
    ('materiales', 'materia_id'): ('materias', 'id'),
    ('materiales', 'alumno_id'): ('alumnos', 'legajo'),
    ('materiales', 'estado_id'): ('estados_material', 'id'),
    ('ponderaciones', 'material_id'): ('materiales', 'id'),
    ('ponderaciones', 'alumno_id'): ('alumnos', 'legajo'),
    ('clases_apoyo', 'materia_id'): ('materias', 'id'),
    ('clases_apoyo', 'tutor_id'): ('tutores', 'legajo'),
    ('suscripciones', 'clase_id'): ('clases_apoyo', 'id'),
    ('suscripciones', 'alumno_id'): ('alumnos', 'legajo'),
    ('mensajes_clase', 'clase_id'): ('clases_apoyo', 'id'),
    ('mensajes_clase', 'tutor_id'): ('tutores', 'legajo'),
    ('notificaciones', 'clase_id'): ('clases_apoyo', 'id'),
    ('notificaciones', 'alumno_id'): ('alumnos', 'legajo'),
}

# Triggers que mantienen la integridad dentro de la propia base: nombre -> (tabla, momento, evento).
TRIGGERS = {
    'usuarios_subtipo_ai': ('usuarios', 'AFTER', 'INSERT'),
    'usuarios_subtipo_au': ('usuarios', 'AFTER', 'UPDATE'),
    'materiales_estado_bu': ('materiales', 'BEFORE', 'UPDATE'),
}

SUBTIPOS = {'alumno': 'alumnos', 'tutor': 'tutores', 'administrador': 'administradores'}

# Tablas propias de Django (migraciones, sesiones, panel de administración): no forman parte del diagrama.
PREFIJOS_DE_DJANGO = ('django_', 'auth_')


class Command(BaseCommand):
    help = 'Verifica que la base de datos real coincida con el diagrama Entidad-Relación.'

    def handle(self, *args, **options):
        self.errores = 0
        with connection.cursor() as cursor:
            self.cursor = cursor
            self.stdout.write(self.style.MIGRATE_HEADING(f'Base de datos: {connection.settings_dict["NAME"]}\n'))
            self._tablas_y_columnas()
            self._relaciones()
            self._triggers()
            self._roles_de_los_usuarios()

        self.stdout.write('')
        if self.errores:
            raise CommandError(f'La base NO coincide con el diagrama: {self.errores} diferencia(s).')
        self.stdout.write(self.style.SUCCESS('✔ La base de datos coincide con el diagrama Entidad-Relación.'))

    # ---- utilidades de salida

    def _ok(self, texto):
        self.stdout.write(self.style.SUCCESS(f'  ✔ {texto}'))

    def _mal(self, texto):
        self.errores += 1
        self.stdout.write(self.style.ERROR(f'  ✘ {texto}'))

    def _titulo(self, texto):
        self.stdout.write(self.style.MIGRATE_LABEL(f'\n{texto}'))

    def _consultar(self, sql, *params):
        self.cursor.execute(sql, list(params))
        return self.cursor.fetchall()

    # ---- chequeos

    def _tablas_y_columnas(self):
        self._titulo('1. Tablas, columnas y claves primarias')
        reales = {fila[0] for fila in self._consultar(
            'SELECT table_name FROM information_schema.tables WHERE table_schema = DATABASE() AND table_type = %s',
            'BASE TABLE')}
        columnas = {}
        for tabla, columna, clave in self._consultar(
                'SELECT table_name, column_name, column_key FROM information_schema.columns WHERE table_schema = DATABASE()'):
            columnas.setdefault(tabla, {})[columna] = clave

        for tabla, definicion in TABLAS.items():
            if tabla not in reales:
                self._mal(f'falta la tabla {tabla}')
                continue
            tiene = columnas.get(tabla, {})
            faltan = [c for c in definicion['columnas'] if c not in tiene]
            sobran = [c for c in tiene if c not in definicion['columnas']]
            if faltan:
                self._mal(f'{tabla}: faltan las columnas {", ".join(faltan)}')
            if sobran:
                self._mal(f'{tabla}: hay columnas que no están en el diagrama: {", ".join(sobran)}')
            if tiene.get(definicion['pk']) != 'PRI':
                self._mal(f'{tabla}: {definicion["pk"]} debería ser la clave primaria')
            if not (faltan or sobran) and tiene.get(definicion['pk']) == 'PRI':
                self._ok(f'{tabla} ({len(definicion["columnas"])} columna(s), PK {definicion["pk"]})')

        extras = sorted(t for t in reales if t not in TABLAS and not t.startswith(PREFIJOS_DE_DJANGO))
        for tabla in extras:
            self._mal(f'hay una tabla que no está en el diagrama: {tabla}')

    def _relaciones(self):
        self._titulo('2. Claves foráneas (relaciones)')
        reales = {
            (tabla, columna): (destino, columna_destino)
            for tabla, columna, destino, columna_destino in self._consultar(
                'SELECT table_name, column_name, referenced_table_name, referenced_column_name '
                'FROM information_schema.key_column_usage '
                'WHERE table_schema = DATABASE() AND referenced_table_name IS NOT NULL')
        }
        for (tabla, columna), (destino, columna_destino) in RELACIONES.items():
            real = reales.get((tabla, columna))
            texto = f'{tabla}.{columna} → {destino}.{columna_destino}'
            if real is None:
                self._mal(f'{texto}: no existe la clave foránea')
            elif real != (destino, columna_destino):
                self._mal(f'{tabla}.{columna} apunta a {real[0]}.{real[1]} y el diagrama dice {destino}.{columna_destino}')
            else:
                self._ok(texto)
        for (tabla, columna), (destino, columna_destino) in sorted(reales.items()):
            if tabla in TABLAS and (tabla, columna) not in RELACIONES:
                self._mal(f'{tabla}.{columna} → {destino}.{columna_destino}: no está en el diagrama')

    def _triggers(self):
        self._titulo('3. Triggers')
        reales = {
            nombre: (tabla, momento, evento)
            for nombre, tabla, momento, evento in self._consultar(
                'SELECT trigger_name, event_object_table, action_timing, event_manipulation '
                'FROM information_schema.triggers WHERE trigger_schema = DATABASE()')
        }
        for nombre, esperado in TRIGGERS.items():
            texto = f'{nombre} ({esperado[1]} {esperado[2]} en {esperado[0]})'
            if nombre not in reales:
                self._mal(f'{texto}: no existe (falta aplicar las migraciones: python manage.py migrate)')
            elif reales[nombre] != esperado:
                self._mal(f'{nombre} existe pero está en {reales[nombre]} y se esperaba {esperado}')
            else:
                self._ok(texto)

    def _roles_de_los_usuarios(self):
        self._titulo('4. Cada usuario está en la tabla de su rol, y solo en esa')
        usuarios = self._consultar('SELECT u.legajo, u.nombre_y_apellido, r.nombre FROM usuarios u JOIN roles r ON r.id = u.rol_id')
        tablas = {
            tabla: {fila[0] for fila in self._consultar(f'SELECT legajo FROM {tabla}')}
            for tabla in SUBTIPOS.values()
        }
        for rol, tabla in SUBTIPOS.items():
            self.stdout.write(f'    {tabla}: {len(tablas[tabla])} fila(s)')

        problemas = 0
        for legajo, nombre, rol in usuarios:
            esperada = SUBTIPOS.get(rol)
            if esperada is None:
                self._mal(f'{legajo} ({nombre}) tiene un rol desconocido: {rol}')
                problemas += 1
                continue
            if legajo not in tablas[esperada]:
                self._mal(f'{legajo} ({nombre}) es {rol} pero no está en {esperada} (corré: python manage.py sincronizar_subtipos)')
                problemas += 1
            for otra in SUBTIPOS.values():
                if otra != esperada and legajo in tablas[otra]:
                    self._mal(f'{legajo} ({nombre}) es {rol} pero también aparece en {otra}')
                    problemas += 1
        if not problemas:
            self._ok(f'{len(usuarios)} usuario(s) revisados: todos coinciden con su rol')
