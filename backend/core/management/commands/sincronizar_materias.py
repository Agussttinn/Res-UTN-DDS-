"""Importa a la base local el plan de estudio de las carreras habilitadas, desde SySACAD.

    python manage.py sincronizar_materias              # actualiza siempre
    python manage.py sincronizar_materias --si-falta   # solo si la carrera todavía no tiene materias (lo usa dev.mjs)

Se puede correr las veces que haga falta: actualiza las materias existentes (por su id de SySACAD) sin duplicarlas.
"""
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from core import sysacad_client, sysacad_sync
from core.models import Materia


class Command(BaseCommand):
    help = 'Importa desde SySACAD las materias de las carreras habilitadas (settings.CARRERAS_HABILITADAS).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--si-falta', action='store_true',
            help='No hace nada con las carreras que ya tienen materias en la base.',
        )

    def handle(self, *args, si_falta=False, **options):
        for carrera in settings.CARRERAS_HABILITADAS:
            if si_falta and Materia.objects.filter(especialidad__codigo_sysacad=carrera).exists():
                self.stdout.write(f'{carrera}: las materias ya están en la base.')
                continue
            try:
                materias = sysacad_sync.sync_materias(carrera)
            except sysacad_client.SysacadError as exc:
                raise CommandError(f'{carrera}: no se pudo importar el plan de estudio. {exc}') from exc
            electivas = sum(m.electiva for m in materias)
            self.stdout.write(self.style.SUCCESS(
                f'{carrera}: {len(materias)} materias importadas ({len(materias) - electivas} del plan y {electivas} electivas).'
            ))
