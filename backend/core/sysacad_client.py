"""Cliente HTTP hacia la API de SySACAD (hoy, su mock en backend/core/mock-sysacad/).

Centraliza acá cualquier llamada a SySACAD para que, el día que se reemplace
la mock por la API real, el único cambio necesario sea SYSACAD_API_URL.
"""
import requests
from django.conf import settings


class SysacadError(Exception):
    """Error de comunicación con SySACAD (timeout, caído, respuesta inesperada)."""


class PlanNoEncontrado(SysacadError):
    """No existe un plan de estudio para la carrera pedida."""


def get_plan(carrera: str) -> dict:
    """Devuelve el plan de estudio completo de una carrera: {"nombre": ..., "materias": [...]}."""
    url = f"{settings.SYSACAD_API_URL}/planes-de-estudio/{carrera}"
    try:
        resp = requests.get(url, timeout=3)
    except requests.RequestException as exc:
        raise SysacadError(f"No se pudo conectar con SySACAD ({url}): {exc}") from exc

    if resp.status_code == 404:
        raise PlanNoEncontrado(carrera)
    resp.raise_for_status()
    return resp.json()
