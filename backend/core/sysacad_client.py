"""Cliente HTTP hacia la API de SySACAD (hoy, su mock en backend/core/mock-sysacad/).

Centraliza acá cualquier llamada a SySACAD para que, el día que se reemplace
la mock por la API real, el único cambio necesario sea SYSACAD_API_URL.
"""
from urllib.parse import quote

import requests
from django.conf import settings

TIMEOUT_SEGUNDOS = 3


class SysacadError(Exception):
    """Error de comunicación con SySACAD (timeout, caído, respuesta inesperada)."""


class PlanNoEncontrado(SysacadError):
    """No existe un plan de estudio para la carrera pedida."""


class AlumnoNoEncontrado(SysacadError):
    """No existe un alumno con ese legajo en SySACAD."""


def _get_json(path: str, no_encontrado: Exception) -> dict:
    """GET a SySACAD. Devuelve el JSON, o lanza `no_encontrado` si responde 404,
    o SysacadError si no hay conexión / tarda demasiado / responde algo inesperado."""
    url = f"{settings.SYSACAD_API_URL}{path}"
    try:
        resp = requests.get(url, timeout=TIMEOUT_SEGUNDOS)
    except requests.RequestException as exc:
        raise SysacadError(f"No se pudo conectar con SySACAD ({url}): {exc}") from exc

    if resp.status_code == 404:
        raise no_encontrado
    try:
        resp.raise_for_status()
        return resp.json()
    except (requests.RequestException, ValueError) as exc:
        raise SysacadError(f"Respuesta inesperada de SySACAD ({url}): {exc}") from exc


def get_plan(carrera: str) -> dict:
    """Devuelve el plan de estudio completo de una carrera: {"nombre": ..., "materias": [...]}."""
    return _get_json(f"/planes-de-estudio/{quote(carrera, safe='')}", PlanNoEncontrado(carrera))


def get_alumno(legajo: str) -> dict:
    """Devuelve los datos del alumno en SySACAD: {"legajo", "nombre", "correo", "carrera", ...}.
    El legajo se escapa: así no puede "salirse" de /alumnos/ hacia otra ruta de SySACAD."""
    return _get_json(f"/alumnos/{quote(legajo, safe='')}", AlumnoNoEncontrado(legajo))
