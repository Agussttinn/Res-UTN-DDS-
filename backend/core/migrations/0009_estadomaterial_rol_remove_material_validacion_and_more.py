import django.db.models.deletion
from django.db import migrations, models

ROLES = ['alumno', 'tutor', 'administrador']
ESTADOS = ['pendiente', 'aprobado', 'rechazado', 'archivado']


def poblar_roles_y_estados(apps, schema_editor):
    """Las tablas nuevas tienen que tener sus filas antes de que alguna otra tabla las referencie."""
    Rol = apps.get_model('core', 'Rol')
    EstadoMaterial = apps.get_model('core', 'EstadoMaterial')
    for nombre in ROLES:
        Rol.objects.get_or_create(nombre=nombre)
    for nombre in ESTADOS:
        EstadoMaterial.objects.get_or_create(nombre=nombre)


def estado_desde_validacion(apps, schema_editor):
    """validacion=True -> aprobado; validacion=False -> pendiente."""
    Material = apps.get_model('core', 'Material')
    EstadoMaterial = apps.get_model('core', 'EstadoMaterial')
    aprobado = EstadoMaterial.objects.get(nombre='aprobado')
    pendiente = EstadoMaterial.objects.get(nombre='pendiente')
    Material.objects.filter(validacion=True).update(estado=aprobado)
    Material.objects.filter(validacion=False).update(estado=pendiente)


def rol_desde_texto(apps, schema_editor):
    """Pasa el texto del rol viejo ('alumno', 'tutor'...) a la fila correspondiente de la tabla roles."""
    Usuario = apps.get_model('core', 'Usuario')
    Rol = apps.get_model('core', 'Rol')
    for nombre in Usuario.objects.values_list('rol', flat=True).distinct():
        rol, _ = Rol.objects.get_or_create(nombre=nombre)
        Usuario.objects.filter(rol=nombre).update(rol_nuevo=rol)


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0008_clase_apoyo_dia_y_horas'),
    ]

    operations = [
        migrations.CreateModel(
            name='EstadoMaterial',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=30, unique=True)),
            ],
            options={'db_table': 'estados_material'},
        ),
        migrations.CreateModel(
            name='Rol',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=30, unique=True)),
            ],
            options={'db_table': 'roles'},
        ),
        migrations.RunPython(poblar_roles_y_estados, migrations.RunPython.noop),

        # Material.validacion (bool) -> Material.estado (FK): se agrega nullable, se completa y recién ahí se exige.
        migrations.AddField(
            model_name='material',
            name='estado',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, related_name='materiales', to='core.estadomaterial'),
        ),
        migrations.RunPython(estado_desde_validacion, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='material',
            name='estado',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='materiales', to='core.estadomaterial'),
        ),
        migrations.RemoveField(
            model_name='material',
            name='validacion',
        ),

        # Usuario.rol (texto) -> Usuario.rol (FK): misma técnica, pasando por una columna temporal.
        migrations.AddField(
            model_name='usuario',
            name='rol_nuevo',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, related_name='+', to='core.rol'),
        ),
        migrations.RunPython(rol_desde_texto, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name='usuario',
            name='rol',
        ),
        migrations.RenameField(
            model_name='usuario',
            old_name='rol_nuevo',
            new_name='rol',
        ),
        migrations.AlterField(
            model_name='usuario',
            name='rol',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='usuarios', to='core.rol'),
        ),

        migrations.AddField(
            model_name='material',
            name='cantidad_ponderaciones',
            field=models.PositiveIntegerField(default=0, editable=False),
        ),
        migrations.AddField(
            model_name='material',
            name='promedio_ponderacion',
            field=models.DecimalField(blank=True, decimal_places=2, editable=False, max_digits=3, null=True),
        ),
        migrations.AlterModelTable(name='especialidad', table='especialidades'),
        migrations.AlterModelTable(name='materia', table='materias'),
        migrations.AlterModelTable(name='material', table='materiales'),
        migrations.AlterModelTable(name='usuario', table='usuarios'),
    ]
