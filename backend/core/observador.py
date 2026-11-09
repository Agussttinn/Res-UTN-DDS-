"""Patrón Observer aplicado a las clases de apoyo.

- Sujeto: una ClaseApoyo, envuelta en `SujetoClase`. Lleva la lista de sus observadores (los alumnos
  suscritos, guardados en la tabla Suscripcion) y, cuando le pasa algo (el tutor la modifica, la cancela
  o manda un mensaje), los avisa a todos con `notificar(evento)`.
- Observador: cualquier `ObservadorClase`. Recibe el evento en `actualizar(evento)` y decide qué hacer.
  Hoy el único es `AvisoEnLaApp`, que le deja una notificación al alumno (la campanita del frontend).

El sujeto no sabe cómo se avisa a cada observador. Para sumar, por ejemplo, un aviso por correo, alcanza
con escribir otro ObservadorClase y devolverlo en `SujetoClase.observadores()`: no se toca ni el sujeto
ni las vistas que disparan los eventos.

Equivalencias con los nombres clásicos del patrón: attach = suscribir, detach = desuscribir,
notify = notificar, update = actualizar.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass

from django.db import IntegrityError, transaction

from .models import Alumno, ClaseApoyo, Notificacion, Suscripcion


@dataclass(frozen=True)
class EventoClase:
    """Lo que le pasó a la clase. `tipo` es Notificacion.MODIFICACION, CANCELACION o MENSAJE."""
    tipo: str
    clase: ClaseApoyo
    titulo: str
    texto: str


class ObservadorClase(ABC):
    @abstractmethod
    def actualizar(self, evento: EventoClase) -> None:
        """Lo llama el sujeto cada vez que la clase observada tiene un evento."""


class AvisoEnLaApp(ObservadorClase):
    """Le deja al alumno una notificación dentro de la aplicación."""

    def __init__(self, alumno: Alumno):
        self.alumno = alumno

    def actualizar(self, evento: EventoClase) -> None:
        Notificacion.objects.create(
            alumno=self.alumno,
            clase=evento.clase,
            tipo=evento.tipo,
            titulo=evento.titulo,
            texto=evento.texto,
        )


class SujetoClase:
    """El sujeto observado: una clase de apoyo y sus suscritos."""

    def __init__(self, clase: ClaseApoyo):
        self.clase = clase

    def suscribir(self, alumno: Alumno) -> bool:
        """Registra al alumno como observador. Devuelve False si ya estaba suscrito."""
        try:
            with transaction.atomic():
                Suscripcion.objects.create(clase=self.clase, alumno=alumno)
        except IntegrityError:
            return False
        return True

    def desuscribir(self, alumno: Alumno) -> bool:
        """Quita al alumno de los observadores. Devuelve False si no estaba suscrito."""
        borradas, _ = Suscripcion.objects.filter(clase=self.clase, alumno=alumno).delete()
        return borradas > 0

    def observadores(self) -> list[ObservadorClase]:
        suscripciones = self.clase.suscripciones.select_related('alumno')
        return [AvisoEnLaApp(suscripcion.alumno) for suscripcion in suscripciones]

    @transaction.atomic
    def notificar(self, evento: EventoClase) -> int:
        """Avisa el evento a todos los observadores. Devuelve a cuántos avisó."""
        observadores = self.observadores()
        for observador in observadores:
            observador.actualizar(evento)
        return len(observadores)
