"""Completa las tablas alumnos, tutores y administradores según el rol de cada usuario.

Sirve si alguien cambió un rol directo en la base de datos (por ejemplo desde DBeaver): la tabla del rol nuevo
queda sin su fila y la API falla. Solo CREA las filas que faltan; nunca borra ninguna. Se puede correr las veces que
haga falta."""
from django.core.management.base import BaseCommand

from core.models import SUBTIPOS, Usuario


class Command(BaseCommand):
    help = 'Crea la fila de alumnos, tutores o administradores que le falta a cada usuario según su rol.'

    def handle(self, *args, **options):
        creadas = 0
        sobrantes = []
        for usuario in Usuario.objects.select_related('rol'):
            rol = usuario.rol.nombre
            modelo = SUBTIPOS.get(rol)
            if modelo is not None and not modelo.objects.filter(pk=usuario.pk).exists():
                modelo.objects.create(usuario=usuario)
                creadas += 1
                self.stdout.write(f'  + {usuario.legajo} ({usuario.nombre_y_apellido}): se creó su fila en {modelo._meta.db_table}')
            # filas de otros roles: se informan pero no se tocan (pueden tener materiales, clases, etc.)
            for otro_rol, otro_modelo in SUBTIPOS.items():
                if otro_rol != rol and otro_modelo.objects.filter(pk=usuario.pk).exists():
                    sobrantes.append(f'{usuario.legajo} ({usuario.nombre_y_apellido}) tiene rol {rol} pero sigue en {otro_modelo._meta.db_table}')
        self.stdout.write(self.style.SUCCESS(f'Listo: {creadas} fila(s) creadas.'))
        if sobrantes:
            self.stdout.write('Filas de un rol anterior (no se borran):')
            for linea in sobrantes:
                self.stdout.write(f'  - {linea}')
