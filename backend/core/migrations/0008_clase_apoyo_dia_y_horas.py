"""El horario de las clases de apoyo pasa de texto libre ("Lun 14:00-16:00") a día + hora de inicio + hora de fin.

Los horarios viejos que se pueden interpretar se convierten solos. Los que no (por ejemplo "por la tarde"),
quedan "a confirmar" (día y horas en null) y se listan en la consola, para que el tutor los complete desde la app.
"""
import datetime
import re
import unicodedata

from django.db import migrations, models

# Lo que se suele escribir para cada día (sin acentos y en minúsculas).
PREFIJOS_DIA = [
    ('lu', 1),
    ('ma', 2),
    ('mi', 3),
    ('ju', 4),
    ('vi', 5),
    ('sa', 6),
]
# "14", "14hs", "14:30", "14.30 hs"
HORA = re.compile(r'(\d{1,2})(?:[:.](\d{2}))?\s*(?:hs|h)?\b')


def _sin_acentos(texto):
    return ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn').lower()


def interpretar(horario):
    """("Lun 14:00-16:00") -> (1, time(14, 0), time(16, 0)). Lo que no se pueda interpretar queda en None."""
    texto = _sin_acentos(horario or '')
    dia = None
    palabra = re.match(r'\s*([a-z]+)', texto)
    if palabra:
        dia = next((numero for prefijo, numero in PREFIJOS_DIA if palabra.group(1).startswith(prefijo)), None)

    horas = []
    for hora, minutos in HORA.findall(texto):
        hora, minutos = int(hora), int(minutos or 0)
        if hora <= 23 and minutos <= 59:
            horas.append(datetime.time(hora, minutos))
    inicio = horas[0] if horas else None
    fin = horas[1] if len(horas) > 1 and horas[1] > horas[0] else None
    return dia, inicio, fin


def convertir_horarios(apps, schema_editor):
    ClaseApoyo = apps.get_model('core', 'ClaseApoyo')
    for clase in ClaseApoyo.objects.all():
        clase.dia, clase.hora_inicio, clase.hora_fin = interpretar(clase.horario)
        clase.save(update_fields=['dia', 'hora_inicio', 'hora_fin'])
        if None in (clase.dia, clase.hora_inicio, clase.hora_fin):
            print(f'\n  Clase de apoyo {clase.pk}: no se pudo interpretar el horario "{clase.horario}". '
                  'Queda "a confirmar": el tutor tiene que completarlo desde la app.')


def volver_a_texto(apps, schema_editor):
    ClaseApoyo = apps.get_model('core', 'ClaseApoyo')
    nombres = dict(DIAS_CORTOS)
    for clase in ClaseApoyo.objects.all():
        if None in (clase.dia, clase.hora_inicio, clase.hora_fin):
            clase.horario = 'A confirmar'
        else:
            clase.horario = f'{nombres[clase.dia]} {clase.hora_inicio:%H:%M}-{clase.hora_fin:%H:%M}'
        clase.save(update_fields=['horario'])


DIAS_CORTOS = [(1, 'Lun'), (2, 'Mar'), (3, 'Mié'), (4, 'Jue'), (5, 'Vie'), (6, 'Sáb')]


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0007_suscripciones_mensajes_notificaciones'),
    ]

    operations = [
        migrations.AddField(
            model_name='claseapoyo',
            name='dia',
            field=models.PositiveSmallIntegerField(blank=True, choices=[(1, 'Lunes'), (2, 'Martes'), (3, 'Miércoles'), (4, 'Jueves'), (5, 'Viernes'), (6, 'Sábado')], null=True),
        ),
        migrations.AddField(
            model_name='claseapoyo',
            name='hora_inicio',
            field=models.TimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='claseapoyo',
            name='hora_fin',
            field=models.TimeField(blank=True, null=True),
        ),
        # La columna vieja pasa a opcional antes de convertir y borrarla: así la migración también se puede
        # deshacer (al volver atrás se recrea vacía, volver_a_texto la llena y recién ahí vuelve a ser obligatoria).
        migrations.AlterField(
            model_name='claseapoyo',
            name='horario',
            field=models.CharField(max_length=20, null=True),
        ),
        migrations.RunPython(convertir_horarios, volver_a_texto),
        migrations.RemoveField(
            model_name='claseapoyo',
            name='horario',
        ),
        migrations.AlterModelOptions(
            name='claseapoyo',
            options={'ordering': ['dia', 'hora_inicio', 'id']},
        ),
    ]
