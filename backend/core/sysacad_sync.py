"""Traduce el plan de estudio que devuelve SySACAD al modelo local Especialidad/Materia.

El plan se importa una vez (comando `python manage.py sincronizar_materias`, o el endpoint de
administrador) y queda guardado en la base: la aplicación lista y filtra las materias desde la
base, nunca consultando a SySACAD en cada pedido.
"""
import re

from django.conf import settings
from django.db import transaction

from . import sysacad_client
from .models import Especialidad, Materia

# SySACAD marca las electivas con un sufijo en el nombre: "Entornos Gráficos (Elec.)".
SUFIJO_ELECTIVA = re.compile(r'\s*\(\s*elec\.?\s*\)\s*$', re.IGNORECASE)


class CarreraNoHabilitada(Exception):
    """La carrera no está entre settings.CARRERAS_HABILITADAS."""


def nombre_y_electiva(nombre_sysacad: str) -> tuple[str, bool]:
    """("Entornos Gráficos (Elec.)") -> ("Entornos Gráficos", True)."""
    nombre = SUFIJO_ELECTIVA.sub('', nombre_sysacad).strip()
    return nombre, nombre != nombre_sysacad.strip()


@transaction.atomic
def sync_materias(carrera_codigo: str) -> list[Materia]:
    """Trae el plan de estudio de `carrera_codigo` desde SySACAD y hace upsert
    de la Especialidad y sus Materias locales. Devuelve las Materias sincronizadas."""
    if carrera_codigo not in settings.CARRERAS_HABILITADAS:
        raise CarreraNoHabilitada(carrera_codigo)

    plan = sysacad_client.get_plan(carrera_codigo)

    especialidad, _ = Especialidad.objects.update_or_create(
        codigo_sysacad=carrera_codigo,
        defaults={"nombre": plan["nombre"]},
    )

    materias = []
    for materia_sysacad in plan["materias"]:
        nombre, electiva = nombre_y_electiva(materia_sysacad["nombre"])
        materia, _ = Materia.objects.update_or_create(
            id_sysacad=materia_sysacad["idMateria"],
            defaults={
                "nombre": nombre,
                "anio": materia_sysacad["nivel"],
                "electiva": electiva,
                "especialidad": especialidad,
            },
        )
        materias.append(materia)

    return materias
