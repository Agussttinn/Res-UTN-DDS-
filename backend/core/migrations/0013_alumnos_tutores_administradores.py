import django.db.models.deletion
from django.db import migrations, models


def crear_subtipos(apps, schema_editor):
    """Una fila en alumnos, tutores o administradores por cada usuario, según su rol.

    Además, si ya hay registros cuyo autor, votante o tutor no tiene el rol que ahora se exige (por ejemplo
    un material subido por un administrador), se crea igual la fila que necesitan para no perder esos datos."""
    Usuario = apps.get_model('core', 'Usuario')
    Alumno = apps.get_model('core', 'Alumno')
    Tutor = apps.get_model('core', 'Tutor')
    Administrador = apps.get_model('core', 'Administrador')
    por_rol = {'alumno': Alumno, 'tutor': Tutor, 'administrador': Administrador}

    for usuario in Usuario.objects.select_related('rol'):
        modelo = por_rol.get(usuario.rol.nombre)
        if modelo is not None:
            modelo.objects.get_or_create(usuario_id=usuario.pk)

    def asegurar(modelo, nombre_modelo, campo):
        legajos = set(apps.get_model('core', nombre_modelo).objects.values_list(campo, flat=True))
        for legajo in legajos:
            modelo.objects.get_or_create(usuario_id=legajo)

    asegurar(Alumno, 'Material', 'usuario_id')
    asegurar(Alumno, 'Ponderacion', 'usuario_id')
    asegurar(Alumno, 'Suscripcion', 'usuario_id')
    asegurar(Alumno, 'Notificacion', 'usuario_id')
    asegurar(Tutor, 'ClaseApoyo', 'tutor_id')
    asegurar(Tutor, 'MensajeClase', 'autor_id')


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0012_calcular_ponderaciones_existentes'),
    ]

    operations = [
        migrations.CreateModel(
            name='Alumno',
            fields=[
                ('usuario', models.OneToOneField(db_column='legajo', on_delete=django.db.models.deletion.CASCADE, primary_key=True, related_name='alumno', serialize=False, to='core.usuario')),
            ],
            options={'db_table': 'alumnos'},
        ),
        migrations.CreateModel(
            name='Tutor',
            fields=[
                ('usuario', models.OneToOneField(db_column='legajo', on_delete=django.db.models.deletion.CASCADE, primary_key=True, related_name='tutor', serialize=False, to='core.usuario')),
            ],
            options={'db_table': 'tutores'},
        ),
        migrations.CreateModel(
            name='Administrador',
            fields=[
                ('usuario', models.OneToOneField(db_column='legajo', on_delete=django.db.models.deletion.CASCADE, primary_key=True, related_name='administrador', serialize=False, to='core.usuario')),
            ],
            options={'db_table': 'administradores'},
        ),
        migrations.RunPython(crear_subtipos, migrations.RunPython.noop),
    ]
