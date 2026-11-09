import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    """Las claves foráneas que apuntaban a usuarios pasan a apuntar a la tabla del subtipo que corresponde:
    alumnos (materiales, ponderaciones, suscripciones, notificaciones) y tutores (clases y mensajes).
    Los valores no cambian: la clave de alumnos y tutores es el mismo legajo."""

    dependencies = [
        ('core', '0013_alumnos_tutores_administradores'),
    ]

    operations = [
        migrations.RemoveConstraint(model_name='ponderacion', name='ponderacion_unica_por_usuario_y_material'),
        migrations.RemoveConstraint(model_name='suscripcion', name='suscripcion_unica_por_usuario_y_clase'),

        migrations.RenameField(model_name='material', old_name='usuario', new_name='alumno'),
        migrations.AlterField(
            model_name='material', name='alumno',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='materiales', to='core.alumno'),
        ),
        migrations.RenameField(model_name='ponderacion', old_name='usuario', new_name='alumno'),
        migrations.AlterField(
            model_name='ponderacion', name='alumno',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='ponderaciones', to='core.alumno'),
        ),
        migrations.RenameField(model_name='suscripcion', old_name='usuario', new_name='alumno'),
        migrations.AlterField(
            model_name='suscripcion', name='alumno',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='suscripciones', to='core.alumno'),
        ),
        migrations.RenameField(model_name='notificacion', old_name='usuario', new_name='alumno'),
        migrations.AlterField(
            model_name='notificacion', name='alumno',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='notificaciones', to='core.alumno'),
        ),
        migrations.AlterField(
            model_name='claseapoyo', name='tutor',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='clases_apoyo', to='core.tutor'),
        ),
        migrations.RenameField(model_name='mensajeclase', old_name='autor', new_name='tutor'),
        migrations.AlterField(
            model_name='mensajeclase', name='tutor',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='mensajes_de_clases', to='core.tutor'),
        ),
        migrations.AlterField(
            model_name='notificacion', name='tipo',
            field=models.CharField(choices=[('modificacion', 'Modificación'), ('cancelacion', 'Cancelación'), ('mensaje', 'Mensaje'), ('rechazo', 'Rechazo de un material')], max_length=20),
        ),

        migrations.AddConstraint(
            model_name='ponderacion',
            constraint=models.UniqueConstraint(fields=('material', 'alumno'), name='ponderacion_unica_por_alumno_y_material'),
        ),
        migrations.AddConstraint(
            model_name='suscripcion',
            constraint=models.UniqueConstraint(fields=('clase', 'alumno'), name='suscripcion_unica_por_alumno_y_clase'),
        ),
    ]
