"""Traduce el plan de estudio que devuelve SySACAD al modelo local Especialidad/Materia."""
from django.db import transaction

from . import sysacad_client
from .models import Especialidad, Materia


@transaction.atomic
def sync_materias(carrera_codigo: str) -> list[Materia]:
    """Trae el plan de estudio de `carrera_codigo` desde SySACAD y hace upsert
    de la Especialidad y sus Materias locales. Devuelve las Materias sincronizadas."""
    plan = sysacad_client.get_plan(carrera_codigo)

    especialidad, _ = Especialidad.objects.update_or_create(
        codigo_sysacad=carrera_codigo,
        defaults={"nombre": plan["nombre"]},
    )

    materias = []
    for materia_sysacad in plan["materias"]:
        materia, _ = Materia.objects.update_or_create(
            id_sysacad=materia_sysacad["idMateria"],
            defaults={
                "nombre": materia_sysacad["nombre"],
                "anio": materia_sysacad["nivel"],
                "especialidad": especialidad,
            },
        )
        materias.append(materia)

    return materias
