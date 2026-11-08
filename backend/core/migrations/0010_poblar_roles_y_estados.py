from django.db import migrations

def poblar_datos_iniciales(apps, schema_editor):
    Rol = apps.get_model('core', 'Rol')
    EstadoMaterial = apps.get_model('core', 'EstadoMaterial')

    roles = ['alumno', 'tutor', 'administrador']
    for r in roles:
        Rol.objects.get_or_create(nombre=r)

    estados = ['pendiente', 'aprobado', 'rechazado', 'archivado']
    for e in estados:
        EstadoMaterial.objects.get_or_create(nombre=e)

class Migration(migrations.Migration):

    dependencies = [
        ('core', '0009_estadomaterial_rol_remove_material_validacion_and_more'),  # Asegurate de poner el nombre exacto de la migración anterior
    ]

    operations = [
        migrations.RunPython(poblar_datos_iniciales),
    ]