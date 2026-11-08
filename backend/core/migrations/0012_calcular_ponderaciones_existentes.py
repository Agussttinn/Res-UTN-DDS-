from decimal import Decimal

from django.db import migrations
from django.db.models import Avg, Count


def calcular_ponderaciones(apps, schema_editor):
    """Guarda en cada material la media y la cantidad de sus ponderaciones ya cargadas."""
    Material = apps.get_model('core', 'Material')
    Ponderacion = apps.get_model('core', 'Ponderacion')
    datos = Ponderacion.objects.values('material_id').annotate(promedio=Avg('valor'), cantidad=Count('id'))
    for fila in datos:
        Material.objects.filter(pk=fila['material_id']).update(
            promedio_ponderacion=Decimal(str(fila['promedio'])).quantize(Decimal('0.01')),
            cantidad_ponderaciones=fila['cantidad'],
        )


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0011_motivo_rechazo_y_nombres_de_tablas'),
    ]

    operations = [
        migrations.RunPython(calcular_ponderaciones, migrations.RunPython.noop),
    ]
